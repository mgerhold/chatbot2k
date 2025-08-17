import asyncio
import logging
from collections.abc import Sequence
from typing import Final
from typing import Optional
from typing import final

from chatbot2k.broadcast_message import BroadcastMessage
from chatbot2k.broadcasters.broadcaster import Broadcaster
from chatbot2k.broadcasters.parser import parse_broadcasters
from chatbot2k.chat import Chat
from chatbot2k.chat_command import to_chat_command
from chatbot2k.chat_message import ChatMessage
from chatbot2k.chat_response import ChatResponse
from chatbot2k.command_handlers.parser import parse_commands
from chatbot2k.config import CONFIG
from chatbot2k.twitch_chat import TwitchChat

logging.basicConfig(level=logging.INFO)


@final
class Sentinel:
    pass


COMMAND_HANDLERS = parse_commands(CONFIG.commands_file)
BROADCASTERS = parse_broadcasters(CONFIG.broadcasts_file)


async def process_chat_message(chat_message: ChatMessage) -> Optional[ChatResponse]:
    command: Final = to_chat_command(chat_message)
    if command is None:
        return None  # No valid command.
    if command.name not in COMMAND_HANDLERS:
        return None  # No known command.
    return await COMMAND_HANDLERS[command.name].handle_command(command)


async def run(
    chats: Sequence[Chat],
    broadcasters: Sequence[Broadcaster],
) -> None:
    queue: Final[asyncio.Queue[tuple[int, ChatMessage | BroadcastMessage | Sentinel]]] = asyncio.Queue()
    active_participant_indices: Final[set[int]] = set(range(len(chats) + len(broadcasters)))

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

        for i, broadcaster in enumerate(broadcasters):
            task_group.create_task(_producer(i + len(chats), broadcaster))

        while active_participant_indices:
            i, chat_message = await queue.get()

            match chat_message:
                case Sentinel():
                    active_participant_indices.discard(i)
                case ChatMessage():
                    for j, broadcaster in enumerate(broadcasters):
                        if j + len(chats) not in active_participant_indices:
                            # This broadcaster is not active, skip it.
                            continue
                        await broadcaster.on_chat_message_received(chat_message)
                    response = await process_chat_message(chat_message)
                    if response is not None:
                        await chats[i].send_response(response)
                case BroadcastMessage():
                    for j, chat in enumerate(chats):
                        if j not in active_participant_indices:
                            # This chat is not active, skip it.
                            continue
                        await chat.send_broadcast(chat_message)


async def main() -> None:
    chats: Final = [
        await TwitchChat.create(
            app_id=CONFIG.twitch_client_id,
            credentials=CONFIG.twitch_credentials,
            channel=CONFIG.twitch_channel,
        ),
    ]
    await run(chats, BROADCASTERS)


if __name__ == "__main__":
    asyncio.run(main())
