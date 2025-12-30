from datetime import datetime
from typing import Annotated
from typing import Final

from fastapi import APIRouter
from fastapi import Depends
from starlette.requests import Request
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from chatbot2k.app_state import AppState
from chatbot2k.dependencies import UserInfo
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_broadcaster_user
from chatbot2k.dependencies import get_templates
from chatbot2k.utils.auth import get_user_profile_image_url

router: Final = APIRouter(prefix="/dashboard")


@router.get("/")
async def dashboard_welcome(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    current_user: Annotated[UserInfo, Depends(get_broadcaster_user)],
) -> Response:
    """Dashboard welcome/overview page - only accessible to the broadcaster."""
    profile_image_url: Final = await get_user_profile_image_url(app_state, current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="dashboard/welcome.html",
        context={
            "bot_name": app_state.config.bot_name,
            "author_name": app_state.config.author_name,
            "copyright_year": datetime.now().year,
            "current_user": current_user,
            "profile_image_url": profile_image_url,
            "is_broadcaster": True,
            "active_page": "welcome",
        },
    )


@router.get("/monitored-channels")
async def dashboard_monitored_channels(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    current_user: Annotated[UserInfo, Depends(get_broadcaster_user)],
) -> Response:
    """Dashboard page for managing monitored Twitch channels."""
    profile_image_url: Final = await get_user_profile_image_url(app_state, current_user.id)

    return templates.TemplateResponse(
        request=request,
        name="dashboard/monitored_channels.html",
        context={
            "bot_name": app_state.config.bot_name,
            "author_name": app_state.config.author_name,
            "copyright_year": datetime.now().year,
            "current_user": current_user,
            "profile_image_url": profile_image_url,
            "is_broadcaster": True,
            "active_page": "monitored_channels",
        },
    )
