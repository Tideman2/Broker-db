
from fastapi import APIRouter
from app.services import user_services
from app.Models.auth_models import Admin, LoginUserRequest

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
