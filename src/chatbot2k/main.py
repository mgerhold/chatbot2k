import asyncio
import logging
from collections.abc import Sequence
from typing import Final
from typing import Optional
from typing import final

from chatbot2k.broadcasters.broadcaster import Broadcaster
from chatbot2k.chats.chat import Chat
from chatbot2k.chats.discord_chat import DiscordChat
from chatbot2k.chats.twitch_chat import TwitchChat
from chatbot2k.config import CONFIG
from chatbot2k.globals import Globals
from chatbot2k.types.broadcast_message import BroadcastMessage
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_response import ChatResponse

logging.basicConfig(level=logging.INFO)


@final
class Sentinel:
    pass


async def process_chat_message(
    chat_message: ChatMessage,
    globals_: Globals,
) -> Optional[list[ChatResponse]]:
    logging.debug(f"Processing chat message from {chat_message.sender_name}: {chat_message.text}")
    command: Final = ChatCommand.from_chat_message(chat_message)
    if command is None:
        return globals_.dictionary.get_explanations(chat_message)  # Maybe `None`.
    if command.name not in globals_.command_handlers:
        return None  # No known command.
    command_handler: Final = globals_.command_handlers[command.name]
    if command_handler.min_required_permission_level > chat_message.sender_permission_level:
        logging.info(
            f"User {chat_message.sender_name} does not have permission to use command {command.name}. "
            + f"Their permission level is {chat_message.sender_permission_level}"
        )
        return None
    logging.info(
        f"Processing command {command.name} from user {chat_message.sender_name} "
        + f"with permission level {chat_message.sender_permission_level}"
    )
    responses: Final = await command_handler.handle_command(command)
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


async def run(chats: Sequence[Chat], globals_: Globals) -> None:
    queue: Final[asyncio.Queue[tuple[int, ChatMessage | BroadcastMessage | Sentinel]]] = asyncio.Queue()
    active_participant_indices: Final[set[int]] = set(range(len(chats) + len(globals_.broadcasters)))

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

        for i, broadcaster in enumerate(globals_.broadcasters):
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
                    for j, broadcaster in enumerate(globals_.broadcasters):
                        if j + len(chats) not in active_participant_indices:
                            # This broadcaster is not active, skip it.
                            continue
                        await broadcaster.on_chat_message_received(chat_message)
                    if not chats[i].feature_flags.REGULAR_CHAT:
                        # This chat is not capable of processing regular chat messages.
                        continue
                    response = await process_chat_message(chat_message, globals_)
                    if response is not None:
                        await chats[i].send_responses(response)
                case BroadcastMessage():
                    for j, chat in enumerate(chats):
                        if j not in active_participant_indices:
                            # This chat is not active, skip it.
                            continue
                        if not chat.feature_flags.BROADCASTING:
                            # This chat is not capable of broadcasting messages.
                            continue
                        await chat.send_broadcast(chat_message)


async def main() -> None:
    chats: Final = [
        await TwitchChat.create(
            app_id=CONFIG.twitch_client_id,
            credentials=CONFIG.twitch_credentials,
            channel=CONFIG.twitch_channel,
        ),
        await DiscordChat.create(),
    ]
    await run(chats, Globals())


if __name__ == "__main__":
    asyncio.run(main())
