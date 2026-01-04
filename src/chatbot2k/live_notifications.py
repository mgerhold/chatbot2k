import asyncio
import logging
from collections.abc import Awaitable
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC
from datetime import datetime
from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import Self
from typing import final

from twitchAPI.eventsub.webhook import EventSubWebhook
from twitchAPI.helper import first
from twitchAPI.object.eventsub import StreamOnlineEvent
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthType

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
    _TWITCH_MESSAGE_EXPIRY_MINUTES = 60

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
        self._event_queue: Final[asyncio.Queue[StreamOnlineEvent]] = asyncio.Queue()
        self._event_handling_task: Final = asyncio.create_task(self._handle_events())

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
        eventsub.unsubscribe_on_stop = False  # Required to preserve subscriptions across restarts.

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
        self._event_handling_task.cancel()
        with suppress(asyncio.CancelledError):
            await self._event_handling_task
        await self._twitch.close()

    async def _handle_events(self) -> None:
        while True:
            event = await self._event_queue.get()

            try:
                message_id = event.metadata.message_id
                message_timestamp = event.metadata.message_timestamp

                # > Make sure the value in the message_timestamp field isn’t older than 10 minutes.
                # (https://dev.twitch.tv/docs/eventsub/)
                message_age = datetime.now(UTC) - message_timestamp
                if message_age.total_seconds() > 10 * 60:
                    logger.warning(
                        f"Ignoring stream live event with message ID '{message_id}' "
                        + f"due to old timestamp ({message_timestamp.isoformat()})"
                    )
                    continue

                try:
                    self._app_state.database.purge_received_twitch_messages(
                        expiry_minutes=MonitoredStreamsManager._TWITCH_MESSAGE_EXPIRY_MINUTES
                    )
                except Exception as e:
                    logger.exception(f"Failed to purge old Twitch messages: {e}")
                    # Proceed anyway.

                # > Make sure you haven’t seen the ID in the message_id field before.
                # (https://dev.twitch.tv/docs/eventsub/)
                try:
                    if self._app_state.database.has_twitch_message_been_received(message_id=message_id):
                        # We have already processed this event before, ignore it.
                        continue
                except Exception as e:
                    logger.exception(f"Failed to check if Twitch message has been received: {e}")
                    # We proceed anyway to avoid missing notifications due to transient errors.

                try:
                    self._app_state.database.add_or_update_received_twitch_message(
                        message_id=message_id,
                        timestamp=message_timestamp,
                    )
                except Exception as e:
                    logger.exception(f"Failed to record received Twitch message: {e}")
                    # Proceed anyway.

                try:
                    await self._callback(await self._fetch_stream_info_with_retries(event))
                except Exception as e:
                    logger.exception(f"Error while processing stream live event: {e}")
            finally:
                self._event_queue.task_done()

    async def _on_stream_live(self, event: StreamOnlineEvent) -> None:
        # We use `put_nowait` here to avoid blocking the EventSub webhook processing. Twitch
        # expects a quick response to webhook notifications, and blocking here could lead to
        # timeouts and failed notifications. Events are processed asynchronously in a separate
        # task.
        self._event_queue.put_nowait(event)

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

    async def _get_broadcaster_id(self) -> Optional[str]:
        broadcaster_name: Final = self._app_state.config.twitch_channel
        user: Final = await first(self._twitch.get_users(logins=[broadcaster_name]))
        if user is None:
            logger.error(f"User '{broadcaster_name}' not found on Twitch.")
            return None
        return user.id

    async def _setup_subscriptions(self) -> None:
        """Set up EventSub subscriptions for all channels in the database."""
        logger.info("Checking for already existing EventSub subscriptions...")

        # We ask the Twitch API for existing subscriptions to avoid creating duplicates.
        active_subscriptions: Final[set[_ActiveSubscription]] = set()
        existing_subscriptions: Final = await self._twitch.get_eventsub_subscriptions(
            sub_type="stream.online",
            target_token=AuthType.APP,  # For webhook subscriptions (not websocket).
        )

        for existing_subscription in existing_subscriptions.data:
            logging.info(f"Existing subscription: {existing_subscription}")

        for existing_subscription in existing_subscriptions.data:
            if existing_subscription.type != "stream.online":
                logger.error(
                    f"Received non-stream.online subscription from Twitch despite filtering: {existing_subscription}"
                )
                continue

            # > The callback URL where the notifications are sent. Included only if method is set to webhook.
            # See: https://dev.twitch.tv/docs/api/reference#get-eventsub-subscriptions
            if existing_subscription.transport.get("method") != "webhook":
                logger.error(
                    f"Received subscription with unexpected transport method: {existing_subscription}"
                    + " (expected: webhook)"
                )
                continue
            if (
                existing_subscription.transport.get("callback")
                != f"{self._app_state.config.twitch_eventsub_public_url}/callback"
            ):
                # Maybe caused by a previous instance of the bot running with a different public URL, just ignore.
                continue

            if existing_subscription.status == "enabled":
                # The structure of the `condition` dict depends on the subscription type. For "stream.online"
                # subscriptions, it contains a "broadcaster_user_id" field.
                # See: https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#streamonline
                broadcaster_user_id = existing_subscription.condition.get("broadcaster_user_id")
                if broadcaster_user_id is None:
                    logger.error(
                        f"Received subscription without broadcaster_user_id condition: {existing_subscription}"
                    )
                    continue

                if any(sub.broadcaster_id == broadcaster_user_id for sub in active_subscriptions):
                    # Duplicate subscription for the same broadcaster ID, remove it.
                    result = await self._eventsub.unsubscribe_topic(existing_subscription.id)
                    if not result:
                        logger.error(
                            "Failed to unsubscribe from duplicate EventSub subscription ID "
                            + f"'{existing_subscription.id}'."
                        )
                        continue
                    logger.info(f"Unsubscribed from duplicate EventSub subscription ID '{existing_subscription.id}'.")
                    continue
                active_subscriptions.add(
                    _ActiveSubscription(
                        broadcaster_id=broadcaster_user_id,
                        subscription_id=existing_subscription.id,
                    )
                )
                logger.info(f"Subscription to broadcaster ID {broadcaster_user_id} does already exist.")
            else:
                # This subscription is in an unexpected or invalid state, so we remove it.
                result = await self._eventsub.unsubscribe_topic(existing_subscription.id)
                if not result:
                    logger.error(
                        f"Failed to unsubscribe from invalid EventSub subscription ID '{existing_subscription.id}'."
                    )
                    continue
                logger.info(f"Unsubscribed from invalid EventSub subscription ID '{existing_subscription.id}'.")

        channels: Final = self._app_state.database.get_live_notification_channels()

        requested_broadcaster_ids: Final = {channel.broadcaster_id for channel in channels}

        # In addition to the explicitly monitored channels, we also monitor the broadcaster's own channel.
        # This is needed for the entrance sounds (which have to be reset when the broadcaster goes live).
        broadcaster_id: Final = await self._get_broadcaster_id()
        if broadcaster_id is not None:
            requested_broadcaster_ids.add(broadcaster_id)
            # TODO: We could also add subscriptions for other events here, e.g. subscriptions, raids, etc.
        else:
            logger.error("Cannot set up EventSub subscriptions without broadcaster ID.")

        subscribed_broadcaster_ids: Final = {subscription.broadcaster_id for subscription in active_subscriptions}
        broadcaster_ids_to_remove: Final = subscribed_broadcaster_ids - requested_broadcaster_ids
        broadcaster_ids_to_add: Final = requested_broadcaster_ids - subscribed_broadcaster_ids

        for id_ in broadcaster_ids_to_remove:
            subscription = next(
                (subscription for subscription in active_subscriptions if subscription.broadcaster_id == id_),
                None,
            )
            if subscription is None:
                logger.error(f"Subscription for broadcaster ID '{id_}' not found.")
                continue
            result = await self._eventsub.unsubscribe_topic(subscription.subscription_id)
            if not result:
                logger.error(f"Failed to unsubscribe from EventSub for broadcaster ID '{id_}'.")
                continue
            logger.info(f"Unsubscribed from EventSub for broadcaster ID '{id_}'.")

        for id_ in broadcaster_ids_to_add:
            if broadcaster_id is not None and id_ == broadcaster_id:
                try:
                    subscription_id = await self._eventsub.listen_stream_online(broadcaster_id, self._on_stream_live)
                    logger.info(
                        "Successfully set up listener for broadcaster's own channel, "
                        + f"subscription ID: {subscription_id}"
                    )
                    continue
                except Exception as e:
                    logger.exception(f"Failed to set up listener for broadcaster's own channel: {e}")
                    continue
            channel = next(
                (channel for channel in channels if channel.broadcaster_id == id_),
                None,
            )
            if channel is None:
                if id_ != broadcaster_id:
                    # Only log an error if this is not the broadcaster's own channel. This case
                    # is already handled above.
                    logger.error(f"Channel with broadcaster ID '{id_}' not found.")
                continue

            id_ = channel.broadcaster_id
            user = await first(self._twitch.get_users(user_ids=[id_]))
            if user is None:
                logger.error(f"User with '{id_}' not found on Twitch.")
                continue
            logger.info(f"Setting up stream online listener for user '{user.display_name}' (ID: {user.id})")
            try:
                subscription_id = await self._eventsub.listen_stream_online(user.id, self._on_stream_live)
            except Exception as e:
                logger.exception(f"Failed to set up listener for user '{user.display_name}': {e}")
                continue

            logger.info(
                f"Successfully set up listener for user '{user.display_name}', " + f"subscription ID: {subscription_id}"
            )
