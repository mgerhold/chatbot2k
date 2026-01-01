import asyncio
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
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_broadcaster_user
from chatbot2k.dependencies import get_common_context
from chatbot2k.dependencies import get_templates
from chatbot2k.types.commands import RetrieveDiscordChatCommand
from chatbot2k.types.configuration_setting_kind import ConfigurationSettingKind
from chatbot2k.types.template_contexts import ActivePage
from chatbot2k.types.template_contexts import CommonContext
from chatbot2k.types.template_contexts import DashboardContext
from chatbot2k.types.template_contexts import DashboardLiveNotificationsContext
from chatbot2k.types.template_contexts import LiveNotificationChannel
from chatbot2k.types.user_info import UserInfo

router: Final = APIRouter(prefix="/dashboard")


@router.get("/")
async def dashboard_general_settings(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
    _broadcaster_user: Annotated[UserInfo, Depends(get_broadcaster_user)],
) -> Response:
    """Dashboard general settings page - only accessible to the broadcaster."""
    bot_name: Final = app_state.database.retrieve_configuration_setting(ConfigurationSettingKind.BOT_NAME)
    author_name: Final = app_state.database.retrieve_configuration_setting(ConfigurationSettingKind.AUTHOR_NAME)

    context: Final = DashboardContext(
        **common_context.model_dump(),
        active_page=ActivePage.GENERAL_SETTINGS,
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard/general_settings.html",
        context=context.model_dump() | {"current_bot_name": bot_name, "current_author_name": author_name},
    )


@router.post("/")
async def update_general_settings(
    app_state: Annotated[AppState, Depends(get_app_state)],
    bot_name: Annotated[str, Form()],
    author_name: Annotated[str, Form()],
    _broadcaster_user: Annotated[UserInfo, Depends(get_broadcaster_user)],
) -> Response:
    """Update general settings."""
    if not bot_name.strip():
        raise HTTPException(status_code=400, detail="Bot name cannot be empty")
    if not author_name.strip():
        raise HTTPException(status_code=400, detail="Author name cannot be empty")

    app_state.database.store_configuration_setting(
        ConfigurationSettingKind.BOT_NAME,
        bot_name.strip(),
    )
    app_state.database.store_configuration_setting(
        ConfigurationSettingKind.AUTHOR_NAME,
        author_name.strip(),
    )

    return RedirectResponse("/dashboard", status_code=303)


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
    common_context: Annotated[CommonContext, Depends(get_common_context)],
    _broadcaster_user: Annotated[UserInfo, Depends(get_broadcaster_user)],
) -> Response:
    """Dashboard page for managing live notifications."""
    channels: Final = [
        LiveNotificationChannel(
            broadcaster_name=channel.broadcaster_name,
            broadcaster_id=channel.broadcaster_id,
            text_template=channel.text_template,
            target_channel=channel.target_channel,
        )
        for channel in app_state.database.get_live_notification_channels()
    ]
    discord_text_channels: Final = await _get_available_discord_text_channels(app_state)

    context: Final = DashboardLiveNotificationsContext(
        **common_context.model_dump(),
        active_page=ActivePage.LIVE_NOTIFICATIONS,
        channels=channels,
        discord_text_channels=discord_text_channels,
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard/live_notifications.html",
        context=context.model_dump(),
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
    _broadcaster_user: Annotated[UserInfo, Depends(get_broadcaster_user)],
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
    _broadcaster_user: Annotated[UserInfo, Depends(get_broadcaster_user)],
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
    _broadcaster_user: Annotated[UserInfo, Depends(get_broadcaster_user)],
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
