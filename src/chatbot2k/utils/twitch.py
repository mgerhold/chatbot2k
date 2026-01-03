from typing import Final
from typing import NamedTuple
from typing import final

from twitchAPI.twitch import Twitch

from chatbot2k.app_state import AppState


@final
class TwitchUserInfo(NamedTuple):
    id: str
    login: str
    display_name: str
    profile_image_url: str


async def get_twitch_user_info_by_ids(
    user_ids: list[str],
    app_state: AppState,
) -> dict[str, TwitchUserInfo]:
    if not user_ids:
        return {}
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

    return users


async def get_twitch_user_info_by_logins(
    logins: list[str],
    app_state: AppState,
) -> dict[str, TwitchUserInfo]:
    if not logins:
        return {}
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

    return users
