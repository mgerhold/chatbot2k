import logging
from datetime import UTC
from datetime import datetime
from typing import Final
from typing import Optional

from cachetools import TTLCache
from twitchAPI.twitch import Twitch

from chatbot2k.app_state import AppState
from chatbot2k.routes.auth_constants import JWT_EXPIRY_DAYS
from chatbot2k.routes.auth_constants import SCOPES

logger: Final = logging.getLogger(__name__)

_PROFILE_IMAGE_CACHE: TTLCache[str, str] = TTLCache(maxsize=1000, ttl=5.0 * 60.0)


async def get_authenticated_twitch_client(app_state: AppState, user_id: str) -> Twitch:
    token_set: Final = app_state.database.get_twitch_token_set(user_id=user_id)
    if token_set is None:
        msg: Final = f"No token set found for user_id: {user_id}"
        raise ValueError(msg)

    twitch: Final = Twitch(
        app_state.config.twitch_chatbot_web_interface_client_id,
        app_state.config.twitch_chatbot_web_interface_client_secret,
        authenticate_app=False,
    )

    async def _on_refresh(new_access_token: str, new_refresh_token: str) -> None:
        now_timestamp: Final = int(datetime.now(UTC).timestamp())
        app_state.database.add_or_update_twitch_token_set(
            user_id=user_id,
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_at=now_timestamp + (JWT_EXPIRY_DAYS * 24 * 60 * 60),
        )
        logger.info(f"Refreshed Twitch tokens for user_id: {user_id}")

    twitch.user_auth_refresh_callback = _on_refresh

    await twitch.set_user_authentication(
        token_set.access_token,
        SCOPES,
        token_set.refresh_token,
        validate=True,
    )
    return twitch


async def get_broadcaster_id(twitch: Twitch, channel_name: str) -> str:
    """Get the broadcaster's user ID from their channel name."""
    users: Final = [user async for user in twitch.get_users(logins=[channel_name])]
    if not users:
        raise ValueError(f"Channel '{channel_name}' not found")
    return users[0].id


async def is_user_moderator(twitch: Twitch, broadcaster_id: str, user_id: str) -> bool:
    """Check if a user is a moderator in the broadcaster's channel using moderated channels API."""
    if user_id == broadcaster_id:
        # Broadcasters are implicitly mods.
        return True

    moderated_channels: Final = [channel async for channel in twitch.get_moderated_channels(user_id=user_id)]
    return any(channel.broadcaster_id == broadcaster_id for channel in moderated_channels)


async def get_user_profile_image_url(app_state: AppState, user_id: str) -> Optional[str]:
    """Fetch the current profile image URL for a user from Twitch.

    Results are cached for 5 minutes to improve performance.
    """
    if user_id in _PROFILE_IMAGE_CACHE:
        return _PROFILE_IMAGE_CACHE[user_id]

    twitch: Final = await get_authenticated_twitch_client(app_state, user_id)
    try:
        users: Final = [user async for user in twitch.get_users(user_ids=[user_id])]
        if not users:
            return None
        profile_image_url: Final = users[0].profile_image_url

        _PROFILE_IMAGE_CACHE[user_id] = profile_image_url
        return profile_image_url
    finally:
        await twitch.close()
