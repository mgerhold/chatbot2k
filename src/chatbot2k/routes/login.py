from typing import Annotated
from typing import Final

from fastapi import APIRouter
from fastapi import Depends
from starlette.requests import Request
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from chatbot2k.dependencies import get_common_context
from chatbot2k.dependencies import get_templates
from chatbot2k.types.template_contexts import CommonContext

router: Final = APIRouter()


@router.get("/login", tags=["Login"])
async def login(
    request: Request,
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context=common_context.model_dump(),
    )
