from fastapi import HTTPException
from app.db.queries.payment_method import GET_PAYMENT_METHOD


def _validate_payment_method(cursor, method_id: int):
    """
    checks if payment method exists or raises 404.
    """

    cursor.execute(GET_PAYMENT_METHOD, (method_id,))
    payment_method = cursor.fetchone()

    if not payment_method:
        raise HTTPException(
            status_code=404,
            detail="payment method not found."
        )

    return payment_method
