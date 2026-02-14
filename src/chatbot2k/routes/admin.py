import logging
from typing import Annotated
from typing import Final
from typing import Literal
from typing import cast
from typing import final
from uuid import uuid4

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from pydantic import BaseModel
from pydantic import field_validator
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from chatbot2k.app_state import AppState
from chatbot2k.constants import RELATIVE_SOUNDBOARD_FILES_DIRECTORY
from chatbot2k.constants import SOUNDBOARD_FILES_DIRECTORY
from chatbot2k.database.engine import TwitchUserVariants
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_broadcaster_user
from chatbot2k.dependencies import get_common_context
from chatbot2k.dependencies import get_templates
from chatbot2k.types.configuration_setting_kind import ConfigurationSettingKind
from chatbot2k.types.template_contexts import AdminBroadcastsContext
from chatbot2k.types.template_contexts import AdminConstantsContext
from chatbot2k.types.template_contexts import AdminContext
from chatbot2k.types.template_contexts import AdminDashboardActivePage
from chatbot2k.types.template_contexts import AdminEntranceSoundsContext
from chatbot2k.types.template_contexts import AdminEventActionsContext
from chatbot2k.types.template_contexts import AdminGeneralSettingsContext
from chatbot2k.types.template_contexts import AdminLiveNotificationsContext
from chatbot2k.types.template_contexts import AdminPendingClipsContext
from chatbot2k.types.template_contexts import AdminSoundboardContext
from chatbot2k.types.template_contexts import Broadcast
from chatbot2k.types.template_contexts import ClipApprovedContext
from chatbot2k.types.template_contexts import ClipApprovedEmailContext
from chatbot2k.types.template_contexts import ClipRejectedContext
from chatbot2k.types.template_contexts import ClipRejectedEmailContext
from chatbot2k.types.template_contexts import CommonContext
from chatbot2k.types.template_contexts import Constant
from chatbot2k.types.template_contexts import EntranceSound
from chatbot2k.types.template_contexts import LiveNotificationChannel
from chatbot2k.types.template_contexts import PendingClip
from chatbot2k.types.template_contexts import RaidEventAction
from chatbot2k.types.template_contexts import RaidEventUserInfo
from chatbot2k.types.template_contexts import SoundboardCommand
from chatbot2k.types.user_info import UserInfo
from chatbot2k.utils.discord import get_available_discord_text_channels
from chatbot2k.utils.mime_types import get_file_extension_by_mime_type
from chatbot2k.utils.notifications import notify_user
from chatbot2k.utils.time_and_locale import get_common_locales
from chatbot2k.utils.time_and_locale import get_common_timezones
from chatbot2k.utils.twitch import get_twitch_user_by_login
from chatbot2k.utils.twitch import get_twitch_user_info_by_ids
from chatbot2k.utils.twitch import get_twitch_user_info_by_logins

router: Final = APIRouter(prefix="/admin", dependencies=[Depends(get_broadcaster_user)])

logger: Final = logging.getLogger(__name__)

# region General Settings


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
    current_script_execution_timeout_string: Final = app_state.database.retrieve_configuration_setting_or_raise(
        ConfigurationSettingKind.SCRIPT_EXECUTION_TIMEOUT,
    )

    if (
        not current_script_execution_timeout_string
        or not current_script_execution_timeout_string.isdigit()
        or int(current_script_execution_timeout_string) < 1
    ):
        raise HTTPException(status_code=500, detail="Invalid script execution timeout configuration")

    context: Final = AdminGeneralSettingsContext(
        **common_context.model_dump(),
        active_page=AdminDashboardActivePage.GENERAL_SETTINGS,
        current_bot_name=bot_name,
        current_author_name=author_name,
        current_timezone=timezone,
        current_locale=locale,
        current_max_pending_soundboard_clips=max_pending_soundboard_clips,
        current_max_pending_soundboard_clips_per_user=max_pending_soundboard_clips_per_user,
        current_broadcaster_email_address=broadcaster_email_address,
        current_script_execution_timeout=int(current_script_execution_timeout_string),
        available_timezones=get_common_timezones(),
        available_locales=get_common_locales(),
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
    script_execution_timeout: Annotated[str, Form()],
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

    # Validate max_pending_soundboard_clips is a non-negative integer.
    try:
        max_clips: Final = int(max_pending_soundboard_clips.strip())
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

    # Validate max_pending_soundboard_clips_per_user is a non-negative integer.
    try:
        max_clips_per_user: Final = int(max_pending_soundboard_clips_per_user.strip())
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

    # Validate script_execution_timeout is a positive integer.
    try:
        timeout_seconds: Final = int(script_execution_timeout.strip())
        if timeout_seconds < 1:
            raise HTTPException(status_code=400, detail="Script execution timeout must be a positive integer")
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="Script execution timeout must be a positive integer",
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

    app_state.database.store_configuration_setting(
        ConfigurationSettingKind.SCRIPT_EXECUTION_TIMEOUT,
        str(timeout_seconds),
    )

    return RedirectResponse(request.url_for("admin_general_settings"), status_code=303)


# endregion

# region Constants


@router.get("/constants", name="admin_constants")
async def admin_constants(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
) -> Response:
    admin_context: Final = AdminContext(
        **common_context.model_dump(),
        active_page=AdminDashboardActivePage.CONSTANTS,
    )
    constants: Final = sorted(
        (
            Constant(
                name=constant.name,
                text=constant.text,
            )
            for constant in app_state.database.get_constants()
        ),
        key=lambda c: c.name,
    )
    context: Final = AdminConstantsContext(
        **admin_context.model_dump(),
        constants=constants,
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/constants.html",
        context=context.model_dump(),
    )


@router.post("/constants/add", name="add_constant")
async def add_constant(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    constant_name: Annotated[str, Form()],
    constant_text: Annotated[str, Form()],
) -> Response:
    """Add a new constant."""
    try:
        app_state.database.add_constant(name=constant_name, text=constant_text)
        logger.info(f"Added constant: {constant_name}")
    except ValueError as e:
        logger.error(f"Failed to add constant: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RedirectResponse(
        url=request.app.url_path_for("admin_constants"),
        status_code=303,
    )


@router.post("/constants/{old_constant_name}/update", name="update_constant")
async def update_constant(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    old_constant_name: str,
    constant_name: Annotated[str, Form()],
    constant_text: Annotated[str, Form()],
) -> Response:
    """Update an existing constant."""
    try:
        app_state.database.remove_constant(name=old_constant_name)
        app_state.database.add_constant(name=constant_name, text=constant_text)
        logger.info(f"Renamed constant: {old_constant_name} -> {constant_name}")
    except (ValueError, KeyError) as e:
        logger.error(f"Failed to update constant: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RedirectResponse(
        url=request.app.url_path_for("admin_constants"),
        status_code=303,
    )


@router.post("/constants/{constant_name}/delete", name="delete_constant")
async def delete_constant(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    constant_name: str,
) -> Response:
    """Delete a constant."""
    try:
        app_state.database.remove_constant(name=constant_name)
        logger.info(f"Deleted constant: {constant_name}")
    except KeyError as e:
        logger.error(f"Failed to delete constant: {e}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    return RedirectResponse(
        url=request.app.url_path_for("admin_constants"),
        status_code=303,
    )


# endregion

# region Broadcasts


@router.get("/broadcasts", name="admin_broadcasts")
async def admin_broadcasts(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
) -> Response:
    """Admin dashboard page for managing broadcasts."""
    admin_context: Final = AdminContext(
        **common_context.model_dump(),
        active_page=AdminDashboardActivePage.BROADCASTS,
    )
    broadcasts: Final = sorted(
        (
            Broadcast(
                id=broadcast.id,
                interval_seconds=broadcast.interval_seconds,
                message=broadcast.message,
                alias_command=broadcast.alias_command,
            )
            for broadcast in app_state.database.get_broadcasts()
            if broadcast.id is not None
        ),
        key=lambda b: b.id,
    )
    static_commands: Final = sorted([f"!{cmd.name}" for cmd in app_state.database.get_static_commands()])
    context: Final = AdminBroadcastsContext(
        **admin_context.model_dump(),
        broadcasts=broadcasts,
        static_commands=static_commands,
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/broadcasts.html",
        context=context.model_dump(),
    )


@router.post("/broadcasts/add", name="add_broadcast")
async def add_broadcast(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    interval_seconds: Annotated[int, Form()],
    message: Annotated[str, Form()],
    alias_command: Annotated[str, Form()] = "",
    enable_alias: Annotated[str, Form()] = "",
) -> Response:
    """Add a new broadcast."""
    try:
        if interval_seconds < 1:
            raise HTTPException(status_code=400, detail="Interval must be at least 1 second")

        # Only set alias_command if checkbox is enabled and a command is selected.
        final_alias_command: Final = alias_command.strip() if enable_alias and alias_command.strip() else None

        if final_alias_command is not None and (
            not final_alias_command.startswith("!")
            or not any(
                final_alias_command.removeprefix("!") == command.name
                for command in app_state.database.get_static_commands()
            )
        ):
            raise HTTPException(status_code=400, detail="Invalid alias command selected")

        app_state.database.add_broadcast(
            interval_seconds=interval_seconds,
            message=message,
            alias_command=final_alias_command,
        )
        logger.info(f"Added broadcast with interval {interval_seconds}s")
    except ValueError as e:
        logger.error(f"Failed to add broadcast: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    await app_state.reload_broadcasters()
    return RedirectResponse(
        url=request.app.url_path_for("admin_broadcasts"),
        status_code=303,
    )


@router.post("/broadcasts/{broadcast_id}/update", name="update_broadcast")
async def update_broadcast(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    broadcast_id: int,
    interval_seconds: Annotated[int, Form()],
    message: Annotated[str, Form()],
    alias_command: Annotated[str, Form()] = "",
) -> Response:
    """Update an existing broadcast."""
    try:
        if interval_seconds < 1:
            raise HTTPException(status_code=400, detail="Interval must be at least 1 second")

        # Empty string means no alias.
        final_alias_command = alias_command.strip() if alias_command.strip() else None

        if final_alias_command is not None and (
            not final_alias_command.startswith("!")
            or not any(
                final_alias_command.removeprefix("!") == command.name
                for command in app_state.database.get_static_commands()
            )
        ):
            raise HTTPException(status_code=400, detail="Invalid alias command selected")

        app_state.database.update_broadcast(
            id_=broadcast_id,
            interval_seconds=interval_seconds,
            message=message,
            alias_command=final_alias_command,
        )
        logger.info(f"Updated broadcast {broadcast_id}")
    except (ValueError, KeyError) as e:
        logger.error(f"Failed to update broadcast: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    await app_state.reload_broadcasters()
    return RedirectResponse(
        url=request.app.url_path_for("admin_broadcasts"),
        status_code=303,
    )


@router.post("/broadcasts/{broadcast_id}/delete", name="delete_broadcast")
async def delete_broadcast(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    broadcast_id: int,
) -> Response:
    """Delete a broadcast."""
    try:
        app_state.database.remove_broadcast(id_=broadcast_id)
        logger.info(f"Deleted broadcast {broadcast_id}")
    except KeyError as e:
        logger.error(f"Failed to delete broadcast: {e}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    await app_state.reload_broadcasters()
    return RedirectResponse(
        url=request.app.url_path_for("admin_broadcasts"),
        status_code=303,
    )


# endregion

# region Live Notifications


@router.get("/live-notifications", name="admin_live_notifications")
async def admin_live_notifications(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
) -> Response:
    """Admin dashboard page for managing live notifications."""
    database_entries: Final = app_state.database.get_live_notification_channels()
    user_info_by_id: Final = await get_twitch_user_info_by_ids(
        user_ids=[entry.broadcaster_id for entry in database_entries],
        app_state=app_state,
    )
    channels: Final = sorted(
        (
            LiveNotificationChannel(
                notification_channel_id=cast(int, channel.id),  # This can never be `None` here.
                broadcaster_name=user_info_by_id[channel.broadcaster_id].display_name,
                broadcaster_id=channel.broadcaster_id,
                broadcaster_profile_image_url=user_info_by_id[channel.broadcaster_id].profile_image_url,
                broadcaster_twitch_url=f"https://twitch.tv/{user_info_by_id[channel.broadcaster_id].login}",
                text_template=channel.text_template,
                target_channel=channel.target_channel,
            )
            for channel in database_entries
        ),
        key=lambda entry: entry.broadcaster_name,
    )
    discord_text_channels: Final = await get_available_discord_text_channels(app_state)

    context: Final = AdminLiveNotificationsContext(
        **common_context.model_dump(),
        active_page=AdminDashboardActivePage.LIVE_NOTIFICATIONS,
        channels=channels,
        discord_text_channels=discord_text_channels,
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/live_notifications.html",
        context=context.model_dump(),
    )


@router.post("/live-notifications/add", name="add_live_notification_channel")
async def add_live_notification_channel(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    broadcaster_name: Annotated[str, Form()],
    text_template: Annotated[str, Form()],
    target_channel: Annotated[str, Form()],
) -> Response:
    """Add a new live notification channel."""
    broadcaster: Final = await get_twitch_user_by_login(broadcaster_name.lower(), app_state)
    if broadcaster is None:
        raise HTTPException(status_code=400, detail="Broadcaster not found")
    try:
        app_state.database.add_live_notification_channel(
            broadcaster_id=broadcaster.id,
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
    text_template: Annotated[str, Form()],
    target_channel: Annotated[str, Form()],
) -> Response:
    """Update an existing live notification channel."""
    try:
        app_state.database.update_live_notification_channel(
            id_=channel_id,
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


# endregion

# region Soundboard


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
        active_page=AdminDashboardActivePage.SOUNDBOARD,
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


@final
class _UpdateSoundboardVolumeRequest(BaseModel):
    volume: float

    @field_validator("volume", mode="after")
    @classmethod
    def validate_volume_range(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("Volume must be between 0.0 and 1.0")
        return v


@router.post("/soundboard/volume/{command_name}", name="update_soundboard_clip_volume")
async def update_soundboard_clip_volume(
    command_name: str,
    request_data: _UpdateSoundboardVolumeRequest,
    app_state: Annotated[AppState, Depends(get_app_state)],
) -> Response:
    """Update the volume of a soundboard clip."""
    try:
        app_state.database.update_soundboard_command_volume(name=command_name, volume=request_data.volume)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return Response(status_code=200)


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


# endregion

# region Pending Clips


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
        active_page=AdminDashboardActivePage.PENDING_CLIPS,
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
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    clip_id: int,
    command_name: Annotated[str, Form()],
) -> Response:
    """Approve a pending soundboard clip and add it to the soundboard."""
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

    await notify_user(
        twitch_user_id=pending_clip.uploader_twitch_id,
        templates=templates,
        notification_template_name="notifications/clip_approved.txt.j2",
        notification_template_context=ClipApprovedContext(
            suggested_command=f"!{pending_clip.name}",
            approved_command=f"!{command_name}",
        ),
        email_template_name="emails/clip_approved.txt.j2",
        email_subject="Your soundboard clip has been approved!",
        email_template_context=ClipApprovedEmailContext(
            user_name=pending_clip.uploader_twitch_display_name,
            suggested_command=f"!{pending_clip.name}",
            approved_command=f"!{command_name}",
            bot_name=app_state.database.retrieve_configuration_setting_or_default(
                ConfigurationSettingKind.BOT_NAME, f"Chatbot of {app_state.config.twitch_channel}"
            ),
        ),
        app_state=app_state,
    )

    return RedirectResponse(request.url_for("admin_pending_clips"), status_code=303)


@router.post("/pending-clips/reject/{clip_id}", name="reject_pending_clip")
async def reject_pending_clip(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    clip_id: int,
    reason: Annotated[str, Form()] = "",
) -> Response:
    """Reject and delete a pending soundboard clip."""
    all_pending_clips: Final = app_state.database.get_all_pending_soundboard_clips()
    pending_clip = next((clip for clip in all_pending_clips if clip.id == clip_id), None)

    if pending_clip is None:
        raise HTTPException(status_code=404, detail="Pending clip not found")

    rejection_reason: Final = reason.strip() if reason else None

    await notify_user(
        twitch_user_id=pending_clip.uploader_twitch_id,
        templates=templates,
        notification_template_name="notifications/clip_rejected.txt.j2",
        notification_template_context=ClipRejectedContext(
            suggested_command=f"!{pending_clip.name}",
            reason=rejection_reason,
        ),
        email_template_name="emails/clip_rejected.txt.j2",
        email_subject="Your soundboard clip has been rejected",
        email_template_context=ClipRejectedEmailContext(
            user_name=pending_clip.uploader_twitch_display_name,
            suggested_command=f"!{pending_clip.name}",
            reason=rejection_reason,
            bot_name=app_state.database.retrieve_configuration_setting_or_default(
                ConfigurationSettingKind.BOT_NAME, f"Chatbot of {app_state.config.twitch_channel}"
            ),
        ),
        app_state=app_state,
    )

    try:
        app_state.database.remove_pending_soundboard_clip(id_=clip_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return RedirectResponse(request.url_for("admin_pending_clips"), status_code=303)


# endregion

# region Entrance Sounds


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
                twitch_profile_image_url=users_by_id[entrance_sound.twitch_user_id].profile_image_url,
                twitch_url=f"https://twitch.tv/{users_by_id[entrance_sound.twitch_user_id].login}",
                clip_url=f"/{RELATIVE_SOUNDBOARD_FILES_DIRECTORY.as_posix()}/{entrance_sound.filename}",
            )
            for entrance_sound in entry_sounds
        ),
        key=lambda entry: entry.twitch_display_name,
    )

    admin_context: Final = AdminContext(
        **common_context.model_dump(),
        active_page=AdminDashboardActivePage.ENTRANCE_SOUNDS,
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


@router.post("/entrance-sounds/{twitch_user_id}/delete", name="delete_entrance_sound")
async def delete_entrance_sound(
    request: Request,
    twitch_user_id: str,
    app_state: Annotated[AppState, Depends(get_app_state)],
) -> Response:
    """Delete an entrance sound for a specific user."""
    entrance_sound: Final = app_state.database.get_entrance_sound_by_twitch_user_id(twitch_user_id=twitch_user_id)
    if entrance_sound is None:
        raise HTTPException(
            status_code=400,
            detail="Failed to delete entrance sound because it does not exist.",
        )
    file_path: Final = SOUNDBOARD_FILES_DIRECTORY / entrance_sound.filename
    try:
        file_path.unlink(missing_ok=True)
    except Exception as e:
        logger.exception(f"Warning: Failed to delete file {file_path}: {e}")

    try:
        app_state.database.delete_entrance_sound(twitch_user_id=twitch_user_id)
    except Exception as e:
        logger.exception(f"Failed to delete entrance sound from database: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete entrance sound from database") from e

    return RedirectResponse(request.url_for("admin_entrance_sounds"), status_code=303)


@router.post("/entrance-sounds/reset-session", name="reset_entry_sounds_session")
async def reset_entry_sounds_session(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
) -> Response:
    app_state.entrance_sound_handler.reset_entrance_sounds_session()
    return RedirectResponse(request.url_for("admin_entrance_sounds"), status_code=303)


# endregion

# region Event Actions


@router.get("/event-actions", name="admin_event_actions")
async def admin_event_actions(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
) -> Response:
    """Admin dashboard page for managing event actions (raid events)."""
    database_entries: Final = app_state.database.get_raid_event_actions()

    # Get Twitch user info for all non-general entries.
    user_ids: Final = [entry.twitch_user_id for entry in database_entries if entry.twitch_user_id is not None]
    user_info_by_id: Final = await get_twitch_user_info_by_ids(
        user_ids=user_ids,
        app_state=app_state,
    )

    # Build raid event actions list.
    raid_event_actions: Final = sorted(
        (
            RaidEventAction(
                id=cast(int, entry.id),
                twitch_user_info=None
                if entry.twitch_user_id is None
                else RaidEventUserInfo(
                    twitch_user_id=entry.twitch_user_id,
                    twitch_user_login=user_info_by_id[entry.twitch_user_id].login,
                    twitch_display_name=user_info_by_id[entry.twitch_user_id].display_name,
                    twitch_profile_image_url=user_info_by_id[entry.twitch_user_id].profile_image_url,
                    twitch_url=f"https://twitch.tv/{user_info_by_id[entry.twitch_user_id].login}",
                ),
                chat_message_to_send=entry.chat_message_to_send,
                soundboard_clip_to_play=entry.soundboard_clip_to_play,
                should_shoutout=entry.should_shoutout,
            )
            for entry in database_entries
        ),
        key=lambda entry: (
            not entry.is_general_entry,
            "" if entry.twitch_user_info is None else entry.twitch_user_info.twitch_display_name,
        ),
    )

    # Get all soundboard commands for the dropdown.
    soundboard_commands: Final = sorted([f"!{cmd.name}" for cmd in app_state.database.get_soundboard_commands()])

    # Check if a general entry already exists.
    has_general_entry: Final = any(action.is_general_entry for action in raid_event_actions)

    context: Final = AdminEventActionsContext(
        **common_context.model_dump(),
        active_page=AdminDashboardActivePage.EVENT_ACTIONS,
        raid_event_actions=raid_event_actions,
        soundboard_commands=soundboard_commands,
        has_general_entry=has_general_entry,
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/event_actions.html",
        context=context.model_dump(),
    )


@router.post("/event-actions/add", name="add_event_action")
async def add_event_action(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    entry_type: Annotated[Literal["general", "specific"], Form()],
    twitch_user_id: Annotated[str, Form()] = "",
    chat_message: Annotated[str, Form()] = "",
    soundboard_clip: Annotated[str, Form()] = "",
    should_shoutout: Annotated[str, Form()] = "",
) -> Response:
    """Add a new raid event action."""
    if entry_type not in ("general", "specific"):
        raise HTTPException(status_code=400, detail="Invalid entry type")

    # For general entries, check if one already exists.
    if entry_type == "general":
        general_raid_event_action: Final = app_state.database.get_general_raid_event_action()
        if general_raid_event_action is not None:
            raise HTTPException(status_code=400, detail="A general raid action already exists")
        target_user_id = TwitchUserVariants.ALL_USERS
    else:
        if not twitch_user_id.strip():
            raise HTTPException(status_code=400, detail="Twitch user ID is required for specific entries")
        target_user_id = twitch_user_id.strip()

    # Validate that at least one action is specified
    chat_msg: Final = chat_message.strip() if chat_message.strip() else None
    soundboard: Final = soundboard_clip.strip().removeprefix("!") if soundboard_clip.strip().removeprefix("!") else None
    shoutout: Final = should_shoutout == "on"

    if chat_msg is None and soundboard is None and not shoutout:
        raise HTTPException(
            status_code=400,
            detail="At least one action must be specified (chat message, soundboard clip, or shoutout)",
        )

    try:
        app_state.database.add_raid_event_action(
            twitch_user_id=target_user_id,
            chat_message_to_send=chat_msg,
            soundboard_clip_to_play=soundboard,
            should_shoutout=shoutout,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return RedirectResponse(request.url_for("admin_event_actions"), status_code=303)


@router.post("/event-actions/update/{action_id}", name="update_event_action")
async def update_event_action(
    request: Request,
    action_id: int,
    app_state: Annotated[AppState, Depends(get_app_state)],
    chat_message: Annotated[str, Form()] = "",
    soundboard_clip: Annotated[str, Form()] = "",
    should_shoutout: Annotated[str, Form()] = "",
) -> Response:
    """Update an existing raid event action."""
    existing_action: Final = app_state.database.get_raid_event_action_by_id(id_=action_id)

    if existing_action is None:
        raise HTTPException(status_code=404, detail="Event action not found")

    target_user_id: Final = (
        TwitchUserVariants.ALL_USERS if existing_action.twitch_user_id is None else existing_action.twitch_user_id
    )

    # Validate that at least one action is specified
    chat_msg: Final = chat_message.strip() if chat_message.strip() else None
    soundboard: Final = soundboard_clip.strip().removeprefix("!") if soundboard_clip.strip().removeprefix("!") else None
    shoutout: Final = should_shoutout == "on"

    if chat_msg is None and soundboard is None and not shoutout:
        raise HTTPException(
            status_code=400,
            detail="At least one action must be specified (chat message, soundboard clip, or shoutout)",
        )

    try:
        app_state.database.update_raid_event_action(
            twitch_user_id=target_user_id,
            chat_message_to_send=chat_msg,
            soundboard_clip_to_play=soundboard,
            should_shoutout=shoutout,
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return RedirectResponse(request.url_for("admin_event_actions"), status_code=303)


@router.post("/event-actions/delete/{action_id}", name="delete_event_action")
async def delete_event_action(
    request: Request,
    action_id: int,
    app_state: Annotated[AppState, Depends(get_app_state)],
) -> Response:
    """Delete a raid event action."""
    existing_action: Final = app_state.database.get_raid_event_action_by_id(id_=action_id)

    if existing_action is None:
        raise HTTPException(status_code=404, detail="Event action not found")

    target_user_id: Final = (
        TwitchUserVariants.ALL_USERS if existing_action.twitch_user_id is None else existing_action.twitch_user_id
    )

    try:
        app_state.database.delete_raid_event_action(twitch_user_id=target_user_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return RedirectResponse(request.url_for("admin_event_actions"), status_code=303)


# endregion
