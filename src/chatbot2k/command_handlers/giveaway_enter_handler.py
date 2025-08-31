from typing import Final
from typing import Optional
from typing import final
from typing import override

from chatbot2k.app_state import AppState
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.command_handlers.giveaway_handler import ENTER_GIVEAWAY_COMMAND
from chatbot2k.command_handlers.giveaway_handler import GiveawayCommand
from chatbot2k.command_handlers.giveaway_handler import PickedUser
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.permission_level import PermissionLevel


@final
class GiveawayEnterCommand(CommandHandler):
    COMMAND_NAME = ENTER_GIVEAWAY_COMMAND

    def __init__(self, app_state: AppState) -> None:
        super().__init__(app_state, name=GiveawayEnterCommand.COMMAND_NAME)

    @override
    async def handle_command(self, chat_command: ChatCommand) -> Optional[list[ChatResponse]]:
        if not chat_command.source_chat.feature_flags.supports_giveaways:
            return []
        responses: Final = GiveawayCommand.enter_giveaway(
            picked_user=PickedUser(
                identifier=chat_command.source_message.sender_name,
                platform=chat_command.source_message.sender_chat.platform,
            ),
            source_message=chat_command.source_message,
        )
        return None if responses is None else responses

    @property
    @override
    def min_required_permission_level(self) -> PermissionLevel:
        return PermissionLevel.VIEWER

    @property
    @override
    def usage(self) -> str:
        return f"!{ENTER_GIVEAWAY_COMMAND}"

    @property
    @override
    def description(self) -> str:
        return "Enter the current giveaway (if one is running)."
