from fastapi import HTTPException

from app.db.connection import get_connection
from app.Models.auth_models import (
    User,
    CreateUserResponse,
    LoginUserRequest,
    UserResponse,
    UserRole
)

from app.email import email_service
from app.templates import template_env

from app.Models.wallet_models import (
    AddBankDestinationRequest,
    AddCryptoDestinationRequest
)
from app.db.queries.user_queries import (
    INSERT_USER,
    INSERT_ADDRESS,
    GET_USER_BY_ID,
    GET_USER_BY_EMAIL,
    USER_EXISTS
)

from app.db.queries.admin_queries import (
    GET_ADMIN_BY_ID
)

from app.utils.wallet import (
    _create_wallet,
    _add_withdraw_destination,
    _add_bank_destination,
    _add_crypto_destination,
    _get_withdraw_destination,
    _validate_destination_label,
    _build_destination_response,
    _get_withdraw_destinations,
    _build_user_withdraw_destinations
)


from app.utils.password import hash_password, verify_password
from app.utils.jwt import (
    ACCESS_SECRET_KEY,
    ACCESS_REFRESH_SECRET_KEY,
    PASSWORD_RESET_SECRET_KEY,
    create_token, decode_token
)
from app.utils.redis import (
    store_access_token_in_redis,
    delete_access_token_from_redis,
    store_refresh_token_in_redis,
    get_refresh_token_from_redis,
    delete_refresh_token_from_redis,
    store_otp_secret_redis,
    get_otp_secret_redis,
    delete_otp_secret_redis,
    store_reset_password_token_redis,
    get_reset_password_token_redis,
    delete_reset_password_token_redis,
)

from app.utils.otp import (
    generate_otp,
    generate_otp_secret,
    verify_otp,
    OTP_INTERVAL
)


async def create_user(data: User) -> CreateUserResponse:
    """
     function that on boards a user to the system
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        hashed_password = hash_password(password=data.password)
        # Insert user
        cursor.execute(INSERT_USER, (
            data.email,
            data.full_name,
            data.phone,
            data.dob,
            data.username,
            data.accept_terms,
            data.marketing_opt_in,
            hashed_password
        ))

        user_id = cursor.lastrowid

        # Insert address
        cursor.execute(INSERT_ADDRESS, (
            user_id,
            data.address1,
            data.address2,
            data.city,
            data.state,
            data.zip,
            data.country
        ))

        # Create wallet for user
        _create_wallet(cursor, user_id)

        access_token = create_token(user_id, "USER", ACCESS_SECRET_KEY)

        await store_access_token_in_redis(
            user_id=str(user_id),
            access_token=access_token,
            expiration_seconds=7200  # 2 hours in seconds
        )

        # Refresh token valid for 7 days
        refresh_token = create_token(
            user_id, "USER", ACCESS_REFRESH_SECRET_KEY, expiration_hours=24*7)

        await store_refresh_token_in_redis(
            user_id=str(user_id),
            token=refresh_token,
            expiration_seconds=3600*24*7,
            user_role=UserRole.USER
        )

        # Handle sending welcome email
        template = template_env.get_template("welcome_aboard.html")

        html_content = template.render(
            email=data.email,
            username=data.username
        )

        email_service.send_email(
            to=data.email,
            subject="Welcome!",
            body=(
                f"Welcome to the platform, "
                f"{data.full_name}!"
            ),
            html_body=html_content
        )

        conn.commit()
        return {"id": user_id, "message": "User created", "token": access_token, "refresh_token": refresh_token}

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


def get_user(user_id) -> User:
    """
    function to get user info from db
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(GET_USER_BY_ID, (user_id,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        return UserResponse(
            id=user["user_id"],
            country=user["country"],
            email=user["email"],
            full_name=user["full_name"],
            phone=user["phone"],
            dob=user["dob"].strftime("%Y-%m-%d") if user["dob"] else None,
            username=user["username"],
            address1=user["address1"],
            address2=user["address2"],
            city=user["city"],
            state=user["state"],
            zip=user["zip"],
            role=user["role"]
        )

    except HTTPException:
        raise
    except Exception as e:
        if conn is not None:
            conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


async def check_if_email_and_password_is_correct(data: LoginUserRequest):
    """
    function to check if email is in db,
    and check password agaisnt hashed in db.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(GET_USER_BY_EMAIL, (data.email,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        user_exists = verify_password(data.password, user["password_hash"])
        if not user_exists:
            raise HTTPException(
                status_code=401,
                detail="Password is incorrect"
            )

        access_token = create_token(
            user["id"], user["role"], ACCESS_SECRET_KEY)

        # Store access token in Redis with 2 hours expiration
        await store_access_token_in_redis(
            user_id=str(user["id"]),
            access_token=access_token,
            expiration_seconds=7200  # 2 hours in seconds
        )

        # Refresh token valid for 7 days
        refresh_token = create_token(
            user["id"], user["role"], ACCESS_REFRESH_SECRET_KEY, expiration_hours=24*7)

        await store_refresh_token_in_redis(
            user_id=str(user["id"]),
            token=refresh_token,
            expiration_seconds=3600*24*7,
            user_role=UserRole.USER
        )

        return {"user_id": user["id"], "token": access_token, "refresh_token": refresh_token}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        print(e)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    finally:
        cursor.close()
        conn.close()


async def generate_new_token(token: str, allow_admin: bool = False) -> str:
    """
    function that checks if the token is valid
    and generates a new token from same payload
    """
    user = decode_token(token, type="refresh")
    user_id = user["user_id"]
    role = user["role"]

    if role == UserRole.ADMIN and not allow_admin:
        raise HTTPException(
            status_code=403,
            detail="Use the admin refresh endpoint."
        )

    if role != UserRole.ADMIN:
        stored_refresh = await get_refresh_token_from_redis(
            str(user_id), user_role=UserRole.USER)

        if stored_refresh != token:
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token"
            )

    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        if role == UserRole.ADMIN:
            cursor.execute(GET_ADMIN_BY_ID, (user_id,))
        else:
            cursor.execute(USER_EXISTS, (user_id,))

        if not cursor.fetchone():
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token"
            )
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

    access_token = create_token(
        user_id, role, ACCESS_SECRET_KEY)

    await store_access_token_in_redis(
        user_id=str(user_id),
        access_token=access_token,
        expiration_seconds=7200,  # 2 hours in seconds
        user_role=role
    )
    return access_token


async def logout_user(user_id: int):
    """
    function to log out a user by deleting the session
    and refresh tokens from redis
    """
    await delete_access_token_from_redis(
        user_id=str(user_id),
        user_role=UserRole.USER
    )
    await delete_refresh_token_from_redis(
        user_id=str(user_id),
        user_role=UserRole.USER
    )
    return {"message": "User logged out"}


def delete_user(user_id: int):
    """
    function to delete user from db
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()

        return {"message": "User deleted"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    finally:
        cursor.close()
        conn.close()


def add_bank_withdraw_destination(user_id: int, destination: AddBankDestinationRequest):
    """
    Add bank withdraw destination
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        label = destination.destination_details.label
        destination_type = destination.destination_details.type

        # Destination label is unique by user
        _validate_destination_label(cursor, label, user_id)

        # Add withdraw destination to db
        _add_withdraw_destination(cursor, user_id, label, destination_type)

        # Add bank destination to db
        destination_id = cursor.lastrowid
        _add_bank_destination(cursor, destination_id,
                              destination.bank_destination)

        newly_created_destination = _get_withdraw_destination(
            cursor, destination_id)
        conn.commit()

        return _build_destination_response(newly_created_destination)

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    finally:
        cursor.close()
        conn.close()


def add_crypto_withdraw_destination(user_id: int, destination: AddCryptoDestinationRequest):
    """
    Add crypto withdraw destination
    """
    print("Whaaaaaaatttstst")
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        label = destination.destination_details.label
        destination_type = destination.destination_details.type

        # Destination label is unique by user
        _validate_destination_label(cursor, label, user_id)

        # Add withdraw destination to db
        _add_withdraw_destination(cursor, user_id, label, destination_type)

        # Add crypto destination to db
        destination_id = cursor.lastrowid
        _add_crypto_destination(cursor, destination_id,
                                destination.crypto_destination)

        newly_created_destination = _get_withdraw_destination(
            cursor, destination_id)
        conn.commit()

        return _build_destination_response(newly_created_destination)

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    finally:
        cursor.close()
        conn.close()


def get_withdraw_destinations(
        user_id: int
):
    """
    Get a user withdraw destinations.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        destinations = _get_withdraw_destinations(cursor, user_id)

        return _build_user_withdraw_destinations(destinations)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


# ============================
# PASSWORD RESET
# ============================

async def send_password_reset_otp(email: str):
    """
    Function to send a password reset OTP to the user's email.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check if user exists
        cursor.execute(GET_USER_BY_EMAIL, (email,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # Generate OTP
        otp_secret = generate_otp_secret()
        otp = generate_otp(otp_secret)
        # Store OTP secret in Redis with 5 minutes expiration
        await store_otp_secret_redis(user["id"], otp_secret)

        # Send OTP email
        template = template_env.get_template("otp_mail.html")
        html_content = template.render(
            email=email,
            otp=otp
        )

        email_service.send_email(
            to=email,
            subject="Password Reset OTP",
            body=f"Your password reset OTP.",
            html_body=html_content
        )

        # 5 minutes in seconds
        return {"message": "OTP sent to email", "timeout": OTP_INTERVAL}

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


async def verify_password_reset_otp(email: str, otp: str):
    """
    Function to verify the password reset OTP.
    Create a new OTP secret for the user and store it in Redis with a 5-minute expiration.
    Create a new token for password reset and store it in Redis with no expiration
    Password reset token will be removed from Redis after password reset is complete.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if user exists
        cursor.execute(GET_USER_BY_EMAIL, (email,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        # Retrieve OTP secret from Redis
        otp_secret = await get_otp_secret_redis(user["id"])

        if not otp_secret:
            raise HTTPException(
                status_code=400,
                detail="OTP has expired or is invalid"
            )

        # Verify OTP
        if not verify_otp(secret=otp_secret, otp=otp):
            raise HTTPException(
                status_code=400,
                detail="Invalid OTP"
            )

        await delete_otp_secret_redis(user["id"])

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        # create password reset token and store it in Redis with 1 hour expiration
        password_reset_token = create_token(
            user["id"],
            user["role"],
            PASSWORD_RESET_SECRET_KEY,
            expiration_hours=1
        )

        await store_reset_password_token_redis(
            user_id=str(user["id"]),
            token=password_reset_token,
            expiration_seconds=3600  # 1 hour in seconds
        )

        return {"message": "OTP verified successfully", "password_reset_token": password_reset_token}

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


async def reset_password(email: str, new_password: str, password_reset_token: str):
    """
    Function to reset the user's password.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if user exists
        cursor.execute(GET_USER_BY_EMAIL, (email,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        # Decode the password reset tokenxx
        payload = decode_token(password_reset_token, type="password_reset")

        if payload["user_id"] != user["id"]:
            raise HTTPException(
                status_code=401,
                detail="Invalid password reset token for this user"
            )

        stored_token = await get_reset_password_token_redis(str(user["id"]))

        if stored_token != password_reset_token:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired password reset token"
            )

        # Hash the new password
        hashed_password = hash_password(new_password)

        # Update the user's password in the database
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hashed_password, user["id"])
        )
        conn.commit()

        # Delete the password reset token from Redis
        await delete_reset_password_token_redis(str(user["id"]))

        return {"message": "Password reset successfully"}

    except HTTPException:
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()
