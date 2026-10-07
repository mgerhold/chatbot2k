from chatbot2k.app_state import AppState
from chatbot2k.builtins import apply_builtins
from chatbot2k.database.tables import Constant


def replace_constants(text: str, constants: list[Constant]) -> str:
    for constant in constants:
        text = text.replace(f"{{{constant.name}}}", constant.text)
    return text


def render_broadcast_message(message: str, app_state: AppState) -> str:
    """Renders a broadcast message the way it is sent to the chats (before chat-specific formatting)."""
    return replace_constants(apply_builtins(message, app_state), app_state.database.get_constants())
