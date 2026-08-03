
from fastapi import APIRouter, Depends
from app.services import user_services
from app.Models.auth_models import Admin, LoginUserRequest
from app.utils.jwt import require_admin

admin_router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@admin_router.post("/register")
def register_admin(payload: Admin):
    """
     function to register Admin.
    """
    response = user_services.create_admin(payload)
    return response


@admin_router.post("/login")
def login_admin(payload: LoginUserRequest):
    """
     Route handler to admin loigin,
    """
    response = user_services.check_if_admin_email_and_password_is_correct(
        payload
    )

    return response
