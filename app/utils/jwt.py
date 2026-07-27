import os
import jwt
from dotenv import load_dotenv
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# pylint: disable=no-member
load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')


def create_token(user_id: int, name: str):
    """
     function to create jwt token
    """
    print(user_id, name)
    payload = {
        "user_id": user_id,
        "name": name,
        "exp": datetime.utcnow() + timedelta(hours=2)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_token(token: str):
    """
     function to decode jwt token and get payload
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
     function to use as a wrapper for protected routes 
    """
    token = credentials.credentials
    print("token in wrapper: ", token)
    payload = decode_token(token)
    print("payload in wrapper: ", payload)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    print(payload, "payload")
    return payload
