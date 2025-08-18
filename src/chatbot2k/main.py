import asyncio
import logging
from collections.abc import Sequence
from typing import Final
from typing import Optional
from typing import final

from chatbot2k.broadcasters.broadcaster import Broadcaster
from chatbot2k.broadcasters.parser import parse_broadcasters
from chatbot2k.chats.chat import Chat
from chatbot2k.chats.twitch_chat import TwitchChat
from chatbot2k.command_handlers.parser import parse_commands
from chatbot2k.config import CONFIG
from chatbot2k.dictionary import Dictionary
from chatbot2k.types.broadcast_message import BroadcastMessage
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_response import ChatResponse

logging.basicConfig(level=logging.INFO)


@final
class Sentinel:
    pass


COMMAND_HANDLERS = parse_commands(CONFIG.commands_file)
BROADCASTERS = parse_broadcasters(CONFIG.broadcasts_file)
DICTIONARY = Dictionary(CONFIG.dictionary_file)


async def process_chat_message(chat_message: ChatMessage) -> Optional[list[ChatResponse]]:
    command: Final = ChatCommand.from_chat_message(chat_message)
    if command is None:
        return DICTIONARY.get_explanations(chat_message)  # Maybe `None`.
    if command.name not in COMMAND_HANDLERS:
        return None  # No known command.
    return await COMMAND_HANDLERS[command.name].handle_command(command)


async def run(chats: Sequence[Chat]) -> None:
    queue: Final[asyncio.Queue[tuple[int, ChatMessage | BroadcastMessage | Sentinel]]] = asyncio.Queue()
    active_participant_indices: Final[set[int]] = set(range(len(chats) + len(BROADCASTERS)))

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

        for i, broadcaster in enumerate(BROADCASTERS):
            task_group.create_task(_producer(i + len(chats), broadcaster))

        while active_participant_indices:
            i, chat_message = await queue.get()

            match chat_message:
                case Sentinel():
                    active_participant_indices.discard(i)
                case ChatMessage():
                    for j, broadcaster in enumerate(BROADCASTERS):
                        if j + len(chats) not in active_participant_indices:
                            # This broadcaster is not active, skip it.
                            continue
                        await broadcaster.on_chat_message_received(chat_message)
                    response = await process_chat_message(chat_message)
                    if response is not None:
                        await chats[i].send_responses(response)
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
    await run(chats)


if __name__ == "__main__":
    asyncio.run(main())
