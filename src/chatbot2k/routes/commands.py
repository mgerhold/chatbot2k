import logging
from typing import Annotated
from typing import Final
from typing import Optional
from typing import final

import httpx
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi.routing import APIRouter
from pydantic import BaseModel
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from chatbot2k.app_state import AppState
from chatbot2k.command_handlers.clip_handler import ClipHandler
from chatbot2k.command_handlers.script_command_handler import ScriptCommandHandler
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_broadcaster_user
from chatbot2k.dependencies import get_common_context
from chatbot2k.dependencies import get_templates
from chatbot2k.types.permission_level import PermissionLevel
from chatbot2k.types.template_contexts import Command
from chatbot2k.types.template_contexts import CommonContext
from chatbot2k.types.template_contexts import Constant
from chatbot2k.types.template_contexts import DictionaryEntry
from chatbot2k.types.template_contexts import MainPageContext
from chatbot2k.types.template_contexts import ScriptCommandData
from chatbot2k.types.template_contexts import SoundboardCommand
from chatbot2k.types.user_info import UserInfo
from chatbot2k.utils.markdown import markdown_to_sanitized_html

router: Final = APIRouter()

logger: Final = logging.getLogger(__name__)


def _permission_level_to_string(permission_level: PermissionLevel) -> str:
    match permission_level:
        case PermissionLevel.VIEWER:
            return "User"
        case PermissionLevel.MODERATOR:
            return "Moderator"
        case PermissionLevel.ADMIN:
            return "Administrator"


def _looks_like_url(text: str) -> bool:
    return text.startswith(("http://", "https://"))


async def _fetch_script_source(
    url: str,
    app_state: AppState,
    *,
    force_refresh: bool = False,
) -> Optional[str]:
    """
    Returns the source code from the given URL from the database. If the database
    does not contain the source code, fetches it via HTTP.
    """
    if not force_refresh:
        cached_source_code: Final = app_state.database.get_cached_source_code(url=url)
        if cached_source_code is not None:
            return cached_source_code
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response: Final = await client.get(url)
            response.raise_for_status()
            app_state.database.add_or_update_cached_source_code(url=url, source_code=response.text)
            return response.text
    except Exception as e:
        logger.error(f"Failed to fetch script source from URL '{url}': {e}")
        return None


@router.get("/", name="main_page")
async def show_main_page(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
) -> Response:
    commands: Final = sorted(
        (
            Command(
                command=handler.usage,
                description=markdown_to_sanitized_html(handler.description),
                required_permission_level=_permission_level_to_string(handler.min_required_permission_level),
            )
            for handler in app_state.command_handlers.values()
            if not isinstance(handler, ClipHandler) and not isinstance(handler, ScriptCommandHandler)
        ),
        key=lambda x: x.command,
    )
    # Fetch script commands and their source code (from URL if needed).
    script_commands_data: Final[list[ScriptCommandData]] = []
    for handler in app_state.command_handlers.values():
        if not isinstance(handler, ScriptCommandHandler):
            continue
        script = app_state.database.get_script(handler.name)
        if script is None:
            logger.error(f"Script command handler '{handler.name}' has no associated script in the database.")
            continue
        script_commands_data.append(
            ScriptCommandData(
                command=handler.usage,
                source_code=(
                    await _fetch_script_source(script.source_code, app_state)
                    if _looks_like_url(script.source_code)
                    else script.source_code
                ),
                source_code_url=script.source_code if _looks_like_url(script.source_code) else None,
            )
        )

    script_commands: Final = sorted(script_commands_data, key=lambda x: x.command)
    constants: Final = sorted(
        (
            Constant(
                name=constant.name,
                text=constant.text,
            )
            for constant in app_state.database.get_constants()
        ),
        key=lambda x: x.name,
    )
    soundboard_commands: Final = sorted(
        (
            SoundboardCommand(
                command=handler.usage,
                clip_url=handler.clip_url,
                uploader_twitch_login=handler.uploader_twitch_login,
                uploader_twitch_display_name=handler.uploader_twitch_display_name,
                volume=handler.volume,
            )
            for handler in app_state.command_handlers.values()
            if isinstance(handler, ClipHandler)
        ),
        key=lambda x: x.command,
    )

    # Turn dictionary mapping into rows and sanitize description as Markdown
    raw_dict: Final = app_state.dictionary.as_dict()  # {word: explanation}
    dictionary_entries: Final = sorted(
        (
            DictionaryEntry(
                word=word,
                explanation=markdown_to_sanitized_html(expl),
            )
            for word, expl in raw_dict.items()
        ),
        key=lambda x: x.word.lower(),
    )

    context: Final = MainPageContext(
        **common_context.model_dump(),
        commands=commands,
        dictionary_entries=dictionary_entries,
        constants=constants,
        script_commands=script_commands,
        soundboard_commands=soundboard_commands,
    )

    return templates.TemplateResponse(
        request=request,
        name="commands.html",
        context=context.model_dump(),
    )


@final
class _SoundboardCommandsResponseItem(BaseModel):
    command: str
    clip_url: str
    uploader_twitch_display_name: Optional[str]


@final
class _SoundboardCommandResponse(BaseModel):
    commands: list[_SoundboardCommandsResponseItem]


@router.get("/soundboard")
async def fetch_soundboard_commands_as_json(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
) -> _SoundboardCommandResponse:
    root_url = str(request.url_for("main_page"))
    while root_url.endswith("/"):
        root_url = root_url[:-1]

    return _SoundboardCommandResponse(
        commands=[
            _SoundboardCommandsResponseItem(
                command=handler.usage,
                clip_url=f"{root_url}/{handler.clip_url.removeprefix('/')}",
                uploader_twitch_display_name=handler.uploader_twitch_display_name,
            )
            for handler in app_state.command_handlers.values()
            if isinstance(handler, ClipHandler)
        ]
    )


@router.post("/api/refresh-source-code/{script_name:path}", name="refresh_source_code")
async def refresh_script_source_code(
    script_name: str,
    app_state: Annotated[AppState, Depends(get_app_state)],
    _: Annotated[UserInfo, Depends(get_broadcaster_user)],  # Require broadcaster permissions.
) -> None:
    normalized_name: Final = script_name.removeprefix("!").lower()
    handler: Final = app_state.command_handlers.get(normalized_name)
    if not isinstance(handler, ScriptCommandHandler):
        raise HTTPException(status_code=404, detail=f"Script command '{script_name}' not found.")
    script: Final = app_state.database.get_script(handler.name)
    if script is None:
        raise HTTPException(
            status_code=404,
            detail=f"Script command '{script_name}' has no associated script in the database.",
        )
    if not _looks_like_url(script.source_code):
        raise HTTPException(
            status_code=400,
            detail=f"Script command '{script_name}' does not have a URL source code.",
        )
    fetched_source: Final = await _fetch_script_source(
        url=script.source_code,
        app_state=app_state,
        force_refresh=True,
    )
    if fetched_source is None:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch source code for script command '{script_name}'.",
        )
