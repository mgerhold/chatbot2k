import logging
import time
from asyncio import sleep
from collections.abc import AsyncGenerator
from typing import Final
from typing import Optional
from typing import final
from typing import override

from chatbot2k.app_state import AppState
from chatbot2k.broadcasters.broadcaster import Broadcaster
from chatbot2k.broadcasters.utils import replace_constants
from chatbot2k.builtins import apply_builtins
from chatbot2k.types.broadcast_message import BroadcastMessage
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_message import ChatMessage


@final
class SimpleBroadcaster(Broadcaster):
    def __init__(
        self,
        interval_seconds: float,
        message: str,
        phase_offset_seconds: float,
        app_state: AppState,
        alias_command: Optional[str] = None,
    ):
        self._interval_seconds = interval_seconds
        self._message = message
        self._phase_offset_seconds = phase_offset_seconds
        self._alias_command = None if alias_command is None else alias_command.removeprefix("!")
        self._time_of_next_broadcast = time.monotonic() + phase_offset_seconds
        self._app_state = app_state

    @override
    async def get_broadcasts_stream(self) -> AsyncGenerator[BroadcastMessage]:
        while True:
            remaining_time = self._time_of_next_broadcast - time.monotonic()
            if remaining_time > 0.0:
                await sleep(remaining_time)
                continue
            self._time_of_next_broadcast += self._interval_seconds
            yield BroadcastMessage(
                text=replace_constants(
                    apply_builtins(self._message, self._app_state),
                    self._app_state.database.get_constants(),
                )
            )

    @override
    async def on_chat_message_received(self, message: ChatMessage) -> None:
        logging.debug(f"Simple broadcaster received chat message: {message}")
        chat_command: Final = ChatCommand.from_chat_message(message)
        if chat_command is None or chat_command.name != self._alias_command or chat_command.arguments:
            return
        self._time_of_next_broadcast = time.monotonic() + self._interval_seconds
