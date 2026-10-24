
from fastapi import APIRouter, Depends, Query
from app.services import (
    user_services,
    admin_services,
    subscription_services,
    portfolio_services
)
from app.Models.auth_models import (
    Admin,
    AdminPublic,
    AdminUpdateRequest,
    AdminUserListItem,
    LoginUserRequest,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserResponse,
    VerifyOTPRequest
)
from app.Models.plans_models import SubscriptionResponse
from app.Models.portfolio_models import SubscriptionHoldingResponse
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
    response = await admin_services.create_admin(payload)
    return response


@admin_router.post("/login")
async def login_admin(payload: LoginUserRequest):
    """
     Route handler to admin loigin,
    """
    response = await admin_services.check_if_admin_email_and_password_is_correct(
        payload
    )

    return response


@admin_router.get("/me")
def fetch_admin(user=Depends(require_admin)):
    """
     Route handler to get current admin,
     enforces jwt auth and admin role
    """
    return admin_services.get_admin(admin_id=user.user_id)


@admin_router.post("/refresh")
async def refresh_admin_token(data: RefreshTokenRequest):
    """
    Route handler to sign a new admin token from an admin refresh token
    """
    new_token = await admin_services.generate_new_admin_token(data.token)
    return {"token": new_token}


@admin_router.post("/logout")
async def logout_admin(user=Depends(require_admin)):
    """
     Route handler to log out admin,
     deletes the session token from redis
    """
    return await admin_services.logout_admin(admin_id=user.user_id)


@admin_router.post("/forgot-password")
async def admin_forgot_password(payload: ForgotPasswordRequest):
    """
     Route handler to send otp to admin email for password reset
    """
    response = await admin_services.send_admin_password_reset_otp(payload.email)
    return response


@admin_router.post("/verify-otp")
async def admin_verify_otp(payload: VerifyOTPRequest):
    """
     Route handler to verify otp sent to admin email for password reset
    """
    response = await admin_services.verify_admin_password_reset_otp(payload.email, payload.otp)
    return response


@admin_router.post("/reset-password")
async def admin_reset_password(payload: ResetPasswordRequest):
    """
     Route handler to reset admin password
    """
    response = await admin_services.reset_admin_password(payload.email, payload.new_password, payload.reset_token)
    return response


# ======================================================
# USER MANAGEMENT
# ======================================================


@admin_router.get("/users", response_model=list[AdminUserListItem])
def list_users_endpoint(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(require_admin)
):
    """
    List paginated users for admin.
    """
    return admin_services.list_users(limit=limit, offset=offset)


@admin_router.get("/users/{user_id}", response_model=UserResponse)
def fetch_user_as_admin(
    user_id: int,
    user=Depends(require_admin)
):
    """
    Get a single user by id for admin.
    """
    return user_services.get_user(user_id=user_id)


@admin_router.get(
    "/users/{user_id}/subscriptions",
    response_model=list[SubscriptionResponse]
)
def list_user_subscriptions_endpoint(
    user_id: int,
    user=Depends(require_admin)
):
    """
    Get every subscription belonging to a user for admin.
    """
    return subscription_services.get_user_subscriptions_for_admin(
        user_id=user_id
    )


@admin_router.get(
    "/subscriptions/{subscription_id}/holdings",
    response_model=list[SubscriptionHoldingResponse]
)
def get_subscription_holdings_endpoint(
    subscription_id: int,
    user=Depends(require_admin)
):
    """
    Get the open positions held under one subscription for admin.
    """
    return portfolio_services.get_subscription_holdings(
        subscription_id=subscription_id
    )


@admin_router.delete("/users/{user_id}")
async def delete_user_as_admin_endpoint(
    user_id: int,
    user=Depends(require_admin)
):
    """
    Hard delete a user for admin.
    """
    return await admin_services.delete_user_as_admin(user_id=user_id)


# ======================================================
# ADMIN MANAGEMENT
# ======================================================


@admin_router.get("/list", response_model=list[AdminPublic])
def list_admins_endpoint(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(require_admin)
):
    """
    List paginated admins.
    """
    return admin_services.list_admins(limit=limit, offset=offset)


@admin_router.get("/{admin_id}", response_model=AdminPublic)
def fetch_admin_by_id(
    admin_id: int,
    user=Depends(require_admin)
):
    """
    Get a single admin by id.
    """
    return admin_services.get_admin(admin_id=admin_id)


@admin_router.patch("/{admin_id}", response_model=AdminPublic)
async def update_admin_endpoint(
    admin_id: int,
    payload: AdminUpdateRequest,
    user=Depends(require_admin)
):
    """
    Update an admin's email and/or password.
    """
    return await admin_services.update_admin(admin_id=admin_id, data=payload)


@admin_router.delete("/{admin_id}")
async def delete_admin_endpoint(
    admin_id: int,
    user=Depends(require_admin)
):
    """
    Delete another admin. Self-delete is rejected.
    """
    return await admin_services.delete_admin(
        admin_id=admin_id, current_admin_id=user.user_id
    )
