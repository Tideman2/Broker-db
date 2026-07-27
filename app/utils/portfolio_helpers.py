from decimal import Decimal
from fastapi import HTTPException

from app.db.queries.user_queries import GET_USER_BY_ID
from app.db.queries.instrument_queries import CHECK_INSTRUMENT
from app.Models.portfolio_models import InstrumentProfitLossResult


def _get_user(cursor, user_id: int):
    """
    Fetches a user or raises 404.
    """

    cursor.execute(GET_USER_BY_ID, (user_id,))
    user = cursor.fetchone()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    return user


def _get_instrument(cursor, instrument_id: int):
    """
    Fetches an instrument or raises 404.
    """

    cursor.execute(CHECK_INSTRUMENT, (instrument_id,))
    instrument = cursor.fetchone()

    if not instrument:
        raise HTTPException(
            status_code=404,
            detail="Instrument not found."
        )

    return instrument


def _validate_quantity(quantity: Decimal):
    """
    Validates quantity.
    """

    if quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than zero."
        )


def _compute_net_quantity(transactions):
    """
    Computes the quantity currently owned.
    """

    total_buy = Decimal("0")
    total_sell = Decimal("0")

    for transaction in transactions:

        if transaction["type"] == "BUY":
            total_buy += transaction["quantity"]

        else:
            total_sell += transaction["quantity"]

    return total_buy - total_sell


def _compute_instrument_profit_loss(
    transactions,
    current_price: Decimal
) -> InstrumentProfitLossResult:
    """
    Computes realized and unrealized profit/loss for one instrument
    using FIFO.

    Parameters
    ----------
    transactions : list
        Ordered transaction history (oldest -> newest)

    current_price : Decimal
        Current market price of the instrument
    """

    buy_queue = []

    realized_profit = Decimal("0")
    unrealized_profit = Decimal("0")
    print(realized_profit, unrealized_profit)
    # Replay every transaction
    for transaction in transactions:

        quantity = transaction["quantity"]
        price = transaction["price"]

        # ------------------------
        # BUY
        # ------------------------
        if transaction["type"] == "BUY":

            buy_queue.append({
                "quantity": quantity,
                "price": price
            })

        # ------------------------
        # SELL
        # ------------------------
        else:

            remaining_sell = quantity

            while remaining_sell > 0:

                if not buy_queue:
                    raise ValueError(
                        "SELL exceeds available BUY lots."
                    )

                oldest_lot = buy_queue[0]

                consumed_quantity = min(
                    remaining_sell,
                    oldest_lot["quantity"]
                )

                realized_profit += (
                    (price - oldest_lot["price"])
                    * consumed_quantity
                )

                oldest_lot["quantity"] -= consumed_quantity

                remaining_sell -= consumed_quantity

                # Remove empty buy lot
                if oldest_lot["quantity"] == 0:
                    buy_queue.pop(0)

    # ------------------------
    # Unrealized Profit
    # ------------------------

    remaining_quantity = Decimal("0")
    remaining_cost_basis = Decimal("0")

    for lot in buy_queue:

        remaining_quantity += lot["quantity"]

        remaining_cost_basis += (
            lot["quantity"] *
            lot["price"]
        )

        unrealized_profit += (
            (current_price - lot["price"])
            * lot["quantity"]
        )

    result = {
        "realized_profit": realized_profit,
        "unrealized_profit": unrealized_profit,
        "total_profit_loss":
            realized_profit + unrealized_profit,
        "remaining_quantity": remaining_quantity,
        "remaining_cost_basis": remaining_cost_basis
    }
    return result
