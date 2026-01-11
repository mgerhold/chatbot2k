from datetime import UTC
from datetime import datetime
from typing import Final

from pydantic import BaseModel
from starlette.templating import Jinja2Templates

from chatbot2k.app_state import AppState
from chatbot2k.utils.email import send_email


async def notify_user(
    *,
    twitch_user_id: str,
    templates: Jinja2Templates,
    notification_template_name: str,
    notification_template_context: BaseModel,
    email_template_name: str,
    email_subject: str,
    email_template_context: BaseModel,
    app_state: AppState,
) -> None:
    app_state.database.add_notification(
        twitch_user_id=twitch_user_id,
        message=templates.get_template(notification_template_name).render(notification_template_context.model_dump()),  # type: ignore[reportUnknownMemberType]
        sent_at=datetime.now(UTC),
    )
    user_profile: Final = app_state.database.get_user_profile(twitch_user_id=twitch_user_id)
    if user_profile is None or user_profile.email is None:
        return
    await send_email(
        to_address=user_profile.email,
        subject=email_subject,
        template=templates.get_template(email_template_name),  # type: ignore[reportUnknownMemberType]
        context=email_template_context,
        settings=app_state.config.smtp_settings,
    )
