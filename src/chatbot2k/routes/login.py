from typing import Annotated
from typing import Final
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter
from fastapi import Depends
from starlette.requests import Request
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from chatbot2k.dependencies import get_common_context
from chatbot2k.dependencies import get_templates
from chatbot2k.types.template_contexts import CommonContext
from chatbot2k.types.template_contexts import LoginContext
from chatbot2k.utils.redirects import get_safe_redirect_target

router: Final = APIRouter()


@router.get("/login", name="login", tags=["Login"])
async def login(
    request: Request,
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
    next: Optional[str] = None,  # The page to redirect to after logging in.
) -> Response:
    twitch_login_url: Final = request.app.url_path_for("twitch_login")
    redirect_target: Final = get_safe_redirect_target(next)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context=LoginContext(
            **common_context.model_dump(),
            twitch_login_url=(
                twitch_login_url
                if redirect_target is None
                else f"{twitch_login_url}?{urlencode({'next': redirect_target})}"
            ),
        ).model_dump(),
    )
