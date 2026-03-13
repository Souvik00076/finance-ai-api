import logging

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)

resend.api_key = settings.RESEND_API_KEY


def send_email(to: str, subject: str, body: str) -> None:
    """
    Send an email using Resend.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body (HTML supported).

    Returns:
        Resend API response dict with the email id.

    Raises:
        Exception: If sending fails.
    """
    try:
        response = resend.Emails.send(
            {
                "from": settings.RESEND_FROM_EMAIL,
                "to": [to],
                "subject": subject,
                "html": body,
            }
        )
        logger.info("Email sent to %s (id: %s)", to, response.get("id"))
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        raise
