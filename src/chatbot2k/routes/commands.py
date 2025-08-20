from typing import Annotated
from typing import Final

from fastapi import Depends
from fastapi import Request
from fastapi.routing import APIRouter
from starlette.templating import Jinja2Templates

from chatbot2k.app_state import AppState
from chatbot2k.config import CONFIG
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_templates
from chatbot2k.types.permission_level import PermissionLevel
from chatbot2k.utils.markdown import markdown_to_sanitized_html

router: Final = APIRouter()


def _permission_level_to_string(permission_level: PermissionLevel) -> str:
    match permission_level:
        case PermissionLevel.VIEWER:
            return "User"
        case PermissionLevel.MODERATOR:
            return "Moderator"
        case PermissionLevel.ADMIN:
            return "Administrator"
        case _:
            return "Unknown"


@router.get("/")
def show_commands(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
):
    commands = sorted(
        [
            {
                "command": handler.usage,
                "description": markdown_to_sanitized_html(handler.description),
                "required_permission_level": _permission_level_to_string(handler.min_required_permission_level),
            }
            for handler in app_state.command_handlers.values()
        ],
        key=lambda x: x["command"],
    )
    return templates.TemplateResponse(
        request=request,
        name="commands.html",
        context={
            "bot_name": CONFIG.bot_name,
            "commands": commands,
        },
    )
