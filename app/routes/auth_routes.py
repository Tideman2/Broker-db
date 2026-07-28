
from fastapi import APIRouter, Depends
from app.services import user_services
from app.Models.auth_models import User, LoginUserRequest, RefreshTokenRequest
from app.utils.jwt import get_current_user

auth_router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@auth_router.post("/register")
def register_user(payload: User):
    """
     function to register user, this function,
     this function will also validate the incoming payload
    """
    response = user_services.create_user(payload)
    return response


@auth_router.post("/login")
def login_user(payload: LoginUserRequest):
    """
     Route handler to login user,
     this function will also validate the incoming payload
    """
    response = user_services.check_if_email_and_password_is_correct(payload)
    return response


@auth_router.get("/user/{user_id}")
def fetch_user(user_id: int, user=Depends(get_current_user)):
    """
     Route handler to get user,
     this function will also validate the incoming payload
     and enforce jwt auth
    """
    return user_services.get_user(user_id)


@auth_router.post("/refresh")
def refresh_token(data: RefreshTokenRequest, user=Depends(get_current_user)):
    """
    Route handler sign a new token with the user id and full name
    """
    new_token = user_services.generate_new_token(data.token)
    return {"token": new_token}


@auth_router.delete("/user/{user_id}")
def delete_user(user_id: int, user=Depends(get_current_user)):
    """
     Route handler to delete user,
     this function will also validate the incoming payload
     and enforce jwt auth
    """
    return user_services.delete_user(user_id)
