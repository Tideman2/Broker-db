import os
import jwt
from dotenv import load_dotenv
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.Models.auth_models import UserRole, CurrentUser
from app.utils.redis import get_access_token_from_redis

# pylint: disable=no-member
load_dotenv()
ACCESS_SECRET_KEY = os.getenv('ACCESS_SECRET_KEY')
ACCESS_REFRESH_SECRET_KEY = os.getenv('ACCESS_REFRESH_SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')


def create_token(
    user_id: int,
    role: UserRole,
    SECRET_KEY: str,
    expiration_hours: int = 2
):
    """
    function to create jwt token
    Secret key is passed as an argument to the function to allow for different secret keys for access and refresh tokens
    expiration_hours is passed as an argument to the function to allow for different expiration times for access and refresh tokens
    """
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=expiration_hours)
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


def decode_token(token: str, type: str = "access"):
    """
     function to decode jwt token and get payload
    type is passed as an argument to the function to allow for different secret keys for access and refresh tokens
    """
    SECRET_KEY = ACCESS_SECRET_KEY if type == "access" else ACCESS_REFRESH_SECRET_KEY
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        which_token = ("access" if type ==
                       "access" else "refresh").capitalize()
        raise HTTPException(
            status_code=401, detail=f"{which_token} token has expired")

    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    token = credentials.credentials
    payload = decode_token(token)

    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    stored_token = await get_access_token_from_redis(str(user_id))

    if stored_token != token:
        raise HTTPException(
            status_code=401,
            detail="Token is not valid or has been revoked"
        )

    return CurrentUser(**payload)


def require_admin(user: CurrentUser = Depends(get_current_user)):
    """
    Check if user is admin
    """

    if user.role != UserRole.ADMIN:

        raise HTTPException(
            status_code=403,
            detail="Admin privileges required."
        )

    return user
