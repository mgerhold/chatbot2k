from datetime import datetime
from typing import Annotated
from typing import Final

from fastapi import APIRouter
from fastapi import Depends
from starlette.requests import Request
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from chatbot2k.app_state import AppState
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_templates

router: Final = APIRouter()


@router.get("/imprint", tags=["Imprint"])
async def imprint(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="imprint.html",
        context={
            "bot_name": app_state.config.bot_name,
            "author_name": app_state.config.author_name,
            "copyright_year": datetime.now().year,
        },
    )
