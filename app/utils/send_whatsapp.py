import logging
from twilio.rest import Client

from app.core.config import settings

logger = logging.getLogger(__name__)

account_sid = settings.TWILIO_SID
account_token = settings.TWILIO_TOKEN
content_sid = settings.TWILIO_CONTENT_SID

client = Client(account_sid, account_token)


def send_whatsapp_message(to: str, otp: str) -> None:
    message = client.messages.create(
        from_='whatsapp:+14155238886',
        content_sid=content_sid,
        content_variables=f'{{"1":"{otp}"}}',
        to=f'whatsapp:{to}'
    )
    logger.info(
        f"WhatsApp message sent - SID: {message.sid}, To: {to}, Status: {message.status}")
