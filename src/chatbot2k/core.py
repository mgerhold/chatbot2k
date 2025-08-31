import asyncio
import logging
from collections.abc import Sequence
from typing import Final
from typing import Optional
from typing import final

from chatbot2k.app_state import AppState
from chatbot2k.broadcasters.broadcaster import Broadcaster
from chatbot2k.chats.chat import Chat
from chatbot2k.chats.discord_chat import DiscordChat
from chatbot2k.chats.twitch_chat import TwitchChat
from chatbot2k.types.broadcast_message import BroadcastMessage
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.feature_flags import FormattingSupport
from chatbot2k.utils.markdown import markdown_to_sanitized_html
from chatbot2k.utils.markdown import markdown_to_text


@final
class Sentinel:
    pass


async def run_main_loop(app_state: AppState) -> None:
    chats: Final = [
        await TwitchChat.create(app_state),
        await DiscordChat.create(app_state),
    ]

    queue: Final[asyncio.Queue[tuple[int, ChatMessage | BroadcastMessage | Sentinel]]] = asyncio.Queue()
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
            await queue.put((i, Sentinel()))

    async with asyncio.TaskGroup() as task_group:
        for i, chat in enumerate(chats):
            task_group.create_task(_producer(i, chat))

        for i, broadcaster in enumerate(app_state.broadcasters):
            task_group.create_task(_producer(i + len(chats), broadcaster))

        while active_participant_indices:
            i, chat_message = await queue.get()

            match chat_message:
                case Sentinel():
                    active_participant_indices.discard(i)
                case ChatMessage():
                    # Notify broadcasters about the chat message so they can react to it,
                    # e.g. by delaying the next broadcast if it was already triggered by
                    # a regular chat message.
                    for j, broadcaster in enumerate(app_state.broadcasters):
                        if j + len(chats) not in active_participant_indices:
                            # This broadcaster is not active, skip it.
                            continue
                        await broadcaster.on_chat_message_received(chat_message)
                    if not chats[i].feature_flags.regular_chat:
                        # This chat is not capable of processing regular chat messages.
                        continue
                    responses = await _process_chat_message(chat_message, app_state)
                    if responses is not None:
                        responses = _preprocess_outbound_messages_for_chat(responses, chats[i])
                        await chats[i].send_responses(responses)
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


async def _process_chat_message(
    chat_message: ChatMessage,
    app_state: AppState,
) -> Optional[list[ChatResponse]]:
    logging.debug(f"Processing chat message from {chat_message.sender_name}: {chat_message.text}")
    command: Final = ChatCommand.from_chat_message(chat_message)
    if command is None:
        return app_state.dictionary.get_explanations(chat_message)  # Maybe `None`.

    if command.name not in app_state.command_handlers:
        return None  # No known command.

    command_handler: Final = app_state.command_handlers[command.name]
    if command_handler.min_required_permission_level > chat_message.sender_permission_level:
        logging.info(
            f"User {chat_message.sender_name} does not have permission to use command {command.name}. "
            + f"Their permission level is {chat_message.sender_permission_level}"
        )
        return None
    logging.info(
        f"Processing command {command.name} from user {chat_message.sender_name} "
        + f"with permission level {chat_message.sender_permission_level} ({chat_message.sender_permission_level.name})"
    )
    responses: Final = await command_handler.handle_command(command)
    dictionary_entries: Final = app_state.dictionary.get_explanations(chat_message)
    if dictionary_entries is not None and responses is not None:
        responses.extend(dictionary_entries)
    return (
        responses
        if responses is not None
        else [
            ChatResponse(
                text=f"Usage: {command_handler.usage}",
                chat_message=chat_message,
            )
        ]
    )


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
