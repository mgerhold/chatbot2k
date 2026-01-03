import asyncio
import logging
from typing import Annotated
from typing import Final
from typing import Literal
from typing import Optional
from typing import cast
from typing import final
from uuid import uuid4
from zoneinfo import available_timezones

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.responses import Response
from starlette.templating import Jinja2Templates
from twitchAPI.twitch import Twitch

from chatbot2k.app_state import AppState
from chatbot2k.chats.discord_chat import DiscordChat
from chatbot2k.constants import RELATIVE_SOUNDBOARD_FILES_DIRECTORY
from chatbot2k.constants import SOUNDBOARD_FILES_DIRECTORY
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_broadcaster_user
from chatbot2k.dependencies import get_common_context
from chatbot2k.dependencies import get_templates
from chatbot2k.types.commands import RetrieveDiscordChatCommand
from chatbot2k.types.configuration_setting_kind import ConfigurationSettingKind
from chatbot2k.types.template_contexts import ActivePage
from chatbot2k.types.template_contexts import AdminContext
from chatbot2k.types.template_contexts import AdminEntranceSoundsContext
from chatbot2k.types.template_contexts import AdminGeneralSettingsContext
from chatbot2k.types.template_contexts import AdminLiveNotificationsContext
from chatbot2k.types.template_contexts import AdminPendingClipsContext
from chatbot2k.types.template_contexts import AdminSoundboardContext
from chatbot2k.types.template_contexts import CommonContext
from chatbot2k.types.template_contexts import EntranceSound
from chatbot2k.types.template_contexts import LiveNotificationChannel
from chatbot2k.types.template_contexts import PendingClip
from chatbot2k.types.template_contexts import SoundboardCommand
from chatbot2k.types.user_info import UserInfo
from chatbot2k.utils.mime_types import get_file_extension_by_mime_type
from chatbot2k.utils.twitch import get_twitch_user_info_by_ids
from chatbot2k.utils.twitch import get_twitch_user_info_by_logins

router: Final = APIRouter(prefix="/admin", dependencies=[Depends(get_broadcaster_user)])

logger: Final = logging.getLogger(__name__)


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


@router.get("/", name="admin_general_settings")
async def admin_general_settings(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
) -> Response:
    """Admin dashboard general settings page - only accessible to the broadcaster."""
    bot_name: Final = app_state.database.retrieve_configuration_setting(ConfigurationSettingKind.BOT_NAME)
    author_name: Final = app_state.database.retrieve_configuration_setting(ConfigurationSettingKind.AUTHOR_NAME)
    timezone: Final = app_state.database.retrieve_configuration_setting(ConfigurationSettingKind.TIMEZONE)
    locale: Final = app_state.database.retrieve_configuration_setting(ConfigurationSettingKind.LOCALE)
    max_pending_soundboard_clips: Final = app_state.database.retrieve_configuration_setting(
        ConfigurationSettingKind.MAX_PENDING_SOUNDBOARD_CLIPS
    )
    max_pending_soundboard_clips_per_user: Final = app_state.database.retrieve_configuration_setting(
        ConfigurationSettingKind.MAX_PENDING_SOUNDBOARD_CLIPS_PER_USER
    )
    broadcaster_email_address: Final = app_state.database.retrieve_configuration_setting(
        ConfigurationSettingKind.BROADCASTER_EMAIL_ADDRESS
    )

    context: Final = AdminGeneralSettingsContext(
        **common_context.model_dump(),
        active_page=ActivePage.GENERAL_SETTINGS,
        current_bot_name=bot_name,
        current_author_name=author_name,
        current_timezone=timezone,
        current_locale=locale,
        current_max_pending_soundboard_clips=max_pending_soundboard_clips,
        current_max_pending_soundboard_clips_per_user=max_pending_soundboard_clips_per_user,
        current_broadcaster_email_address=broadcaster_email_address,
        available_timezones=_get_common_timezones(),
        available_locales=_get_common_locales(),
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/general_settings.html",
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
    max_pending_soundboard_clips: Annotated[str, Form()],
    max_pending_soundboard_clips_per_user: Annotated[str, Form()],
    broadcaster_email_address: Annotated[str, Form()] = "",
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

    # Validate max_pending_soundboard_clips is a non-negative integer
    try:
        max_clips = int(max_pending_soundboard_clips.strip())
        if max_clips < 0:
            raise HTTPException(
                status_code=400,
                detail="Max pending soundboard clips must be a non-negative integer",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="Max pending soundboard clips must be a non-negative integer",
        ) from e

    # Validate max_pending_soundboard_clips_per_user is a non-negative integer
    try:
        max_clips_per_user = int(max_pending_soundboard_clips_per_user.strip())
        if max_clips_per_user < 0:
            raise HTTPException(
                status_code=400,
                detail="Max pending soundboard clips per user must be a non-negative integer",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="Max pending soundboard clips per user must be a non-negative integer",
        ) from e

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
    app_state.database.store_configuration_setting(
        ConfigurationSettingKind.MAX_PENDING_SOUNDBOARD_CLIPS,
        str(max_clips),
    )
    app_state.database.store_configuration_setting(
        ConfigurationSettingKind.MAX_PENDING_SOUNDBOARD_CLIPS_PER_USER,
        str(max_clips_per_user),
    )

    app_state.database.store_configuration_setting(
        ConfigurationSettingKind.BROADCASTER_EMAIL_ADDRESS,
        broadcaster_email_address.strip(),
    )

    return RedirectResponse(request.url_for("admin_general_settings"), status_code=303)


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


@router.get("/live-notifications", name="admin_live_notifications")
async def admin_live_notifications(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
) -> Response:
    """Admin dashboard page for managing live notifications."""
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

    context: Final = AdminLiveNotificationsContext(
        **common_context.model_dump(),
        active_page=ActivePage.LIVE_NOTIFICATIONS,
        channels=channels,
        discord_text_channels=discord_text_channels,
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/live_notifications.html",
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
    return RedirectResponse(request.url_for("admin_live_notifications"), status_code=303)


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
    return RedirectResponse(request.url_for("admin_live_notifications"), status_code=303)


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
    return RedirectResponse(request.url_for("admin_live_notifications"), status_code=303)


@router.get("/soundboard", name="admin_soundboard")
async def admin_soundboard(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
) -> Response:
    """Admin dashboard page for viewing soundboard clips."""
    db_commands = app_state.database.get_soundboard_commands()
    soundboard_commands: Final = sorted(
        (
            SoundboardCommand(
                command=cmd.name,
                clip_url=f"/{RELATIVE_SOUNDBOARD_FILES_DIRECTORY.as_posix()}/{cmd.filename}",
                uploader_twitch_login=cmd.uploader_twitch_login,
                uploader_twitch_display_name=cmd.uploader_twitch_display_name,
            )
            for cmd in db_commands
        ),
        key=lambda cmd: cmd.command,
    )

    existing_commands: Final = [command.lower() for command in app_state.command_handlers]

    context: Final = AdminSoundboardContext(
        **common_context.model_dump(),
        active_page=ActivePage.SOUNDBOARD,
        soundboard_commands=soundboard_commands,
        existing_commands=existing_commands,
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/soundboard.html",
        context=context.model_dump(),
    )


@router.post("/soundboard/upload", name="upload_soundboard_clip")
async def upload_soundboard_clip(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    current_user: Annotated[UserInfo, Depends(get_broadcaster_user)],
    command_name: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
) -> Response:
    """Upload a new soundboard clip."""
    command_name = command_name.strip().lstrip("!")
    if not command_name:
        raise HTTPException(status_code=400, detail="Command name cannot be empty")

    if command_name.lower() in (name.lower() for name in app_state.command_handlers):
        raise HTTPException(status_code=400, detail=f"Command '!{command_name}' already exists")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    try:
        contents: Final = await file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}") from e

    detected_extension: Final = await get_file_extension_by_mime_type(contents)
    if detected_extension is None:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format.",
        )

    unique_filename: Final = f"{uuid4()}{detected_extension}"
    file_path: Final = SOUNDBOARD_FILES_DIRECTORY / unique_filename

    SOUNDBOARD_FILES_DIRECTORY.mkdir(parents=True, exist_ok=True)

    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}") from e

    try:
        app_state.database.add_soundboard_command(
            name=command_name,
            filename=unique_filename,
            uploader_twitch_id=current_user.id,
            uploader_twitch_login=current_user.login,
            uploader_twitch_display_name=current_user.display_name,
        )
    except ValueError as e:
        # If database insertion fails, clean up the file.
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e)) from e

    app_state.reload_command_handlers()

    return RedirectResponse(request.url_for("admin_soundboard"), status_code=303)


@router.post("/soundboard/update/{old_command_name}", name="update_soundboard_command")
async def update_soundboard_command(
    request: Request,
    old_command_name: str,
    app_state: Annotated[AppState, Depends(get_app_state)],
    command_name: Annotated[str, Form()],
) -> Response:
    """Update a soundboard command name."""
    new_command_name = command_name.strip().lower().replace("!", "")

    if not new_command_name:
        raise HTTPException(status_code=400, detail="Command name cannot be empty")

    # Check if we're just changing case or if it's actually the same.
    if new_command_name.lower() == old_command_name.lower():
        # Just a case change or no change, allow it.
        try:
            app_state.database.update_soundboard_command_name(old_name=old_command_name, new_name=new_command_name)
        except (ValueError, KeyError) as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
    else:
        # Different command name, check for duplicates.
        try:
            app_state.database.update_soundboard_command_name(old_name=old_command_name, new_name=new_command_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    app_state.reload_command_handlers()

    return RedirectResponse(request.url_for("admin_soundboard"), status_code=303)


@router.post("/soundboard/delete/{command_name}", name="delete_soundboard_clip")
async def delete_soundboard_clip(
    request: Request,
    command_name: str,
    app_state: Annotated[AppState, Depends(get_app_state)],
) -> Response:
    """Delete a soundboard clip."""
    soundboard_commands: Final = app_state.database.get_soundboard_commands()
    command = next((c for c in soundboard_commands if c.name.lower() == command_name.lower()), None)

    if command is None:
        raise HTTPException(status_code=404, detail="Soundboard command not found")

    file_path: Final = SOUNDBOARD_FILES_DIRECTORY / command.filename
    try:
        file_path.unlink(missing_ok=True)
    except Exception as e:
        logger.exception(f"Warning: Failed to delete file {file_path}: {e}")

    if not app_state.database.remove_command_case_insensitive(name=command.name):
        raise HTTPException(status_code=500, detail="Failed to delete command from database")

    app_state.reload_command_handlers()

    return RedirectResponse(request.url_for("admin_soundboard"), status_code=303)


@router.get("/pending-clips", name="admin_pending_clips")
async def admin_pending_clips(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
) -> Response:
    """Admin dashboard page for reviewing pending soundboard clips."""
    all_pending_clips: Final = app_state.database.get_all_pending_soundboard_clips()

    pending_clips: Final = sorted(
        [
            PendingClip(
                id=clip.id,
                command=clip.name,
                clip_url=f"/{RELATIVE_SOUNDBOARD_FILES_DIRECTORY.as_posix()}/{clip.filename}",
                may_persist_uploader_info=clip.may_persist_uploader_info,
                uploader_twitch_login=clip.uploader_twitch_login,
                uploader_twitch_display_name=clip.uploader_twitch_display_name,
            )
            for clip in all_pending_clips
            if clip.id is not None
        ],
        key=lambda c: c.command,
    )

    context: Final = AdminPendingClipsContext(
        **common_context.model_dump(),
        active_page=ActivePage.PENDING_CLIPS,
        pending_clips=pending_clips,
        existing_commands=[name.lower() for name in app_state.command_handlers],
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/pending_clips.html",
        context=context.model_dump(),
    )


@router.post("/pending-clips/approve/{clip_id}", name="approve_pending_clip")
async def approve_pending_clip(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    clip_id: int,
    command_name: Annotated[str, Form()],
) -> Response:
    """Approve a pending soundboard clip and add it to the soundboard."""
    # Get the pending clip.
    all_pending_clips: Final = app_state.database.get_all_pending_soundboard_clips()
    pending_clip = next((clip for clip in all_pending_clips if clip.id == clip_id), None)

    if pending_clip is None:
        raise HTTPException(status_code=404, detail="Pending clip not found")

    command_name = command_name.strip().lstrip("!")
    if not command_name:
        raise HTTPException(status_code=400, detail="Command name cannot be empty")

    if command_name.lower() in (name.lower() for name in app_state.command_handlers):
        raise HTTPException(status_code=400, detail=f"Command '!{command_name}' already exists")

    # Add to soundboard commands.
    try:
        app_state.database.add_soundboard_command(
            name=command_name,
            filename=pending_clip.filename,
            uploader_twitch_id=(pending_clip.uploader_twitch_id if pending_clip.may_persist_uploader_info else None),
            uploader_twitch_login=(
                pending_clip.uploader_twitch_login if pending_clip.may_persist_uploader_info else None
            ),
            uploader_twitch_display_name=(
                pending_clip.uploader_twitch_display_name if pending_clip.may_persist_uploader_info else None
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        app_state.database.remove_pending_soundboard_clip(id_=clip_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    app_state.reload_command_handlers()

    return RedirectResponse(request.url_for("admin_pending_clips"), status_code=303)


@router.post("/pending-clips/reject/{clip_id}", name="reject_pending_clip")
async def reject_pending_clip(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    clip_id: int,
) -> Response:
    """Reject and delete a pending soundboard clip."""
    try:
        app_state.database.remove_pending_soundboard_clip(id_=clip_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return RedirectResponse(request.url_for("admin_pending_clips"), status_code=303)


@router.get("/entrance-sounds", name="admin_entrance_sounds")
async def admin_entrance_sounds(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
) -> Response:
    entry_sounds: Final = app_state.database.get_all_entry_sounds()
    users_by_id: Final = await get_twitch_user_info_by_ids(
        user_ids=[entrance_sound.twitch_user_id for entrance_sound in entry_sounds],
        app_state=app_state,
    )

    entrance_sounds: Final = sorted(
        (
            EntranceSound(
                twitch_user_id=entrance_sound.twitch_user_id,
                twitch_display_name=users_by_id[entrance_sound.twitch_user_id].display_name,
                twitch_url=f"https://twitch.tv/{users_by_id[entrance_sound.twitch_user_id].login}",
                clip_url=f"/{RELATIVE_SOUNDBOARD_FILES_DIRECTORY.as_posix()}/{entrance_sound.filename}",
            )
            for entrance_sound in entry_sounds
        ),
        key=lambda entry: entry.twitch_display_name,
    )

    admin_context: Final = AdminContext(
        **common_context.model_dump(),
        active_page=ActivePage.ENTRANCE_SOUNDS,
    )

    context: Final = AdminEntranceSoundsContext(
        **admin_context.model_dump(),
        entrance_sounds=entrance_sounds,
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/entrance_sounds.html",
        context=context.model_dump(),
    )


@final
class _ValidateTwitchUserSuccessResponse(BaseModel):
    valid: Literal[True] = True
    user_id: str
    profile_image_url: str


@final
class _ValidateTwitchUserErrorResponse(BaseModel):
    valid: Literal[False] = False
    error: str


@router.get("/api/validate-twitch-user", name="validate_twitch_user")
async def validate_twitch_user(
    username: str,
    app_state: Annotated[AppState, Depends(get_app_state)],
) -> _ValidateTwitchUserSuccessResponse | _ValidateTwitchUserErrorResponse:
    """Validate a Twitch username and return user ID if found."""
    login: Final = username.lower()
    users: Final = await get_twitch_user_info_by_logins([login], app_state)
    if len(users) != 1:
        return _ValidateTwitchUserErrorResponse(
            valid=False,
            error="User not found",
        )
    user: Final = next(iter(users.values()))
    return _ValidateTwitchUserSuccessResponse(
        valid=True,
        user_id=user.id,
        profile_image_url=user.profile_image_url,
    )


@router.post("/entrance-sounds/upload", name="upload_entrance_sound")
async def upload_entrance_sound(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    twitch_user_id: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
) -> Response:
    """Upload a new entrance sound for a user."""
    try:
        contents: Final = await file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}") from e

    detected_extension: Final = await get_file_extension_by_mime_type(contents)
    if detected_extension is None:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format.",
        )

    unique_filename: Final = f"{uuid4()}{detected_extension}"
    file_path: Final = SOUNDBOARD_FILES_DIRECTORY / unique_filename

    SOUNDBOARD_FILES_DIRECTORY.mkdir(parents=True, exist_ok=True)

    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}") from e

    try:
        app_state.database.add_entrance_sound(
            twitch_user_id=twitch_user_id,
            filename=unique_filename,
        )
    except ValueError as e:
        # If database insertion fails, clean up the file.
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e)) from e

    return RedirectResponse(request.url_for("admin_entrance_sounds"), status_code=303)


@router.post("/entrance-sounds/{twitch_user_id}/update", name="update_entrance_sound")
async def update_entrance_sound(
    request: Request,
    twitch_user_id: str,
    app_state: Annotated[AppState, Depends(get_app_state)],
) -> Response:
    """Update an entrance sound for a specific user."""
    # TODO: Implement entrance sound update logic
    return RedirectResponse(request.url_for("admin_entrance_sounds"), status_code=303)


@router.post("/entrance-sounds/{twitch_user_id}/delete", name="delete_entrance_sound")
async def delete_entrance_sound(
    request: Request,
    twitch_user_id: str,
    app_state: Annotated[AppState, Depends(get_app_state)],
) -> Response:
    """Delete an entrance sound for a specific user."""
    # TODO: Implement entrance sound deletion logic
    return RedirectResponse(request.url_for("admin_entrance_sounds"), status_code=303)
