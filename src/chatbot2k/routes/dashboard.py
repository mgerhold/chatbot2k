import asyncio
from typing import Annotated
from typing import Final
from typing import Optional
from typing import cast
from zoneinfo import available_timezones

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
from chatbot2k.types.template_contexts import DashboardGeneralSettingsContext
from chatbot2k.types.template_contexts import DashboardLiveNotificationsContext
from chatbot2k.types.template_contexts import DashboardSoundboardContext
from chatbot2k.types.template_contexts import LiveNotificationChannel
from chatbot2k.types.template_contexts import SoundboardCommand

router: Final = APIRouter(prefix="/dashboard", dependencies=[Depends(get_broadcaster_user)])


def _get_common_timezones() -> list[str]:
    """Return a curated list of commonly used timezones."""
    all_timezones: Final = available_timezones()
    # Filter to common zones (exclude deprecated and uncommon ones)
    common_prefixes: Final = {
        "America/",
        "Europe/",
        "Asia/",
        "Australia/",
        "Pacific/",
        "Africa/",
    }
    timezones: Final = sorted(
        tz for tz in all_timezones if any(tz.startswith(prefix) for prefix in common_prefixes) or tz == "UTC"
    )
    # Put UTC first.
    if "UTC" in timezones:
        timezones.remove("UTC")
        timezones.insert(0, "UTC")
    return timezones


def _get_common_locales() -> list[tuple[str, str]]:
    """Return a list of common locales as (code, display_name) tuples."""
    return [
        ("de_DE.UTF-8", "German (Germany)"),
        ("de_AT.UTF-8", "German (Austria)"),
        ("de_CH.UTF-8", "German (Switzerland)"),
        ("en_US.UTF-8", "English (United States)"),
        ("en_GB.UTF-8", "English (United Kingdom)"),
        ("en_CA.UTF-8", "English (Canada)"),
        ("en_AU.UTF-8", "English (Australia)"),
        ("fr_FR.UTF-8", "French (France)"),
        ("fr_CA.UTF-8", "French (Canada)"),
        ("fr_BE.UTF-8", "French (Belgium)"),
        ("fr_CH.UTF-8", "French (Switzerland)"),
        ("es_ES.UTF-8", "Spanish (Spain)"),
        ("es_MX.UTF-8", "Spanish (Mexico)"),
        ("es_AR.UTF-8", "Spanish (Argentina)"),
        ("it_IT.UTF-8", "Italian (Italy)"),
        ("pt_PT.UTF-8", "Portuguese (Portugal)"),
        ("pt_BR.UTF-8", "Portuguese (Brazil)"),
        ("nl_NL.UTF-8", "Dutch (Netherlands)"),
        ("nl_BE.UTF-8", "Dutch (Belgium)"),
        ("pl_PL.UTF-8", "Polish (Poland)"),
        ("ru_RU.UTF-8", "Russian (Russia)"),
        ("ja_JP.UTF-8", "Japanese (Japan)"),
        ("ko_KR.UTF-8", "Korean (South Korea)"),
        ("zh_CN.UTF-8", "Chinese (Simplified, China)"),
        ("zh_TW.UTF-8", "Chinese (Traditional, Taiwan)"),
        ("sv_SE.UTF-8", "Swedish (Sweden)"),
        ("da_DK.UTF-8", "Danish (Denmark)"),
        ("no_NO.UTF-8", "Norwegian (Norway)"),
        ("fi_FI.UTF-8", "Finnish (Finland)"),
        ("tr_TR.UTF-8", "Turkish (Turkey)"),
        ("ar_SA.UTF-8", "Arabic (Saudi Arabia)"),
        ("he_IL.UTF-8", "Hebrew (Israel)"),
        ("hi_IN.UTF-8", "Hindi (India)"),
        ("th_TH.UTF-8", "Thai (Thailand)"),
    ]


@router.get("/", name="dashboard_general_settings")
async def dashboard_general_settings(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
) -> Response:
    """Dashboard general settings page - only accessible to the broadcaster."""
    bot_name: Final = app_state.database.retrieve_configuration_setting(ConfigurationSettingKind.BOT_NAME)
    author_name: Final = app_state.database.retrieve_configuration_setting(ConfigurationSettingKind.AUTHOR_NAME)
    timezone: Final = app_state.database.retrieve_configuration_setting(ConfigurationSettingKind.TIMEZONE)
    locale: Final = app_state.database.retrieve_configuration_setting(ConfigurationSettingKind.LOCALE)

    context: Final = DashboardGeneralSettingsContext(
        **common_context.model_dump(),
        active_page=ActivePage.GENERAL_SETTINGS,
        current_bot_name=bot_name,
        current_author_name=author_name,
        current_timezone=timezone,
        current_locale=locale,
        available_timezones=_get_common_timezones(),
        available_locales=_get_common_locales(),
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard/general_settings.html",
        context=context.model_dump(),
    )


@router.post("/", name="update_general_settings")
async def update_general_settings(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    bot_name: Annotated[str, Form()],
    author_name: Annotated[str, Form()],
    timezone: Annotated[str, Form()],
    locale: Annotated[str, Form()],
) -> Response:
    """Update general settings."""
    if not bot_name.strip():
        raise HTTPException(status_code=400, detail="Bot name cannot be empty")
    if not author_name.strip():
        raise HTTPException(status_code=400, detail="Author name cannot be empty")
    if not timezone.strip():
        raise HTTPException(status_code=400, detail="Timezone cannot be empty")
    if not locale.strip():
        raise HTTPException(status_code=400, detail="Locale cannot be empty")

    app_state.database.store_configuration_setting(
        ConfigurationSettingKind.BOT_NAME,
        bot_name.strip(),
    )
    app_state.database.store_configuration_setting(
        ConfigurationSettingKind.AUTHOR_NAME,
        author_name.strip(),
    )
    app_state.database.store_configuration_setting(
        ConfigurationSettingKind.TIMEZONE,
        timezone.strip(),
    )
    app_state.database.store_configuration_setting(
        ConfigurationSettingKind.LOCALE,
        locale.strip(),
    )

    return RedirectResponse(request.url_for("dashboard_general_settings"), status_code=303)


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


@router.get("/live-notifications", name="dashboard_live_notifications")
async def dashboard_live_notifications(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
) -> Response:
    """Dashboard page for managing live notifications."""
    channels: Final = [
        LiveNotificationChannel(
            notification_channel_id=cast(int, channel.id),  # This can never be `None` here.
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


@router.post("/live-notifications/add", name="add_live_notification_channel")
async def add_live_notification_channel(
    request: Request,
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
    return RedirectResponse(request.url_for("dashboard_live_notifications"), status_code=303)


@router.post("/live-notifications/update/{channel_id}", name="update_live_notification_channel")
async def update_live_notification_channel(
    request: Request,
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
    return RedirectResponse(request.url_for("dashboard_live_notifications"), status_code=303)


@router.post("/live-notifications/delete/{channel_id}", name="delete_live_notification_channel")
async def delete_live_notification_channel(
    request: Request,
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
    return RedirectResponse(request.url_for("dashboard_live_notifications"), status_code=303)


@router.get("/soundboard", name="dashboard_soundboard")
async def dashboard_soundboard(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
) -> Response:
    """Dashboard page for viewing soundboard clips."""
    soundboard_commands: Final = [
        SoundboardCommand(command=cmd.name, clip_url=cmd.clip_url)
        for cmd in app_state.database.get_soundboard_commands()
    ]

    context: Final = DashboardSoundboardContext(
        **common_context.model_dump(),
        active_page=ActivePage.SOUNDBOARD,
        soundboard_commands=soundboard_commands,
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard/soundboard.html",
        context=context.model_dump(),
    )
