
from fastapi import APIRouter, Depends
from app.services import user_services
from app.Models.auth_models import (
    Admin,
    LoginUserRequest,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyOTPRequest
)
from app.utils.jwt import require_admin

admin_router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@admin_router.post("/register")
async def register_admin(payload: Admin):
    """
     function to register Admin.
    """
    response = await user_services.create_admin(payload)
    return response


@admin_router.post("/login")
async def login_admin(payload: LoginUserRequest):
    """
     Route handler to admin loigin,
    """
    response = await user_services.check_if_admin_email_and_password_is_correct(
        payload
    )

    return response


@admin_router.get("/me")
def fetch_admin(user=Depends(require_admin)):
    """
     Route handler to get current admin,
     enforces jwt auth and admin role
    """
    return user_services.get_admin(admin_id=user.user_id)


@admin_router.post("/refresh")
async def refresh_admin_token(data: RefreshTokenRequest):
    """
    Route handler to sign a new admin token from a refresh token
    """
    new_token = await user_services.generate_new_token(data.token)
    return {"token": new_token}


@admin_router.post("/logout")
async def logout_admin(user=Depends(require_admin)):
    """
     Route handler to log out admin,
     deletes the session token from redis
    """
    return await user_services.logout_admin(admin_id=user.user_id)


@admin_router.post("/forgot-password")
async def admin_forgot_password(payload: ForgotPasswordRequest):
    """
     Route handler to send otp to admin email for password reset
    """
    response = await user_services.send_admin_password_reset_otp(payload.email)
    return response


@admin_router.post("/verify-otp")
async def admin_verify_otp(payload: VerifyOTPRequest):
    """
     Route handler to verify otp sent to admin email for password reset
    """
    response = await user_services.verify_admin_password_reset_otp(payload.email, payload.otp)
    return response


@admin_router.post("/reset-password")
async def admin_reset_password(payload: ResetPasswordRequest):
    """
     Route handler to reset admin password
    """
    response = await user_services.reset_admin_password(payload.email, payload.new_password, payload.reset_token)
    return response
