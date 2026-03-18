from fastapi import status, Depends
from fastapi import APIRouter

from app.dependencies import get_current_user
from app.models.user import User
from app.settings.schema import ProfileResponse, VerifyWhatsappRequest, WhatsappLinkRequest
from app.schemas.common import ResponseModel
from app.utils.send_whatsapp import send_whatsapp_message, verify_otp
from app.core.config import settings

router = APIRouter(prefix='/settings', tags=["Settings"])


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
            can_verify=False,
            phone=current_user.phone or '',
            created_at=current_user.created_at.isoformat(),
            chat_number=settings.CHAT_NUMBER if current_user.is_phone_linked else None
        )
    )


@router.post('/whatsapp-link', status_code=status.HTTP_201_CREATED, response_model=ResponseModel)
async def link_whatsapp(request: WhatsappLinkRequest, current_user: User = Depends(get_current_user)):
    phone = request.phone

    # Update user phone
    current_user.phone = phone
    await current_user.save()

    # Send SMS OTP via Twilio Verify API (Twilio generates the OTP automatically)
    send_whatsapp_message(phone, None)

    return ResponseModel(
        success=True,
        message="SMS OTP sent successfully",
        data={"phone": phone}
    )


@router.post('/phone/verify', status_code=status.HTTP_200_OK, response_model=ResponseModel)
async def verify_phone(request: VerifyWhatsappRequest, current_user: User = Depends(get_current_user)):
    # Verify OTP using Twilio Verify API
    if not current_user.phone:
        return ResponseModel(
            success=False,
            message="Phone number not found. Please link your phone first."
        )

    is_valid = verify_otp(current_user.phone, request.otp)

    if not is_valid:
        return ResponseModel(
            success=False,
            message="Invalid or expired OTP"
        )

    # Update user phone verification status
    current_user.is_phone_linked = True
    await current_user.save()

    return ResponseModel(
        success=True,
        message="WhatsApp verified successfully"
    )
