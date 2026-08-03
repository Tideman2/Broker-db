import os
import jwt
from dotenv import load_dotenv
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.Models.auth_models import UserRole, CurrentUser

# pylint: disable=no-member
load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')


def create_token(
    user_id: int,
    role: UserRole
):
    """
    function to create jwt token
    """
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=2)
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def decode_token(token: str):
    """
     function to decode jwt token and get payload
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Expired signature")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


security = HTTPBearer()


def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    """
    function to use as a wrapper for protected routes 
    """
    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

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
