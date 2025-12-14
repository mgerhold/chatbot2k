import logging
import secrets
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from http import HTTPStatus
from typing import Annotated
from typing import Final
from typing import Optional
from typing import cast
from urllib.parse import quote

import jwt
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.requests import Request
from fastapi.responses import RedirectResponse
from fastapi.responses import Response
from twitchAPI.helper import first
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.twitch import Twitch

from chatbot2k.app_state import AppState
from chatbot2k.dependencies import get_app_state
from chatbot2k.routes.auth_constants import JWT_ALG
from chatbot2k.routes.auth_constants import JWT_EXPIRY_DAYS
from chatbot2k.routes.auth_constants import OAUTH_STATE_COOKIE
from chatbot2k.routes.auth_constants import SCOPES
from chatbot2k.routes.auth_constants import SESSION_COOKIE

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
        secure=True,
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

    twitch: Final = await Twitch(
        app_state.config.twitch_chatbot_web_interface_client_id,
        app_state.config.twitch_chatbot_web_interface_client_secret,
        authenticate_app=False,
    )

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

    # TODO: Persist tokens in database associated with the user (by their ID).

    now: Final = datetime.now(UTC)
    expires_at: Final = now + timedelta(days=JWT_EXPIRY_DAYS)
    payload: Final = {
        "sub": user.id,
        "login": user.login,
        "display_name": user.display_name,
        "exp": int(expires_at.timestamp()),
        "iat": int(now.timestamp()),  # Issued at.
    }
    logger.info(f"{user.id = }, {user.login = }, {user.display_name = }")
    session_jwt: Final = jwt.encode(  # type: ignore[reportUnknownMemberType]
        payload,
        app_state.config.jwt_secret,
        algorithm=JWT_ALG,
    )

    await twitch.close()

    response: Final = RedirectResponse("/", status_code=HTTPStatus.FOUND)
    response.delete_cookie(
        key=OAUTH_STATE_COOKIE,
        path="/auth/twitch",
    )
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_jwt,
        max_age=JWT_EXPIRY_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return response
