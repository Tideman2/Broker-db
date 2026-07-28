from fastapi import HTTPException

from app.db.connection import get_connection
from app.Models.auth_models import (
    User,
    CreateUserResponse,
    LoginUserRequest
)
from app.Models.wallet_models import (
    AddBankDestinationRequest,
    AddCryptoDestinationRequest
)
from app.db.queries.user_queries import (
    INSERT_USER,
    INSERT_ADDRESS,
    GET_USER_BY_ID,
    GET_USER_BY_EMAIL
)

from app.utils.wallet import (
    _create_wallet,
    _add_withdraw_destination,
    _add_bank_destination,
    _add_crypto_destination,
    _get_withdraw_destination,
    _validate_destination_label,
    _build_destination_response
)

from app.utils.password import hash_password, verify_password
from app.utils.jwt import create_token, decode_token


def create_user(data: User) -> CreateUserResponse:
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
            data.zip
        ))

        # Create wallet for user
        _create_wallet(cursor, user_id)

        conn.commit()
        access_token = create_token(user_id, data.full_name)
        return {"id": user_id, "message": "User created", "token": access_token}

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
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(GET_USER_BY_ID, (user_id,))
        user = cursor.fetchone()
        return user

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e
    finally:
        cursor.close()
        conn.close()


def check_if_email_and_password_is_correct(data: LoginUserRequest):
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

        accsse_token = create_token(user["id"], user["full_name"])
        return {"user_id": user["id"], "token": accsse_token}

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


def generate_new_token(token: str) -> str:
    """
    function that checks if the token is valid
    and generates a new token from same payload
    """
    user = decode_token(token)
    user_id = user["user_id"]
    full_name = user["name"]
    token = create_token(user_id, full_name)
    return token


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
