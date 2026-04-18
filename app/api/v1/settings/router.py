from fastapi import status, Depends
from fastapi import APIRouter

from app.dependencies import get_current_user
from app.models import provider
from app.models.provider import ProviderEnum
from app.models.user import User
from app.models.user_data import UserData
from app.api.v1.settings.schema import ProfileResponse, VerifyProviderRequest, ProviderLinkRequest
from app.schemas.common import ResponseModel
from app.utils.send_whatsapp import send_whatsapp_message, verify_otp
from app.core.config import settings


router = APIRouter(prefix='/settings', tags=["Settings"])


async def _backfill_total_spent(user: User, chat_id: str) -> None:
    """If user's total_spent is 0, sum all historical item prices for the chat_id."""
    docs = await UserData.find({"chat_id": chat_id}).to_list()
    total = 0.0
    for doc in docs:
        for item in doc.items:
            total += item.price
    if total > 0:
        user.total_spent = total


@router.get("", status_code=status.HTTP_200_OK, response_model=ResponseModel[ProfileResponse])
async def profile_info(current_user: User = Depends(get_current_user)):
    """Get current user's profile information."""
    return ResponseModel(
        success=True,
        message="Profile retrieved successfully",
        data=ProfileResponse(
            email=current_user.email,
            full_name=current_user.full_name,
            picture=current_user.picture,
            provider=current_user.provider,
            email_verified=current_user.email_verified,
            is_phone_linked=current_user.is_phone_linked,
            is_telegram_linked=current_user.is_telegram_linked,
            can_verify=False,
            phone=current_user.phone or '',
            created_at=current_user.created_at.isoformat(),
            chat_number=settings.CHAT_NUMBER if current_user.is_phone_linked else None
        )
    )


@router.post('/whatsapp-link', status_code=status.HTTP_201_CREATED, response_model=ResponseModel)
async def link_whatsapp(request: ProviderLinkRequest, current_user: User = Depends(get_current_user)):
    phone = request.phone
    # Check if another user already linked this phone
    existing = await User.find_one(User.phone == phone, User.is_phone_linked == True)
    if existing and str(existing.id) != str(current_user.id):
        return ResponseModel(
            success=False,
            message="This phone number is already linked to another account"
        )
    # Update user phone
    current_user.phone = phone
    # Backfill total_spent if not yet calculated
    await current_user.save()
    # Send SMS OTP via Twilio Verify API (Twilio generates the OTP automatically)
    send_whatsapp_message(phone, None)
    return ResponseModel(
        success=True,
        message="SMS OTP sent successfully",
        data={"phone": phone}
    )


@router.post('/telegram-link', status_code=status.HTTP_201_CREATED,
             response_model=ResponseModel)
async def link_telegram(request: ProviderLinkRequest,
                        current_user: User = Depends(get_current_user)):
    phone = request.phone
    # Check if another user already linked this telegram
    existing = await User.find_one(User.telegram_id == phone, User.is_telegram_linked == True)
    if existing and str(existing.id) != str(current_user.id):
        return ResponseModel(
            success=False,
            message="This Telegram ID is already linked to another account"
        )
    current_user.telegram_id = phone
    current_user.is_telegram_linked = True
    # Backfill total_spent if not yet calculated
    await _backfill_total_spent(current_user, phone)
    await current_user.save()
    return ResponseModel(
        success=True,
        message="OTP is sent to the telegram chat account",
        data={"phone": phone}
    )


@router.post('/phone/verify', status_code=status.HTTP_200_OK, response_model=ResponseModel)
async def verify_phone(request: VerifyProviderRequest,
                       current_user: User = Depends(get_current_user)):
    # Verify OTP using Twilio Verify API
    if not current_user.phone:
        return ResponseModel(
            success=False,
            message="Phone number not found. Please link your phone first."
        )
    is_valid = verify_otp(current_user.phone, request.otp)
    current_user.is_phone_linked = True

    if not is_valid:
        return ResponseModel(
            success=False,
            message="Invalid or expired OTP"
        )

    await _backfill_total_spent(current_user, current_user.phone)
    # Update user phone verification status
    await current_user.save()

    return ResponseModel(
        success=True,
        message="WhatsApp verified successfully"
    )
