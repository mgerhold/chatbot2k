import asyncio
from datetime import datetime
from typing import Annotated
from typing import Final
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Form
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.responses import Response
from starlette.templating import Jinja2Templates
from twitchAPI.twitch import Twitch

from chatbot2k.app_state import AppState
from chatbot2k.chats.discord_chat import DiscordChat
from chatbot2k.dependencies import UserInfo
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_broadcaster_user
from chatbot2k.dependencies import get_templates
from chatbot2k.types.commands import RetrieveDiscordChatCommand
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


async def _get_available_discord_text_channels(app_state: AppState) -> Optional[list[str]]:
    on_callback_called: Final = asyncio.Event()
    available_channels: Final[list[str]] = []

    async def _callback(discord_chat: DiscordChat) -> None:
        nonlocal on_callback_called
        nonlocal available_channels

        text_channels: Final = discord_chat.get_writable_text_channels(force_refresh=True)
        available_channels.extend(text_channels)
        on_callback_called.set()

    await app_state.command_queue.put(RetrieveDiscordChatCommand(_callback))
    try:
        await asyncio.wait_for(on_callback_called.wait(), timeout=1.0)
    except TimeoutError:
        return None

    return available_channels


@router.get("/live-notifications")
async def dashboard_live_notifications(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    current_user: Annotated[UserInfo, Depends(get_broadcaster_user)],
) -> Response:
    """Dashboard page for managing live notifications."""
    profile_image_url: Final = await get_user_profile_image_url(app_state, current_user.id)
    channels: Final = app_state.database.get_live_notification_channels()
    discord_text_channels: Final = await _get_available_discord_text_channels(app_state)

    return templates.TemplateResponse(
        request=request,
        name="dashboard/live_notifications.html",
        context={
            "bot_name": app_state.config.bot_name,
            "author_name": app_state.config.author_name,
            "copyright_year": datetime.now().year,
            "current_user": current_user,
            "profile_image_url": profile_image_url,
            "is_broadcaster": True,
            "active_page": "live_notifications",
            "channels": channels,
            "discord_text_channels": discord_text_channels,
        },
    )


async def _find_broadcaster_id_by_name(name: str, app_state: AppState) -> Optional[str]:
    client: Final = await Twitch(
        app_state.config.twitch_client_id,
        app_state.config.twitch_client_secret,
    )
    async for user in client.get_users(logins=[name]):
        return user.id
    return None


@router.post("/live-notifications/add")
async def add_live_notification_channel(
    app_state: Annotated[AppState, Depends(get_app_state)],
    broadcaster_name: Annotated[str, Form()],
    text_template: Annotated[str, Form()],
    target_channel: Annotated[str, Form()],
) -> Response:
    """Add a new live notification channel."""
    broadcaster_id: Final = await _find_broadcaster_id_by_name(broadcaster_name, app_state)
    if broadcaster_id is None:
        raise HTTPException(status_code=400, detail="Broadcaster not found")
    try:
        app_state.database.add_live_notification_channel(
            broadcaster_name=broadcaster_name,
            broadcaster_id=broadcaster_id,
            text_template=text_template,
            target_channel=target_channel,
        )
        app_state.monitored_channels_changed.set()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RedirectResponse("/dashboard/live-notifications", status_code=303)


@router.post("/live-notifications/update/{channel_id}")
async def update_live_notification_channel(
    channel_id: int,
    app_state: Annotated[AppState, Depends(get_app_state)],
    broadcaster_name: Annotated[str, Form()],
    text_template: Annotated[str, Form()],
    target_channel: Annotated[str, Form()],
) -> Response:
    """Update an existing live notification channel."""
    broadcaster_id: Final = await _find_broadcaster_id_by_name(broadcaster_name, app_state)
    if broadcaster_id is None:
        raise HTTPException(status_code=400, detail="Broadcaster not found")
    try:
        app_state.database.update_live_notification_channel(
            id_=channel_id,
            broadcaster_name=broadcaster_name,
            broadcaster_id=broadcaster_id,
            text_template=text_template,
            target_channel=target_channel,
        )
        app_state.monitored_channels_changed.set()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return RedirectResponse("/dashboard/live-notifications", status_code=303)


@router.post("/live-notifications/delete/{channel_id}")
async def delete_live_notification_channel(
    channel_id: int,
    app_state: Annotated[AppState, Depends(get_app_state)],
) -> Response:
    """Delete a live notification channel."""
    channels: Final = app_state.database.get_live_notification_channels()
    channel = next((c for c in channels if c.id == channel_id), None)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")

    try:
        app_state.database.remove_live_notification_channel(broadcaster_id=channel.broadcaster_id)
        app_state.monitored_channels_changed.set()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return RedirectResponse("/dashboard/live-notifications", status_code=303)
