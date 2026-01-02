import logging
from typing import Annotated
from typing import Final

from fastapi import APIRouter
from fastapi import Depends
from starlette.requests import Request
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from chatbot2k.dependencies import get_authenticated_user
from chatbot2k.dependencies import get_common_context
from chatbot2k.dependencies import get_templates
from chatbot2k.types.template_contexts import CommonContext

router: Final = APIRouter(prefix="/viewer", dependencies=[Depends(get_authenticated_user)])

logger: Final = logging.getLogger(__name__)


@router.get("/", name="viewer_dashboard")
async def viewer_dashboard(
    request: Request,
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
) -> Response:
    """Viewer dashboard welcome page - accessible to all logged-in users."""
    return templates.TemplateResponse(
        request=request,
        name="viewer/welcome.html",
        context=common_context.model_dump(),
    )
