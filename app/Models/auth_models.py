from enum import Enum
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, TypedDict


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class Admin(BaseModel):
    email: str
    password: str = Field(
        min_length=8,
        max_length=100
    )


class CurrentUser(BaseModel):
    user_id: int
    role: UserRole


class User(BaseModel):
    """
    User class extending pydantic Base model
    """
    country: str

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=100
    )

    full_name: str = Field(
        min_length=2,
        max_length=100
    )

    phone: str = Field(
        min_length=8,
        max_length=20
    )

    dob: Optional[str] = None

    username: Optional[str] = Field(
        default=None,
        min_length=3
    )

    address1: str = Field(min_length=3)
    address2: Optional[str] = None

    city: str = Field(min_length=2)
    state: str = Field(min_length=2)

    zip: str = Field(min_length=3)

    accept_terms: bool
    marketing_opt_in: Optional[bool] = False


class CreateUserResponse(TypedDict):
    """
     Create user service response type
    """
    id: int
    message: str
    token: str


class LoginUserRequest(BaseModel):
    """
    Login user request type
    """
    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=100
    )


class RefreshTokenRequest(BaseModel):
    token: str
