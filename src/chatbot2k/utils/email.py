import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Final
from typing import Optional

from jinja2 import Template
from pydantic import BaseModel

from chatbot2k.types.smtp_settings import SmtpCryptoKind
from chatbot2k.types.smtp_settings import SmtpSettings

logger: Final = logging.getLogger(__name__)


def _send_email_impl(
    to_address: str,
    subject: str,
    template: Template,
    context: Optional[BaseModel],
    settings: SmtpSettings,
    timeout: float = 30.0,
) -> None:
    message: Final = EmailMessage()
    message["From"] = settings.from_address
    message["To"] = to_address
    message["Subject"] = subject

    content = template.render(None if context is None else context.model_dump())
    message.set_content(content)

    ssl_context: Final = ssl.create_default_context()

    logger.info(f"Sending email to {to_address}...")

    match settings.crypto:
        case SmtpCryptoKind.SSL:
            with smtplib.SMTP_SSL(
                settings.host,
                settings.port,
                context=ssl_context,
                timeout=timeout,
            ) as smtp:
                smtp.login(settings.username, settings.password)
                smtp.send_message(message)
        case SmtpCryptoKind.TLS | SmtpCryptoKind.NONE:
            with smtplib.SMTP(
                settings.host,
                settings.port,
                timeout=timeout,
            ) as smtp:
                smtp.ehlo()
                if settings.crypto == SmtpCryptoKind.TLS:
                    smtp.starttls(context=ssl_context)
                    smtp.ehlo()
                smtp.login(settings.username, settings.password)
                smtp.send_message(message)

    logger.info(f"Email sent to {to_address}.")


async def send_email(
    to_address: str,
    subject: str,
    template: Template,
    context: Optional[BaseModel],
    settings: SmtpSettings,
    timeout: float = 30.0,
) -> None:
    await asyncio.to_thread(
        _send_email_impl,
        to_address,
        subject,
        template,
        context,
        settings,
        timeout,
    )
