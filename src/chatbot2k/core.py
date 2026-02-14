import asyncio
import logging
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Sequence
from contextlib import suppress
from typing import Final
from typing import Optional
from typing import final

from twitchAPI.object.eventsub import ChannelRaidEvent

from chatbot2k.app_state import AppState
from chatbot2k.broadcasters.broadcaster import Broadcaster
from chatbot2k.chats.chat import Chat
from chatbot2k.chats.discord_chat import DiscordChat
from chatbot2k.chats.twitch_chat import TwitchChat
from chatbot2k.command_handlers.clip_handler import ClipHandler
from chatbot2k.constants import RELATIVE_SOUNDBOARD_FILES_DIRECTORY
from chatbot2k.entrance_sounds import EntranceSoundHandler
from chatbot2k.live_notifications import MonitoredStreamsManager
from chatbot2k.types.broadcast_message import BroadcastMessage
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.commands import ReloadBroadcastersCommand
from chatbot2k.types.commands import RetrieveDiscordChatCommand
from chatbot2k.types.feature_flags import FormattingSupport
from chatbot2k.types.live_notification import LiveNotification
from chatbot2k.types.live_notification import LiveNotificationTextTemplate
from chatbot2k.types.live_notification import StreamLiveEvent
from chatbot2k.types.shoutout_command import ShoutoutCommand
from chatbot2k.utils.markdown import markdown_to_sanitized_html
from chatbot2k.utils.markdown import markdown_to_text

logger: Final = logging.getLogger(__name__)


@final
class _Sentinel:
    pass


async def _handle_channel_going_live(
    app_state: AppState,
    event: StreamLiveEvent,
    chats: Sequence[Chat],
) -> None:
    logger.info(f"Stream has gone live: {event.broadcaster_name} (ID = {event.broadcaster_id})")

    # If this channel is the channel of our broadcaster (which we monitor automatically), we
    # have to reset the entrance sounds session.
    if event.broadcaster_login.lower() == app_state.config.twitch_channel.lower():
        app_state.entrance_sound_handler.reset_entrance_sounds_session()

    channels: Final = app_state.database.get_live_notification_channels()
    notification_channel: Final = next(
        (channel for channel in channels if channel.broadcaster_id == event.broadcaster_id),
        None,
    )
    if notification_channel is None:
        logger.error(f"No target channel found for broadcaster {event.broadcaster_name}")
        return
    notification: Final = LiveNotification(
        event=event,
        target_channel=notification_channel.target_channel,
        text_template=LiveNotificationTextTemplate(notification_channel.text_template),
    )
    for chat in chats:
        if not chat.feature_flags.can_post_live_notifications:
            continue
        await chat.post_live_notification(notification)


async def _handle_channel_being_raided(
    app_state: AppState,
    event: ChannelRaidEvent,
    chats: Sequence[Chat],
) -> None:
    logger.info(
        f"Stream has been raided by {event.event.from_broadcaster_user_name} "
        + f"(ID = {event.event.from_broadcaster_user_id})"
    )

    action: Final = app_state.database.get_raid_event_action_by_twitch_user(
        twitch_user_id=event.event.from_broadcaster_user_id
    )

    if action is None:
        logger.info("No action configured for this raid event.")
        return

    replacements: Final = {
        "{raider_name}": event.event.from_broadcaster_user_name,
        "{raid_viewer_count}": str(event.event.viewers),
    }

    message = action.chat_message_to_send
    if message is not None:
        for placeholder, replacement in replacements.items():
            message = message.replace(placeholder, replacement)

        for chat in chats:
            if not chat.feature_flags.can_react_to_raids:
                continue
            await chat.react_to_raid(BroadcastMessage(message))

    if action.should_shoutout:
        for chat in chats:
            if not chat.feature_flags.can_shoutout:
                continue

            await chat.shoutout(
                ShoutoutCommand(
                    from_broadcaster_id=event.event.to_broadcaster_user_id,
                    to_broadcaster_id=event.event.from_broadcaster_user_id,
                )
            )

    if action.soundboard_clip_to_play is not None:
        soundboard_commands: Final = app_state.database.get_soundboard_commands()
        soundboard_command: Final = next(
            (command for command in soundboard_commands if command.name == action.soundboard_clip_to_play),
            None,
        )
        if soundboard_command is None:
            logger.error(f"Soundboard command '{action.soundboard_clip_to_play}' not found.")
            return
        clip_url: Final = f"/{RELATIVE_SOUNDBOARD_FILES_DIRECTORY.as_posix()}/{soundboard_command.filename}"
        await app_state.enqueue_soundboard_clip_url(clip_url, soundboard_command.volume)


async def run_main_loop(app_state: AppState) -> None:
    chats: Final[list[Chat]] = [
        await TwitchChat.create(app_state),
        await DiscordChat.create(app_state),
    ]

    queue: Final[asyncio.Queue[tuple[int, ChatMessage | BroadcastMessage | _Sentinel]]] = asyncio.Queue()
    active_participant_indices: Final[set[int]] = set(range(len(chats) + len(app_state.broadcasters)))

    async def _producer(i: int, chat_or_broadcaster: Chat | Broadcaster) -> None:
        try:
            match chat_or_broadcaster:
                case Chat():
                    async for chat_message in chat_or_broadcaster.get_message_stream():
                        await queue.put((i, chat_message))
                case Broadcaster():
                    async for broadcast_message in chat_or_broadcaster.get_broadcasts_stream():
                        await queue.put((i, broadcast_message))
        finally:
            # Either the chat or broadcaster finished or an error occurred,
            # we signal that it is done.
            await queue.put((i, _Sentinel()))

    async def _on_channel_live(event: StreamLiveEvent) -> None:
        await _handle_channel_going_live(app_state, event, chats)

    async def _on_channel_raid(event: ChannelRaidEvent) -> None:
        await _handle_channel_being_raided(app_state, event, chats)

    # The broadcaster tasks can not be part of the task group further below,
    # because they have to be cancelled and recreated when the configuration changes.
    broadcaster_tasks: Final[list[asyncio.Task[None]]] = []

    async def _handle_commands() -> None:
        while True:
            command = await app_state.command_queue.get()
            match command:
                case RetrieveDiscordChatCommand():
                    discord_chat = next((chat for chat in chats if isinstance(chat, DiscordChat)), None)
                    if discord_chat is None:
                        logger.error("No Discord chat available to retrieve.")
                        continue
                    await command.execute(discord_chat)
                case ReloadBroadcastersCommand():
                    logger.info("Reloading broadcasters. Cancelling existing broadcaster tasks...")
                    for task in broadcaster_tasks:
                        task.cancel()
                    logger.info("Awaiting existing broadcaster tasks to finish...")
                    with suppress(asyncio.CancelledError):
                        await asyncio.gather(*broadcaster_tasks)
                    logger.info("Cleared existing broadcaster tasks. Reloading broadcasters from configuration...")
                    broadcaster_tasks.clear()
                    for i, broadcaster in enumerate(app_state.broadcasters):
                        broadcaster_tasks.append(asyncio.create_task(_producer(i + len(chats), broadcaster)))

    monitored_streams: Final = await MonitoredStreamsManager.try_create(app_state, _on_channel_live, _on_channel_raid)

    async with asyncio.TaskGroup() as task_group:
        task_group.create_task(_handle_commands())

        for i, chat in enumerate(chats):
            task_group.create_task(_producer(i, chat))

        for i, broadcaster in enumerate(app_state.broadcasters):
            broadcaster_tasks.append(asyncio.create_task(_producer(i + len(chats), broadcaster)))

        if monitored_streams is not None:
            task_group.create_task(monitored_streams.run())

        while active_participant_indices:
            i, chat_message = await queue.get()

            match chat_message:
                case _Sentinel():
                    active_participant_indices.discard(i)
                case ChatMessage():
                    entrance_sound_to_play = (
                        None
                        if not chats[i].feature_flags.can_trigger_entrance_sounds
                        else await app_state.entrance_sound_handler.get_entrance_sound(chat_message)
                    )

                    # Notify broadcasters about the chat message so they can react to it,
                    # e.g. by delaying the next broadcast if it was already triggered by
                    # a regular chat message.
                    for j, broadcaster in enumerate(app_state.broadcasters):
                        if j + len(chats) not in active_participant_indices:
                            # This broadcaster is not active, skip it.
                            continue
                        await broadcaster.on_chat_message_received(chat_message)
                    if not chats[i].feature_flags.regular_chat:
                        if entrance_sound_to_play is not None:
                            await entrance_sound_to_play.trigger()
                        # This chat is not capable of processing regular chat messages.
                        continue

                    async def _callback(responses: list[ChatResponse], chat: Chat) -> None:
                        responses = _preprocess_outbound_messages_for_chat(responses, chat)
                        await chat.send_responses(responses)

                    asyncio.create_task(
                        _process_chat_message(
                            chat_message,
                            app_state,
                            _callback,
                            chats[i],
                            entrance_sound_to_play=entrance_sound_to_play,
                        )
                    )
                case BroadcastMessage():
                    for j, chat in enumerate(chats):
                        if j not in active_participant_indices:
                            # This chat is not active, skip it.
                            continue
                        if not chat.feature_flags.broadcasting:
                            # This chat is not capable of broadcasting messages.
                            continue
                        preprocessed = _preprocess_outbound_messages_for_chat([chat_message], chat)[0]
                        await chat.send_broadcast(preprocessed)
    for task in broadcaster_tasks:
        task.cancel()
    await asyncio.gather(*broadcaster_tasks)


async def _process_chat_message(
    chat_message: ChatMessage,
    app_state: AppState,
    callback: Callable[[list[ChatResponse], Chat], Awaitable[None]],
    chat: Chat,
    *,
    entrance_sound_to_play: Optional[EntranceSoundHandler.EntranceSoundCommand],
) -> None:
    can_trigger_entrance_sound = True
    try:
        logging.debug(f"Processing chat message from {chat_message.sender_name}: {chat_message.text}")
        command: Final = ChatCommand.from_chat_message(chat_message)
        if command is None:
            explanation_result: Final = app_state.dictionary.get_explanations(chat_message)  # Maybe `None`.
            if explanation_result is not None:
                await callback(explanation_result, chat)
            return None

        if command.name not in app_state.command_handlers:
            return None  # No known command.

        command_handler: Final = app_state.command_handlers[command.name]
        if command_handler.min_required_permission_level > chat_message.sender_permission_level:
            logging.info(
                f"User {chat_message.sender_name} does not have permission to use command {command.name}. "
                + f"Their permission level is {chat_message.sender_permission_level}"
            )
            return None

        is_soundboard_command: Final = isinstance(command_handler, ClipHandler)
        if is_soundboard_command:
            # Do not trigger entrance sounds for soundboard commands to avoid
            # multiple sounds being triggered at the same time.
            can_trigger_entrance_sound = False

        logging.info(
            f"Processing command {command.name} from user {chat_message.sender_name} "
            + f"with permission level {chat_message.sender_permission_level} "
            + f"({chat_message.sender_permission_level.name})"
        )
        responses: Final = await asyncio.create_task(command_handler.handle_command(command))
        dictionary_entries: Final = app_state.dictionary.get_explanations(chat_message)
        if dictionary_entries is not None and responses is not None:
            responses.extend(dictionary_entries)

        result: Final = (
            responses
            if responses is not None
            else [
                ChatResponse(
                    text=f"Usage: {command_handler.usage}",
                    chat_message=chat_message,
                )
            ]
        )

        await callback(result, chat)
        return None
    finally:
        if can_trigger_entrance_sound and entrance_sound_to_play is not None:
            await entrance_sound_to_play.trigger()


def _preprocess_outbound_messages_for_chat[T: ChatResponse | BroadcastMessage](
    messages: Sequence[T],
    chat: Chat,
) -> list[T]:
    result: list[T] = []
    for message in messages:
        match chat.feature_flags.formatting_support:
            case FormattingSupport.NONE:
                result.append(message._replace(text=markdown_to_text(message.text)))
            case FormattingSupport.HTML:
                result.append(message._replace(text=markdown_to_sanitized_html(message.text)))
            case FormattingSupport.MARKDOWN:
                result.append(message)
    return result
