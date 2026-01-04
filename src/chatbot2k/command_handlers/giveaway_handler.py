import random
from dataclasses import dataclass
from enum import Enum
from enum import auto
from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import final
from typing import override

from chatbot2k.app_state import AppState
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_message import ChatMessage
from chatbot2k.types.chat_platform import ChatPlatform
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.permission_level import PermissionLevel

ENTER_GIVEAWAY_COMMAND = "enter"


@final
class PickedUser(NamedTuple):
    identifier: str
    platform: ChatPlatform


@final
class _State(Enum):
    IDLE = auto()
    RUNNING = auto()
    ENDED = auto()


@final
@dataclass
class _GiveawayState:
    state: _State
    picked: set[PickedUser]


@final
class GiveawayCommand(CommandHandler):
    COMMAND_NAME = "giveaway"

    # This is a class attribute to keep the data even across reloading the commands.
    _state = _GiveawayState(state=_State.IDLE, picked=set())

    _START_COMMAND = "start"
    _END_COMMAND = "end"
    _PICK_COMMAND = "pick"

    def __init__(self, app_state: AppState) -> None:
        super().__init__(app_state, name=GiveawayCommand.COMMAND_NAME)

    @override
    async def handle_command(self, chat_command: ChatCommand) -> Optional[list[ChatResponse]]:
        if not chat_command.source_chat.feature_flags.supports_giveaways:
            return []
        if not chat_command.arguments:
            return None

        subcommand: Final = chat_command.arguments[0].lower()
        chat_message: Final = chat_command.source_message
        match subcommand:
            case GiveawayCommand._START_COMMAND:
                return [self._start_giveaway(chat_message)]
            case GiveawayCommand._END_COMMAND:
                return [self._end_giveaway(chat_message)]
            case GiveawayCommand._PICK_COMMAND:
                return [self._pick_winner(chat_message)]
            case _:
                return None

    @property
    @override
    def min_required_permission_level(self) -> PermissionLevel:
        return PermissionLevel.ADMIN

    @property
    @override
    def usage(self) -> str:
        return (
            "!giveaway "
            + f"<{GiveawayCommand._START_COMMAND}|{GiveawayCommand._END_COMMAND}|{GiveawayCommand._PICK_COMMAND}>"
        )

    @property
    @override
    def description(self) -> str:
        return (
            "Manage giveaways. Subcommands: "
            + f"`{GiveawayCommand._START_COMMAND}` - Start a new giveaway, "
            + f"`{GiveawayCommand._END_COMMAND}` - End the current giveaway, "
            + f"`{GiveawayCommand._PICK_COMMAND}` - Pick a random winner from the current participants."
        )

    @staticmethod
    def enter_giveaway(picked_user: PickedUser, source_message: ChatMessage) -> Optional[list[ChatResponse]]:
        if GiveawayCommand._state.state != _State.RUNNING:
            return [ChatResponse("No giveaway is currently running.", source_message)]
        if picked_user in GiveawayCommand._state.picked:
            return []
        GiveawayCommand._state.picked.add(picked_user)
        return [ChatResponse(f"{picked_user.identifier} has entered the giveaway!", source_message)]

    def _start_giveaway(self, source_message: ChatMessage) -> ChatResponse:
        if GiveawayCommand._state.state not in (_State.IDLE, _State.ENDED):
            return ChatResponse(
                "A giveaway is already running. Please end it before starting a new one.",
                source_message,
            )
        GiveawayCommand._state = _GiveawayState(state=_State.RUNNING, picked=set())
        return ChatResponse(
            f"A new giveaway has started! Type `!{ENTER_GIVEAWAY_COMMAND}` to participate.",
            source_message,
        )

    def _end_giveaway(self, source_message: ChatMessage) -> ChatResponse:
        if GiveawayCommand._state.state != _State.RUNNING:
            return ChatResponse("Cannot end giveaway: No giveaway is currently running.", source_message)
        GiveawayCommand._state.state = _State.ENDED
        return ChatResponse("The giveaway has ended! No more entries will be accepted.", source_message)

    def _pick_winner(self, source_message: ChatMessage) -> ChatResponse:
        if GiveawayCommand._state.state == _State.RUNNING:
            return ChatResponse("Cannot pick a winner: The giveaway is still running.", source_message)
        if GiveawayCommand._state.state != _State.ENDED:
            return ChatResponse("Cannot pick a winner: No giveaway is currently running.", source_message)
        if not GiveawayCommand._state.picked:
            return ChatResponse(
                "No participants have entered the giveaway yet or there is no one left to pick.", source_message
            )

        winner: Final = random.choice(list(GiveawayCommand._state.picked))  # noqa: S311 # This is not security-sensitive.
        GiveawayCommand._state.picked.remove(winner)
        return ChatResponse(f"The winner of the giveaway is: {winner.identifier}!", source_message)
