import asyncio
import logging
import secrets
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from http import HTTPStatus
from time import monotonic
from typing import Annotated
from typing import Final
from typing import Optional
from typing import cast
from typing import final
from urllib.parse import quote

import jwt
from attr import dataclass
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.requests import Request
from fastapi.responses import RedirectResponse
from fastapi.responses import Response
from twitchAPI.helper import first
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.oauth import revoke_token
from twitchAPI.twitch import Twitch

from chatbot2k.app_state import AppState
from chatbot2k.config import Environment
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_current_user
from chatbot2k.routes.auth_constants import JWT_ALG
from chatbot2k.routes.auth_constants import JWT_EXPIRY_DAYS
from chatbot2k.routes.auth_constants import OAUTH_STATE_COOKIE
from chatbot2k.routes.auth_constants import SCOPES
from chatbot2k.routes.auth_constants import SESSION_COOKIE
from chatbot2k.types.user_info import UserInfo

logger: Final = logging.getLogger(__name__)

router: Final = APIRouter(prefix="/auth/twitch")


def _build_authorize_url(app_state: AppState, state: str) -> str:
    return (
        "https://id.twitch.tv/oauth2/authorize"
        + "?response_type=code"
        + f"&client_id={quote(app_state.config.twitch_chatbot_web_interface_client_id)}"
        + f"&redirect_uri={quote(app_state.config.twitch_redirect_uri)}"
        + f"&scope={quote(' '.join(scope.value for scope in SCOPES))}"
        + f"&state={quote(state)}"
    )


_STATE_TTL_SECONDS = 600


@final
@dataclass
class _LoginState:
    done: asyncio.Event
    expires_at: float
    session_jwt: Optional[str] = None
    error: Optional[str] = None


_LOGIN: dict[str, _LoginState] = {}
_LOGIN_LOCK = asyncio.Lock()


def _prune_login_states(now: float) -> None:
    expired: Final = [state for state, login_state in _LOGIN.items() if login_state.expires_at <= now]
    for state in expired:
        _LOGIN.pop(state, None)


async def _get_or_create_login_state(state: str) -> tuple[_LoginState, bool]:
    now: Final = monotonic()
    async with _LOGIN_LOCK:
        _prune_login_states(now)
        login_state = _LOGIN.get(state)
        if login_state is not None:
            return login_state, False  # follower
        login_state = _LoginState(done=asyncio.Event(), expires_at=now + _STATE_TTL_SECONDS)
        _LOGIN[state] = login_state
        return login_state, True  # owner


@router.get("/login")
async def twitch_login(app_state: Annotated[AppState, Depends(get_app_state)]) -> Response:
    state: Final = secrets.token_urlsafe(32)
    url: Final = _build_authorize_url(app_state, state)

    response: Final = RedirectResponse(url, status_code=HTTPStatus.FOUND)
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        max_age=600,
        httponly=True,
        secure=app_state.config.environment == Environment.PRODUCTION,
        samesite="lax",
        path="/auth/twitch",
    )
    return response


@router.get("/callback")
async def twitch_callback(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    code: Optional[str] = None,
    state: Optional[str] = None,
) -> Response:
    expected_state: Final = request.cookies.get(OAUTH_STATE_COOKIE)
    if expected_state is None or state is None or code is None or state != expected_state:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="OAuth state mismatch or missing code",
        )

    login_state, is_owner = await _get_or_create_login_state(state)

    if not is_owner:
        # Another request is/was handling this state. Wait for it and re-issue cookie.
        await login_state.done.wait()
        if login_state.session_jwt is not None:
            response = RedirectResponse("/", status_code=HTTPStatus.SEE_OTHER)
            response.delete_cookie(key=OAUTH_STATE_COOKIE, path="/auth/twitch")
            response.set_cookie(
                key=SESSION_COOKIE,
                value=login_state.session_jwt,
                max_age=JWT_EXPIRY_DAYS * 24 * 60 * 60,
                httponly=True,
                secure=app_state.config.environment == Environment.PRODUCTION,
                samesite="lax",
                path="/",
            )
            return response
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail=login_state.error or "Failed to authenticate with Twitch",
        )

    try:

        async def _do_login() -> str:
            twitch: Final = await Twitch(
                app_state.config.twitch_chatbot_web_interface_client_id,
                app_state.config.twitch_chatbot_web_interface_client_secret,
                authenticate_app=False,
            )
            try:
                auth: Final = UserAuthenticator(twitch, SCOPES, url=app_state.config.twitch_redirect_uri)
                auth_result: Final = await auth.authenticate(user_token=code)  # type: ignore[reportUnknownVariableType]
                if auth_result is None:
                    await twitch.close()
                    raise HTTPException(
                        status_code=HTTPStatus.UNAUTHORIZED,
                        detail="Failed to authenticate with Twitch",
                    )
                access_token, refresh_token = cast(tuple[str, str], auth_result)
                await twitch.set_user_authentication(access_token, SCOPES, refresh_token)
                user: Final = await first(twitch.get_users())
                if user is None:
                    await twitch.close()
                    raise HTTPException(
                        status_code=HTTPStatus.UNAUTHORIZED,
                        detail="Failed to retrieve user information from Twitch",
                    )

                now: Final = datetime.now(UTC)
                expires_at: Final = now + timedelta(days=JWT_EXPIRY_DAYS)
                expires_at_timestamp: Final = int(expires_at.timestamp())

                app_state.database.add_or_update_twitch_token_set(
                    user_id=user.id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at_timestamp,
                )

                payload: Final = {
                    "sub": user.id,
                    "login": user.login,
                    "display_name": user.display_name,
                    "exp": expires_at_timestamp,
                    "iat": int(now.timestamp()),  # Issued at.
                }
                logger.info(f"{user.id = }, {user.login = }, {user.display_name = }")
                session_jwt: Final = jwt.encode(  # type: ignore[reportUnknownMemberType]
                    payload,
                    app_state.config.jwt_secret,
                    algorithm=JWT_ALG,
                )
                return session_jwt
            finally:
                await twitch.close()

        session_jwt: Final = await _do_login()
        login_state.session_jwt = session_jwt
        return_response = RedirectResponse("/", status_code=HTTPStatus.SEE_OTHER)
        return_response.delete_cookie(key=OAUTH_STATE_COOKIE, path="/auth/twitch")
        return_response.set_cookie(
            key=SESSION_COOKIE,
            value=session_jwt,
            max_age=JWT_EXPIRY_DAYS * 24 * 60 * 60,
            httponly=True,
            secure=app_state.config.environment == Environment.PRODUCTION,
            samesite="lax",
            path="/",
        )
        return return_response
    except Exception as e:
        logger.exception("Error during Twitch OAuth callback")
        login_state.error = str(e)
        raise
    finally:
        login_state.done.set()


@router.get("/logout")
async def twitch_logout(
    current_user: Annotated[Optional[UserInfo], Depends(get_current_user)],
    app_state: Annotated[AppState, Depends(get_app_state)],
) -> Response:
    """Logout endpoint that revokes tokens and clears the session cookie."""
    if current_user is not None:
        token_set: Final = app_state.database.get_twitch_token_set(user_id=current_user.id)
        if token_set is not None:
            try:
                await revoke_token(
                    app_state.config.twitch_chatbot_web_interface_client_id,
                    token_set.access_token,
                )
                logger.info(f"Revoked access token for user {current_user.id}")
            except Exception as e:
                logger.warning(f"Failed to revoke token for user {current_user.id}: {e}")

        app_state.database.delete_twitch_token_set(user_id=current_user.id)

    response: Final = RedirectResponse("/", status_code=HTTPStatus.FOUND)
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
    )
    return response
