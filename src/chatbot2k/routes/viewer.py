import logging
from pathlib import Path
from typing import Annotated
from typing import Final
from typing import NamedTuple
from typing import Self
from typing import final
from uuid import uuid4

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from chatbot2k.app_state import AppState
from chatbot2k.constants import SOUNDBOARD_FILES_DIRECTORY
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_authenticated_user
from chatbot2k.dependencies import get_common_context
from chatbot2k.dependencies import get_templates
from chatbot2k.types.configuration_setting_kind import ConfigurationSettingKind
from chatbot2k.types.template_contexts import CommonContext
from chatbot2k.types.template_contexts import ViewerSoundboardContext
from chatbot2k.types.user_info import UserInfo

router: Final = APIRouter(prefix="/viewer", dependencies=[Depends(get_authenticated_user)])

logger: Final = logging.getLogger(__name__)


@router.get("/", name="viewer_dashboard")
async def viewer_dashboard(
    request: Request,
) -> Response:
    """Redirect to viewer soundboard page."""
    return RedirectResponse(request.url_for("viewer_soundboard"), status_code=303)


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

    context: Final = ViewerSoundboardContext(
        **common_context.model_dump(),
        active_page="soundboard",
        max_pending_clips=limits.max_clips,
        max_pending_clips_per_user=limits.max_clips_per_user,
        total_pending_clips=total_pending_count,
        user_pending_clips=user_pending_count,
        user_can_upload=user_can_upload,
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
    command_name: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    agree_terms: Annotated[str, Form()],
    may_persist_uploader_info: Annotated[str, Form()] = "off",
) -> Response:
    """Upload a pending soundboard clip."""
    # Validate terms agreement
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

    file_extension: Final = Path(file.filename).suffix
    if not file_extension:
        raise HTTPException(status_code=400, detail="File must have an extension")

    unique_filename: Final = f"{uuid4()}{file_extension}"
    file_path: Final = SOUNDBOARD_FILES_DIRECTORY / unique_filename

    SOUNDBOARD_FILES_DIRECTORY.mkdir(parents=True, exist_ok=True)

    try:
        contents: Final = await file.read()
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

    return RedirectResponse(request.url_for("viewer_soundboard"), status_code=303)
