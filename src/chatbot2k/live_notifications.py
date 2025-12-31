import asyncio
import logging
from collections.abc import Awaitable
from collections.abc import Callable
from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import Self
from typing import final

from twitchAPI.eventsub.webhook import EventSubWebhook
from twitchAPI.helper import first
from twitchAPI.object.eventsub import StreamOnlineEvent
from twitchAPI.twitch import Twitch

from chatbot2k.app_state import AppState
from chatbot2k.config import Environment
from chatbot2k.database.tables import LiveNotificationChannel

logger: Final = logging.getLogger(__name__)


@final
class StreamLiveEvent(NamedTuple):
    broadcaster_name: str
    broadcaster_id: str


@final
class MonitoredStreamsManager:
    @final
    class _Passkey: ...

    def __init__(
        self,
        twitch: Twitch,
        eventsub: EventSubWebhook,
        callback: Callable[[StreamLiveEvent], Awaitable[None]],
        app_state: AppState,
        _: _Passkey,
    ) -> None:
        self._twitch: Final = twitch
        self._eventsub: Final = eventsub
        self._callback: Final = callback
        self._app_state: Final = app_state

    @classmethod
    async def try_create(
        cls,
        app_state: AppState,
        callback: Callable[[StreamLiveEvent], Awaitable[None]],
    ) -> Optional[Self]:
        if app_state.config.environment != Environment.PRODUCTION:
            logger.warning(f"Live notifications are disabled in {app_state.config.environment} environment.")
            return None

        twitch: Final = await Twitch(
            app_state.config.twitch_client_id,
            app_state.config.twitch_client_secret,
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

        instance: Final = cls(
            twitch,
            eventsub,
            callback,
            app_state,
            cls._Passkey(),
        )
        await instance._setup_subscriptions(app_state.database.get_live_notification_channels())
        return instance

    async def run(self) -> None:
        try:
            while True:
                await self._app_state.monitored_channels_changed.wait()
                logger.info("Monitored channels changed, updating EventSub subscriptions...")
                await self._setup_subscriptions(channels=self._app_state.database.get_live_notification_channels())
                self._app_state.monitored_channels_changed.clear()
        finally:
            await self.close()

    async def close(self) -> None:
        await self._eventsub.stop()
        await self._twitch.close()

    async def _on_stream_live(self, event: StreamOnlineEvent) -> None:
        await self._callback(
            StreamLiveEvent(
                broadcaster_name=event.event.broadcaster_user_name,
                broadcaster_id=event.event.broadcaster_user_id,
            )
        )

    async def _setup_subscriptions(
        self,
        channels: list[LiveNotificationChannel],
    ) -> None:
        """Set up EventSub subscriptions for all channels in the database."""
        logger.info("Removing all active EventSub subscriptions...")
        await self._eventsub.unsubscribe_all()
        logger.info("Setting up EventSub subscriptions for monitored channels...")
        for channel in channels:
            login = channel.broadcaster
            user = await first(self._twitch.get_users(logins=[login]))
            if user is None:
                logger.error(f"User '{login}' not found on Twitch.")
                continue
            logger.info(f"Setting up stream online listener for user '{login}' (ID: {user.id})")
            try:
                subscription_id = await self._eventsub.listen_stream_online(user.id, self._on_stream_live)
            except Exception as e:
                logger.exception(f"Failed to set up listener for user '{login}': {e}")
                continue
            logger.info(f"Successfully set up listener for user '{login}', subscription ID: {subscription_id}")
