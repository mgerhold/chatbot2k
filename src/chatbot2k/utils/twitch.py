from typing import Final
from typing import NamedTuple
from typing import final

from cachetools import TTLCache
from twitchAPI.twitch import Twitch

from chatbot2k.app_state import AppState


@final
class TwitchUserInfo(NamedTuple):
    id: str
    login: str
    display_name: str
    profile_image_url: str


_USERS_BY_ID_CACHE: TTLCache[str, TwitchUserInfo] = TTLCache(maxsize=100, ttl=5.0 * 60.0)
_USERS_BY_LOGIN_CACHE: TTLCache[str, TwitchUserInfo] = TTLCache(maxsize=100, ttl=5.0 * 60.0)


async def get_twitch_user_info_by_ids(
    user_ids: list[str],
    app_state: AppState,
) -> dict[str, TwitchUserInfo]:
    if not user_ids:
        return {}
    cached: Final = {user_id: user for user_id, user in _USERS_BY_ID_CACHE.items() if user_id in user_ids}
    if len(cached) == len(user_ids):
        # No need to query Twitch API.
        return cached
    # At least one user is not cached. We query the Twitch API for all user IDs, so that
    # we can refresh the cache for all of them (including the already cached ones).

    twitch: Final = await Twitch(
        app_state.config.twitch_client_id,
        app_state.config.twitch_client_secret,
    )
    users: Final = {
        user.id: TwitchUserInfo(
            id=user.id,
            login=user.login,
            display_name=user.display_name,
            profile_image_url=user.profile_image_url,
        )
        async for user in twitch.get_users(user_ids=user_ids)
    }
    await twitch.close()

    for user_id, user in users.items():
        _USERS_BY_ID_CACHE[user_id] = user
        _USERS_BY_LOGIN_CACHE[user.login] = user

    return users


async def get_twitch_user_info_by_logins(
    logins: list[str],
    app_state: AppState,
) -> dict[str, TwitchUserInfo]:
    if not logins:
        return {}

    cached: Final = {user_login: user for user_login, user in _USERS_BY_LOGIN_CACHE.items() if user_login in logins}
    if len(cached) == len(logins):
        # No need to query Twitch API.
        return cached
    # At least one user is not cached. We query the Twitch API for all user IDs, so that
    # we can refresh the cache for all of them (including the already cached ones).

    twitch: Final = await Twitch(
        app_state.config.twitch_client_id,
        app_state.config.twitch_client_secret,
    )
    users: Final = {
        user.login: TwitchUserInfo(
            id=user.id,
            login=user.login,
            display_name=user.display_name,
            profile_image_url=user.profile_image_url,
        )
        async for user in twitch.get_users(logins=logins)
    }
    await twitch.close()

    for user_login, user in users.items():
        _USERS_BY_ID_CACHE[user.id] = user
        _USERS_BY_LOGIN_CACHE[user_login] = user

    return users
