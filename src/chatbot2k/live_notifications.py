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
from chatbot2k.types.live_notification import StreamLiveEvent

logger: Final = logging.getLogger(__name__)


@final
class _ActiveSubscription(NamedTuple):
    broadcaster_id: str
    subscription_id: str  # Also known as "subscription topic".


@final
class MonitoredStreamsManager:
    _FETCH_STREAM_INFO_MAX_NUM_RETRIES = 3

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
        self._active_subscriptions: Final[set[_ActiveSubscription]] = set()

    @classmethod
    async def try_create(
        cls,
        app_state: AppState,
        callback: Callable[[StreamLiveEvent], Awaitable[None]],
    ) -> Optional[Self]:
        if app_state.config.environment != Environment.PRODUCTION:
            # Twitch needs a publicly accessible URL supporting HTTPS for EventSub webhooks. We cannot
            # provide that in non-production environments (usually local development setups), so we
            # disable live notifications there.
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
        await instance._setup_subscriptions()
        return instance

    async def run(self) -> None:
        try:
            while True:
                await self._app_state.monitored_channels_changed.wait()
                self._app_state.monitored_channels_changed.clear()
                logger.info("Monitored channels changed, updating EventSub subscriptions...")
                await self._setup_subscriptions()
        finally:
            await self.close()

    async def close(self) -> None:
        await self._eventsub.stop()
        await self._twitch.close()

    async def _on_stream_live(self, event: StreamOnlineEvent) -> None:
        await self._callback(await self._fetch_stream_info_with_retries(event))

    async def _fetch_stream_info_with_retries(self, event: StreamOnlineEvent) -> StreamLiveEvent:
        broadcaster_id: Final = event.event.broadcaster_user_id
        broadcaster_user: Final = await first(self._twitch.get_users(user_ids=[broadcaster_id]))
        broadcaster_name: Final = (
            event.event.broadcaster_user_name if broadcaster_user is None else broadcaster_user.display_name
        )
        broadcaster_login: Final = (
            event.event.broadcaster_user_login if broadcaster_user is None else broadcaster_user.login
        )
        backoff_delay = 1.0
        for _ in range(MonitoredStreamsManager._FETCH_STREAM_INFO_MAX_NUM_RETRIES):
            stream = await first(self._twitch.get_streams(user_id=[broadcaster_id]))
            if stream is not None:
                logger.info(
                    f"Fetched stream info for broadcaster '{broadcaster_name}' ({stream.title=}, "
                    + f"{stream.game_name=}, {stream.thumbnail_url=})"
                )
                return StreamLiveEvent(
                    broadcaster_name=broadcaster_name,
                    broadcaster_login=broadcaster_login,
                    broadcaster_id=broadcaster_id,
                    stream_title=stream.title,
                    game_name=stream.game_name,
                    thumbnail_url=stream.thumbnail_url,
                )
            await asyncio.sleep(backoff_delay)
            backoff_delay *= 2.0

        # If all retries fail, return with `None` values.
        return StreamLiveEvent(
            broadcaster_name=broadcaster_name,
            broadcaster_login=broadcaster_login,
            broadcaster_id=broadcaster_id,
            stream_title=None,
            game_name=None,
            thumbnail_url=None,
        )

    async def _setup_subscriptions(self) -> None:
        """Set up EventSub subscriptions for all channels in the database."""
        channels: Final = self._app_state.database.get_live_notification_channels()
        if not channels:
            logger.info("No channels to monitor for live notifications.")
            return
        requested_broadcaster_ids: Final = {channel.broadcaster_id for channel in channels}
        subscribed_broadcaster_ids: Final = {subscription.broadcaster_id for subscription in self._active_subscriptions}
        broadcaster_ids_to_remove: Final = subscribed_broadcaster_ids - requested_broadcaster_ids
        broadcaster_ids_to_add: Final = requested_broadcaster_ids - subscribed_broadcaster_ids

        for broadcaster_id in broadcaster_ids_to_remove:
            subscription = next(
                (
                    subscription
                    for subscription in self._active_subscriptions
                    if subscription.broadcaster_id == broadcaster_id
                ),
                None,
            )
            if subscription is None:
                logger.error(f"Subscription for broadcaster ID '{broadcaster_id}' not found.")
                continue
            result = await self._eventsub.unsubscribe_topic(subscription.subscription_id)
            if not result:
                logger.error(f"Failed to unsubscribe from EventSub for broadcaster ID '{broadcaster_id}'.")
                continue
            self._active_subscriptions.remove(subscription)
            logger.info(f"Unsubscribed from EventSub for broadcaster ID '{broadcaster_id}'.")

        for broadcaster_id in broadcaster_ids_to_add:
            channel = next(
                (channel for channel in channels if channel.broadcaster_id == broadcaster_id),
                None,
            )
            if channel is None:
                logger.error(f"Channel with broadcaster ID '{broadcaster_id}' not found.")
                continue

            id_ = channel.broadcaster_id
            user = await first(self._twitch.get_users(user_ids=[id_]))
            if user is None:
                logger.error(f"User '{channel.broadcaster_name}' not found on Twitch.")
                continue
            logger.info(f"Setting up stream online listener for user '{channel.broadcaster_name}' (ID: {user.id})")
            try:
                subscription_id = await self._eventsub.listen_stream_online(user.id, self._on_stream_live)
            except Exception as e:
                logger.exception(f"Failed to set up listener for user '{channel.broadcaster_name}': {e}")
                continue

            self._active_subscriptions.add(
                _ActiveSubscription(
                    broadcaster_id=channel.broadcaster_id,
                    subscription_id=subscription_id,
                )
            )
            logger.info(
                f"Successfully set up listener for user '{channel.broadcaster_name}', "
                + f"subscription ID: {subscription_id}"
            )
