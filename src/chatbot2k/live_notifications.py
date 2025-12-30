import asyncio
import logging
from collections.abc import AsyncIterator
from collections.abc import Awaitable
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Final
from typing import NamedTuple
from typing import final

from twitchAPI.eventsub.webhook import EventSubWebhook
from twitchAPI.helper import first
from twitchAPI.object.eventsub import StreamOnlineEvent
from twitchAPI.twitch import Twitch

from chatbot2k.app_state import AppState
from chatbot2k.config import Environment

logger: Final = logging.getLogger(__name__)


@final
class StreamLiveEvent(NamedTuple):
    broadcaster_name: str
    broadcaster_id: str


async def _setup_subscriptions(
    app_state: AppState,
    twitch: Twitch,
    eventsub: EventSubWebhook,
    callback: Callable[[StreamOnlineEvent], Awaitable[None]],
) -> None:
    """Set up EventSub subscriptions for all channels in the database."""
    channels: Final = app_state.database.get_live_notification_channels()

    for channel in channels:
        login = channel.broadcaster
        user = await first(twitch.get_users(logins=[login]))
        if user is None:
            logger.error(f"User '{login}' not found on Twitch.")
            continue
        logger.info(f"Setting up stream online listener for user '{login}' (ID: {user.id})")
        try:
            subscription_id = await eventsub.listen_stream_online(user.id, callback)
        except Exception as e:
            logger.exception(f"Failed to set up listener for user '{login}': {e}")
            continue
        logger.info(f"Successfully set up listener for user '{login}', subscription ID: {subscription_id}")


@asynccontextmanager
async def monitor_streams(
    app_state: AppState,
    callback: Callable[[StreamLiveEvent], Awaitable[None]],
) -> AsyncIterator[None]:
    channels: Final = app_state.database.get_live_notification_channels()
    if app_state.config.environment != Environment.PRODUCTION:
        logger.warning(f"Live notifications are disabled in {app_state.config.environment} environment.")
        channels_string: Final = ", ".join(channel.broadcaster for channel in channels)
        logger.info(f"Would subscribe to the following channels: {channels_string}")
        yield
        return

    twitch: Final = await Twitch(
        app_state.config.twitch_client_id,
        app_state.config.twitch_client_secret,
    )

    async def _on_stream_live(event: StreamOnlineEvent) -> None:
        await callback(
            StreamLiveEvent(
                broadcaster_name=event.event.broadcaster_user_name,
                broadcaster_id=event.event.broadcaster_user_id,
            )
        )

    eventsub: Final = EventSubWebhook(
        callback_url=app_state.config.twitch_eventsub_public_url,
        port=app_state.config.twitch_eventsub_listen_port,
        twitch=twitch,
        host_binding="0.0.0.0",
        callback_loop=asyncio.get_running_loop(),
    )
    eventsub.secret = app_state.config.twitch_eventsub_secret

    await eventsub.unsubscribe_all()

    eventsub.start()

    await _setup_subscriptions(app_state, twitch, eventsub, _on_stream_live)

    try:
        yield
    finally:
        await eventsub.stop()
        await twitch.close()
