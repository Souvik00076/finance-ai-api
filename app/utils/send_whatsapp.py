import logging
from twilio.rest import Client

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_twilio_client() -> Client:
    return Client(settings.TWILIO_SID, settings.TWILIO_TOKEN)


def send_whatsapp_message(to: str, otp: str | None = None) -> None:
    """Send SMS OTP using Twilio Verify API.

    Note: The otp parameter is kept for backward compatibility but is not used.
    Twilio Verify API automatically generates and sends the OTP.
    """
    try:
        client = get_twilio_client()
        verification = client.verify.v2.services(
            settings.TWILIO_VERIFY_SERVICE_SID
        ).verifications.create(
            to=to,
            channel='sms'
        )
        logger.info(
            f"SMS OTP sent via Verify API - SID: {verification.sid}, To: {to}, Status: {verification.status}")
    except Exception as e:
        logger.error(f"Failed to send SMS OTP to {to}: {e}")
        raise


def verify_otp(to: str, otp: str) -> bool:
    """Verify OTP using Twilio Verify API.

    Args:
        to: Phone number to verify (in E.164 format, e.g., +1234567890)
        otp: OTP code to verify

    Returns:
        bool: True if OTP is valid and verification successful, False otherwise
    """
    try:
        client = get_twilio_client()
        verification_check = client.verify.v2.services(
            settings.TWILIO_VERIFY_SERVICE_SID
        ).verification_checks.create(
            to=to,
            code=otp
        )

        logger.info(
            f"OTP verification attempt - To: {to}, Status: {verification_check.status}")

        # Twilio returns 'approved' status if OTP is valid
        if verification_check.status == 'approved':
            return True
        else:
            logger.warning(f"OTP verification failed for {
                           to}: {verification_check.status}")
            return False

    except Exception as e:
        logger.error(f"Failed to verify OTP for {to}: {e}")
        return False
