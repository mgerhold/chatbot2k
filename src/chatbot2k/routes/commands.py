import logging
from typing import Annotated
from typing import Final
from typing import Optional

import httpx
from cachetools import TTLCache
from fastapi import Depends
from fastapi import Request
from fastapi.routing import APIRouter
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from chatbot2k.app_state import AppState
from chatbot2k.command_handlers.clip_handler import ClipHandler
from chatbot2k.command_handlers.script_command_handler import ScriptCommandHandler
from chatbot2k.dependencies import get_app_state
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
        case _:
            return "Unknown"


def _looks_like_url(text: str) -> bool:
    return text.startswith(("http://", "https://"))


_SOURCE_CODE_CACHE: TTLCache[str, str] = TTLCache(maxsize=1000, ttl=15.0 * 60.0)


async def _fetch_script_source(url: str) -> Optional[str]:
    """
    Tries to fetch the script source code from the given URL. Returns `None`
    if fetching fails. Employs a simple in-memory cache to avoid repeated network requests.
    """
    if url in _SOURCE_CODE_CACHE:
        return _SOURCE_CODE_CACHE[url]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response: Final = await client.get(url)
            response.raise_for_status()
            _SOURCE_CODE_CACHE[url] = response.text
            return response.text
    except Exception as e:
        logger.error(f"Failed to fetch script source from URL '{url}': {e}")
        return None


@router.get("/")
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
                    await _fetch_script_source(script.source_code)
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
        script_commands_data=script_commands,
        soundboard_commands=soundboard_commands,
    )

    return templates.TemplateResponse(
        request=request,
        name="commands.html",
        context=context.model_dump(),
    )
