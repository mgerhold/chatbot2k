import logging
from datetime import UTC
from datetime import datetime
from enum import StrEnum
from typing import Annotated
from typing import Final
from typing import NamedTuple
from typing import Optional
from typing import Self
from typing import cast
from typing import final
from uuid import uuid4

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import Query
from fastapi import UploadFile
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from chatbot2k.app_state import AppState
from chatbot2k.constants import RELATIVE_SOUNDBOARD_FILES_DIRECTORY
from chatbot2k.constants import SOUNDBOARD_FILES_DIRECTORY
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_authenticated_user
from chatbot2k.dependencies import get_common_context
from chatbot2k.dependencies import get_templates
from chatbot2k.types.configuration_setting_kind import ConfigurationSettingKind
from chatbot2k.types.template_contexts import CommonContext
from chatbot2k.types.template_contexts import NewPendingClipEmailContext
from chatbot2k.types.template_contexts import Notification
from chatbot2k.types.template_contexts import PendingClip
from chatbot2k.types.template_contexts import VerifyEmailContext
from chatbot2k.types.template_contexts import ViewerContext
from chatbot2k.types.template_contexts import ViewerDashboardActivePage
from chatbot2k.types.template_contexts import ViewerNotificationsContext
from chatbot2k.types.template_contexts import ViewerProfileContext
from chatbot2k.types.template_contexts import ViewerSoundboardContext
from chatbot2k.types.user_info import UserInfo
from chatbot2k.utils.email import send_email
from chatbot2k.utils.mime_types import get_file_extension_by_mime_type

router: Final = APIRouter(prefix="/viewer", dependencies=[Depends(get_authenticated_user)])

logger: Final = logging.getLogger(__name__)


@final
class ProfileMessage(StrEnum):
    """Messages to display on the profile page."""

    EMAIL_VERIFICATION_SENT = "email_verification_sent"
    EMAIL_VERIFIED = "email_verified"
    PROFILE_DELETED = "profile_deleted"
    PROFILE_UPDATED = "profile_updated"
    ERROR = "error"


@router.get("/", name="viewer_dashboard")
async def viewer_dashboard(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    current_user: Annotated[UserInfo, Depends(get_authenticated_user)],
) -> Response:
    """Redirect to viewer soundboard page."""
    notifications: Final = app_state.database.get_notifications(twitch_user_id=current_user.id)
    if notifications:
        return RedirectResponse(request.url_for("viewer_dashboard_notifications"), status_code=303)
    else:
        return RedirectResponse(request.url_for("viewer_soundboard"), status_code=303)


@router.get("/notifications", name="viewer_dashboard_notifications")
async def viewer_dashboard_notifications(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
    current_user: Annotated[UserInfo, Depends(get_authenticated_user)],
) -> Response:
    notifications: Final = app_state.database.get_notifications(twitch_user_id=current_user.id)
    return templates.TemplateResponse(
        request=request,
        name="viewer/notifications.html",
        context=ViewerNotificationsContext(
            **common_context.model_dump(),
            active_page=ViewerDashboardActivePage.NOTIFICATIONS,
            notifications=[
                Notification(
                    id=cast(int, notification.id),  # This cannot be `None` here when coming from the DB.
                    twitch_user_id=notification.twitch_user_id,
                    message=notification.message,
                    sent_at=notification.sent_at,
                    has_been_read=notification.has_been_read,
                )
                for notification in notifications
            ],
        ).model_dump(),
    )


@router.post("/notifications/mark-as-read/{notification_id}", name="mark_notifications_as_read")
async def mark_notifications_as_read(
    app_state: Annotated[AppState, Depends(get_app_state)],
    current_user: Annotated[UserInfo, Depends(get_authenticated_user)],
    notification_id: int,
) -> Response:
    """Mark a notification as read (delete it)."""
    notifications: Final = app_state.database.get_notification(notification_id=notification_id)
    if notifications is None or notifications.twitch_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")

    app_state.database.mark_notification_as_read(notification_id=notification_id)
    return Response(status_code=200)


@router.post("/notifications/mark-as-unread/{notification_id}", name="mark_notifications_as_unread")
async def mark_notifications_as_unread(
    app_state: Annotated[AppState, Depends(get_app_state)],
    current_user: Annotated[UserInfo, Depends(get_authenticated_user)],
    notification_id: int,
) -> Response:
    """Mark a notification as unread (re-add it)."""
    notifications: Final = app_state.database.get_notification(notification_id=notification_id)
    if notifications is None or notifications.twitch_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")

    app_state.database.mark_notification_as_unread(notification_id=notification_id)
    return Response(status_code=200)


@router.post("/notifications/delete/{notification_id}", name="delete_notification")
async def delete_notification(
    app_state: Annotated[AppState, Depends(get_app_state)],
    current_user: Annotated[UserInfo, Depends(get_authenticated_user)],
    notification_id: int,
) -> Response:
    """Delete a notification."""
    notifications: Final = app_state.database.get_notification(notification_id=notification_id)
    if notifications is None or notifications.twitch_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")

    app_state.database.delete_notification(notification_id=notification_id)
    return Response(status_code=200)


def _get_message_text(message: ProfileMessage) -> str:
    match message:
        case ProfileMessage.EMAIL_VERIFICATION_SENT:
            return "Please verify your email address. We've sent an email containing a verification link."
        case ProfileMessage.EMAIL_VERIFIED:
            return "Your email address has been successfully verified!"
        case ProfileMessage.PROFILE_DELETED:
            return "Profile data has been deleted."
        case ProfileMessage.PROFILE_UPDATED:
            return "Profile has been updated successfully."
        case ProfileMessage.ERROR:
            return "An error occurred while processing your request."


@router.get("/profile", name="viewer_dashboard_profile")
async def viewer_dashboard_profile(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
    current_user: Annotated[UserInfo, Depends(get_authenticated_user)],
    message: Annotated[Optional[ProfileMessage], Query()] = None,
) -> Response:
    user_profile: Final = app_state.database.get_user_profile(twitch_user_id=current_user.id)
    viewer_context: Final = ViewerContext(**common_context.model_dump(), active_page=ViewerDashboardActivePage.PROFILE)

    message_text: Final = None if message is None else _get_message_text(message)

    context: Final = ViewerProfileContext(
        **viewer_context.model_dump(),
        email=None if user_profile is None else user_profile.email,
        email_is_verified=False if user_profile is None else user_profile.email_is_verified,
        message=message_text,
    )
    return templates.TemplateResponse(
        request=request,
        name="viewer/profile.html",
        context=context.model_dump(),
    )


@router.post("/profile", name="update_viewer_profile")
async def update_viewer_profile(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    current_user: Annotated[UserInfo, Depends(get_authenticated_user)],
    email: Annotated[Optional[str], Form()],
) -> Response:
    email = None if email is None else email.strip().lower()
    if email is None or not email:
        email = None

    app_state.database.upsert_user_profile(
        twitch_user_id=current_user.id,
        email=email,
    )

    message_type: ProfileMessage
    if email is not None:
        token: Final = uuid4().hex
        app_state.database.add_email_verification_token(
            token=token,
            twitch_user_id=current_user.id,
            created_at=datetime.now(UTC),
        )
        await send_email(
            to_address=email,
            subject="Verify Your Email Address",
            template=templates.get_template("emails/verify_email.txt.j2"),  # type: ignore[reportUnknownMemberType]
            context=VerifyEmailContext(
                user_name=current_user.display_name,
                verification_link=str(request.url_for("verify_email", token=token)),
                bot_name=app_state.database.retrieve_configuration_setting_or_default(
                    ConfigurationSettingKind.BOT_NAME, f"Chatbot of {app_state.config.twitch_channel}"
                ),
            ),
            settings=app_state.config.smtp_settings,
        )
        message_type = ProfileMessage.EMAIL_VERIFICATION_SENT
    else:
        message_type = ProfileMessage.PROFILE_UPDATED

    redirect_url: Final = request.url_for("viewer_dashboard_profile").include_query_params(message=message_type)
    return RedirectResponse(redirect_url, status_code=303)


@router.post("/profile/delete", name="viewer_delete_profile")
async def viewer_delete_profile(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    current_user: Annotated[UserInfo, Depends(get_authenticated_user)],
) -> Response:
    app_state.database.delete_user_profile(twitch_user_id=current_user.id)

    redirect_url: Final = request.url_for("viewer_dashboard_profile").include_query_params(
        message=ProfileMessage.PROFILE_DELETED
    )
    return RedirectResponse(redirect_url, status_code=303)


@router.get("/verify-email/{token}", name="verify_email", dependencies=[])
async def verify_email(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    token: str,
) -> Response:
    """Verify a user's email address using a verification token."""
    verification_token: Final = app_state.database.get_email_verification_token(token=token)

    if verification_token is None:
        error_url: Final = request.url_for("viewer_dashboard_profile").include_query_params(
            message=ProfileMessage.ERROR
        )
        return RedirectResponse(error_url, status_code=303)

    # Ensure created_at is timezone-aware (UTC)
    created_at: Final = (
        verification_token.created_at
        if verification_token.created_at.tzinfo is not None
        else verification_token.created_at.replace(tzinfo=UTC)
    )
    token_age: Final = datetime.now(UTC) - created_at
    if token_age.total_seconds() > 24 * 60 * 60:  # 24 hours.
        app_state.database.delete_email_verification_token(token=token)
        expired_url: Final = request.url_for("viewer_dashboard_profile").include_query_params(
            message=ProfileMessage.ERROR
        )
        return RedirectResponse(expired_url, status_code=303)

    try:
        app_state.database.mark_email_as_verified(twitch_user_id=verification_token.twitch_user_id)
        app_state.database.delete_email_verification_token(token=token)
    except KeyError:
        profile_error_url: Final = request.url_for("viewer_dashboard_profile").include_query_params(
            message=ProfileMessage.ERROR
        )
        return RedirectResponse(profile_error_url, status_code=303)

    success_url: Final = request.url_for("viewer_dashboard_profile").include_query_params(
        message=ProfileMessage.EMAIL_VERIFIED
    )
    return RedirectResponse(success_url, status_code=303)


@final
class _ClipsConfigurationLimits(NamedTuple):
    max_clips: int
    max_clips_per_user: int

    @classmethod
    def get(cls, app_state: AppState) -> Self:
        max_clips_str: Final = app_state.database.retrieve_configuration_setting(
            ConfigurationSettingKind.MAX_PENDING_SOUNDBOARD_CLIPS
        )
        max_clips_per_user_str: Final = app_state.database.retrieve_configuration_setting(
            ConfigurationSettingKind.MAX_PENDING_SOUNDBOARD_CLIPS_PER_USER
        )

        if (
            max_clips_str is None
            or not max_clips_str
            or not max_clips_str.isdigit()
            or int(max_clips_str) <= 0
            or max_clips_per_user_str is None
            or not max_clips_per_user_str
            or not max_clips_per_user_str.isdigit()
            or int(max_clips_per_user_str) <= 0
        ):
            raise HTTPException(
                status_code=500,
                detail="Soundboard configuration is invalid. Please contact the administrator.",
            )

        return cls(
            max_clips=int(max_clips_str),
            max_clips_per_user=int(max_clips_per_user_str),
        )


@router.get("/soundboard", name="viewer_soundboard")
async def viewer_soundboard(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    common_context: Annotated[CommonContext, Depends(get_common_context)],
    current_user: Annotated[UserInfo, Depends(get_authenticated_user)],
) -> Response:
    """Viewer soundboard page for uploading pending clips."""
    limits: Final = _ClipsConfigurationLimits.get(app_state)

    total_pending_count: Final = app_state.database.get_number_of_pending_soundboard_clips()
    user_pending_clips: Final = app_state.database.get_pending_soundboard_clips_by_twitch_user_id(
        twitch_user_id=current_user.id
    )
    user_pending_count: Final = len(user_pending_clips)

    user_can_upload: Final = total_pending_count < limits.max_clips and user_pending_count < limits.max_clips_per_user

    pending_clips: Final = sorted(
        (
            PendingClip(
                id=clip.id,
                command=clip.name,
                clip_url=f"/{RELATIVE_SOUNDBOARD_FILES_DIRECTORY.as_posix()}/{clip.filename}",
                may_persist_uploader_info=clip.may_persist_uploader_info,
                uploader_twitch_login=clip.uploader_twitch_login,
                uploader_twitch_display_name=clip.uploader_twitch_display_name,
            )
            for clip in user_pending_clips
            if clip.id is not None  # Should never happen, but needed to satisfy the type checker.
        ),
        key=lambda c: c.command,
    )

    context: Final = ViewerSoundboardContext(
        **common_context.model_dump(),
        active_page=ViewerDashboardActivePage.SOUNDBOARD,
        max_pending_clips=limits.max_clips,
        max_pending_clips_per_user=limits.max_clips_per_user,
        total_pending_clips=total_pending_count,
        user_pending_clips_count=user_pending_count,
        user_can_upload=user_can_upload,
        pending_clips=pending_clips,
    )

    return templates.TemplateResponse(
        request=request,
        name="viewer/soundboard.html",
        context=context.model_dump(),
    )


@router.post("/soundboard/upload", name="upload_pending_soundboard_clip")
async def upload_pending_soundboard_clip(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    current_user: Annotated[UserInfo, Depends(get_authenticated_user)],
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
    command_name: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    agree_terms: Annotated[str, Form()],
    may_persist_uploader_info: Annotated[str, Form()] = "off",
) -> Response:
    """Upload a pending soundboard clip."""
    # Validate terms agreement.
    if agree_terms != "on":
        raise HTTPException(
            status_code=400,
            detail="You must agree to the terms before uploading a clip",
        )

    limits: Final = _ClipsConfigurationLimits.get(app_state)

    total_pending: Final = app_state.database.get_number_of_pending_soundboard_clips()
    if total_pending >= limits.max_clips:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum number of pending clips ({limits.max_clips}) reached. Please try again later.",
        )

    user_pending_clips: Final = app_state.database.get_pending_soundboard_clips_by_twitch_user_id(
        twitch_user_id=current_user.id
    )
    if len(user_pending_clips) >= limits.max_clips_per_user:
        raise HTTPException(
            status_code=400,
            detail=f"You have reached your limit of {limits.max_clips_per_user} pending clips.",
        )

    command_name = command_name.strip().lstrip("!")
    if not command_name:
        raise HTTPException(status_code=400, detail="Command name cannot be empty")

    # Validate file
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
        app_state.database.add_pending_soundboard_clip(
            name=command_name,
            filename=unique_filename,
            uploader_twitch_id=current_user.id,
            uploader_twitch_login=current_user.login,
            uploader_twitch_display_name=current_user.display_name,
            may_persist_uploader_info=(may_persist_uploader_info == "on"),
        )
    except ValueError as e:
        # If database insertion fails, clean up the file.
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e)) from e

    to_address: Final = app_state.database.retrieve_configuration_setting(
        ConfigurationSettingKind.BROADCASTER_EMAIL_ADDRESS
    )
    if to_address is None or not to_address:
        logger.error(
            "Broadcaster email address is not configured; cannot send notification "
            + "email for new pending soundboard clip."
        )
    else:
        await send_email(
            to_address=to_address,
            subject="New Soundboard Clip Upload",
            template=templates.get_template("emails/new_pending_clip.txt.j2"),  # type: ignore[reportUnknownMemberType]
            context=NewPendingClipEmailContext(
                broadcaster_name=app_state.config.twitch_channel,
                uploader_display_name=current_user.display_name,
                uploader_id=current_user.id,
                command_name=command_name,
                dashboard_url=str(request.url_for("admin_pending_clips")),
                bot_name=app_state.database.retrieve_configuration_setting_or_default(
                    ConfigurationSettingKind.BOT_NAME, f"Chatbot of {app_state.config.twitch_channel}"
                ),
            ),
            settings=app_state.config.smtp_settings,
        )

    return RedirectResponse(request.url_for("viewer_soundboard"), status_code=303)


@router.post("/soundboard/update/{clip_id}", name="update_pending_soundboard_clip")
async def update_pending_soundboard_clip(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    current_user: Annotated[UserInfo, Depends(get_authenticated_user)],
    clip_id: int,
    command_name: Annotated[str, Form()],
    may_persist_uploader_info: Annotated[str, Form()] = "off",
) -> Response:
    """Update a pending soundboard clip's name and visibility preference."""
    # Verify the clip belongs to the current user.
    user_pending_clips: Final = app_state.database.get_pending_soundboard_clips_by_twitch_user_id(
        twitch_user_id=current_user.id
    )
    if not any(clip.id == clip_id for clip in user_pending_clips):
        raise HTTPException(status_code=404, detail="Clip not found or access denied")

    command_name = command_name.strip().lstrip("!")
    if not command_name:
        raise HTTPException(status_code=400, detail="Command name cannot be empty")

    try:
        app_state.database.update_pending_soundboard_clip(
            id_=clip_id,
            name=command_name,
            may_persist_uploader_info=(may_persist_uploader_info == "on"),
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return RedirectResponse(request.url_for("viewer_soundboard"), status_code=303)


@router.post("/soundboard/delete/{clip_id}", name="delete_pending_soundboard_clip")
async def delete_pending_soundboard_clip(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
    current_user: Annotated[UserInfo, Depends(get_authenticated_user)],
    clip_id: int,
) -> Response:
    """Delete a pending soundboard clip."""
    # Verify the clip belongs to the current user.
    user_pending_clips: Final = app_state.database.get_pending_soundboard_clips_by_twitch_user_id(
        twitch_user_id=current_user.id
    )
    if not any(clip.id == clip_id for clip in user_pending_clips):
        raise HTTPException(status_code=404, detail="Clip not found or access denied")

    try:
        app_state.database.remove_pending_soundboard_clip(id_=clip_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return RedirectResponse(request.url_for("viewer_soundboard"), status_code=303)
