from datetime import datetime
from functools import lru_cache
from http import HTTPStatus
from pathlib import Path
from typing import Annotated
from typing import Final
from typing import Optional

import jwt
from fastapi import Depends
from fastapi import HTTPException
from starlette.requests import Request
from starlette.templating import Jinja2Templates

from chatbot2k.app_state import AppState
from chatbot2k.globals import Globals
from chatbot2k.routes.auth_constants import JWT_ALG
from chatbot2k.routes.auth_constants import SESSION_COOKIE
from chatbot2k.types.configuration_setting_kind import ConfigurationSettingKind
from chatbot2k.types.template_contexts import CommonContext
from chatbot2k.types.user_info import UserInfo
from chatbot2k.utils.auth import get_authenticated_twitch_client
from chatbot2k.utils.auth import get_broadcaster_id
from chatbot2k.utils.auth import get_user_profile_image_url
from chatbot2k.utils.auth import is_user_broadcaster
from chatbot2k.utils.auth import is_user_moderator


@lru_cache
def get_app_state() -> AppState:
    # Returns a singleton instance of `Globals` which implements
    # the `AppState` interface.
    return Globals()


@lru_cache
def get_templates() -> Jinja2Templates:
    templates_path: Final = Path(__file__).parent.parent.parent / "templates"
    if not templates_path.exists():
        raise FileNotFoundError(f"Templates directory not found: {templates_path}")
    return Jinja2Templates(templates_path)


def get_current_user(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
) -> Optional[UserInfo]:
    """Extract user information from JWT cookie if present and valid."""
    session_token: Final = request.cookies.get(SESSION_COOKIE)
    if session_token is None:
        return None

    try:
        payload: Final = jwt.decode(  # type: ignore[reportUnknownMemberType]
            jwt=session_token,
            key=app_state.config.jwt_secret,
            algorithms=[JWT_ALG],
        )
        return UserInfo(
            id=payload.get("sub"),
            login=payload.get("login"),
            display_name=payload.get("display_name"),
        )
    except (jwt.InvalidTokenError, KeyError):
        return None


def get_authenticated_user(
    current_user: Annotated[Optional[UserInfo], Depends(get_current_user)],
) -> UserInfo:
    """Dependency that ensures a user is logged in, otherwise raises 401."""
    if current_user is None:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Not authenticated",
        )
    return current_user


async def get_broadcaster_user(
    current_user: Annotated[UserInfo, Depends(get_authenticated_user)],
    app_state: Annotated[AppState, Depends(get_app_state)],
) -> UserInfo:
    """Dependency that ensures the logged-in user is the broadcaster."""
    if not await is_user_broadcaster(app_state, current_user.id):
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Broadcaster access required",
        )
    return current_user


async def get_moderator_user(
    current_user: Annotated[UserInfo, Depends(get_authenticated_user)],
    app_state: Annotated[AppState, Depends(get_app_state)],
) -> UserInfo:
    """Dependency that ensures the logged-in user is a moderator."""
    twitch: Final = await get_authenticated_twitch_client(app_state, current_user.id)
    try:
        broadcaster_id: Final = await get_broadcaster_id(twitch, app_state.config.twitch_channel)

        if not await is_user_moderator(twitch, broadcaster_id, current_user.id):
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail="Moderator access required",
            )
        return current_user
    finally:
        await twitch.close()


async def get_common_context(
    current_user: Annotated[Optional[UserInfo], Depends(get_current_user)],
    app_state: Annotated[AppState, Depends(get_app_state)],
) -> CommonContext:
    profile_image_url: Final = (
        None
        if current_user is None
        else await get_user_profile_image_url(
            app_state,
            current_user.id,
        )
    )
    is_broadcaster: Final = False if current_user is None else await is_user_broadcaster(app_state, current_user.id)
    pending_clips_count: Final = app_state.database.get_number_of_pending_soundboard_clips()

    # Get notification counts for the current user
    if current_user is not None:
        notifications: Final = app_state.database.get_notifications(twitch_user_id=current_user.id)
        unread_notifications_count = sum(1 for n in notifications if not n.has_been_read)
        total_notifications_count = len(notifications)
    else:
        unread_notifications_count = 0
        total_notifications_count = 0

    return CommonContext(
        bot_name=app_state.database.retrieve_configuration_setting_or_default(
            ConfigurationSettingKind.BOT_NAME,
            default="<bot name not set>",
        ),
        author_name=app_state.database.retrieve_configuration_setting_or_default(
            ConfigurationSettingKind.AUTHOR_NAME,
            default="<author name not set>",
        ),
        copyright_year=datetime.now().year,
        current_user=current_user,
        profile_image_url=profile_image_url,
        is_broadcaster=is_broadcaster,
        pending_clips_count=pending_clips_count,
        unread_notifications_count=unread_notifications_count,
        total_notifications_count=total_notifications_count,
    )
