from typing import Optional
from typing import final

from chatbot2k.app_state import AppState
from chatbot2k.command_handlers.command_handler import CommandHandler
from chatbot2k.translation_key import TranslationKey
from chatbot2k.types.chat_command import ChatCommand
from chatbot2k.types.chat_response import ChatResponse
from chatbot2k.types.permission_level import PermissionLevel


@final
class SoundboardHandler(CommandHandler):
    COMMAND_NAME = "soundboard"
    _ENABLE_COMMAND = "enable"
    _DISABLE_COMMAND = "disable"

    def __init__(self, app_state: AppState) -> None:
        super().__init__(app_state, name=SoundboardHandler.COMMAND_NAME)

    async def handle_command(self, chat_command: ChatCommand) -> Optional[list[ChatResponse]]:
        if len(chat_command.arguments) < 1:
            return None
        command = chat_command.arguments[0].lower()
        match command:
            case SoundboardHandler._ENABLE_COMMAND:
                self._app_state.is_soundboard_enabled = True
                return [
                    ChatResponse(
                        text=self._app_state.translations_manager.get_translation(TranslationKey.SOUNDBOARD_ENABLED),
                        chat_message=chat_command.source_message,
                    )
                ]
            case SoundboardHandler._DISABLE_COMMAND:
                self._app_state.is_soundboard_enabled = False
                return [
                    ChatResponse(
                        text=self._app_state.translations_manager.get_translation(TranslationKey.SOUNDBOARD_DISABLED),
                        chat_message=chat_command.source_message,
                    )
                ]
            case _:
                # Unknown subcommand.
                return None

    @property
    def min_required_permission_level(self) -> PermissionLevel:
        return PermissionLevel.ADMIN

    @property
    def usage(self) -> str:
        return (
            f"!{SoundboardHandler.COMMAND_NAME} "
            + f"[{SoundboardHandler._ENABLE_COMMAND}|{SoundboardHandler._DISABLE_COMMAND}]"
        )

    @property
    def description(self) -> str:
        return (
            "Enables or disables the soundboard feature. Use "
            + f"`!{SoundboardHandler.COMMAND_NAME} {SoundboardHandler._ENABLE_COMMAND}` "
            + f"to enable and `!{SoundboardHandler.COMMAND_NAME} {SoundboardHandler._DISABLE_COMMAND}` "
            + "to disable the soundboard."
        )
