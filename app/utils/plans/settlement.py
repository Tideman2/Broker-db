from datetime import datetime, UTC
from decimal import Decimal

from app.db.queries.subscriptions_queries import (
    GET_SUBSCRIPTION_TRANSACTIONS,
    GET_SUBSCRIPTION_BY_ID,
    ZERO_SUBSCRIPTION_POOL,
    RECORD_SUBSCRIPTION_SETTLEMENT
)
from app.db.queries.instrument_queries import CHECK_INSTRUMENT_ANY
from app.db.queries.transaction_queries import INSERT_SELL_TRANSACTION

from app.utils.portfolio_helpers import _match_buy_lots
from app.utils.wallet.wallet import _credit_available

from app.utils.plans.subscription_helpers import (
    _credit_subscription_pool,
    _cancel_subscription,
    _complete_subscription
)


def _open_positions_by_instrument(
    transactions: list[dict]
) -> dict[int, Decimal]:
    """
    Groups a subscription's trades by instrument and returns the
    quantity still open in each, using FIFO to match sells to buys.
    """

    grouped: dict[int, list[dict]] = {}

    for transaction in transactions:
        grouped.setdefault(
            transaction["instrument_id"], []
        ).append(transaction)

    open_positions: dict[int, Decimal] = {}

    for instrument_id, instrument_transactions in grouped.items():

        _, remaining_lots = _match_buy_lots(instrument_transactions)

        remaining_quantity = sum(
            (lot["quantity"] for lot in remaining_lots),
            Decimal("0")
        )

        if remaining_quantity > 0:
            open_positions[instrument_id] = remaining_quantity

    return open_positions


def _market_value_of_open_positions(
    cursor,
    subscription_id: int
) -> Decimal:
    """
    Marks a subscription's open positions to their instrument's current
    price and returns the total value.
    """

    cursor.execute(
        GET_SUBSCRIPTION_TRANSACTIONS,
        (subscription_id,)
    )
    transactions = cursor.fetchall()

    open_positions = _open_positions_by_instrument(transactions)

    market_value = Decimal("0")

    for instrument_id, quantity in open_positions.items():

        cursor.execute(CHECK_INSTRUMENT_ANY, (instrument_id,))
        instrument = cursor.fetchone()

        market_value += instrument["current_price"] * quantity

    return market_value


def _liquidate_open_positions(
    cursor,
    subscription_id: int,
    user_id: int
):
    """
    Sells every open position under a subscription at the instrument's
    current price and credits the proceeds back into the pool.
    """

    cursor.execute(
        GET_SUBSCRIPTION_TRANSACTIONS,
        (subscription_id,)
    )
    transactions = cursor.fetchall()

    open_positions = _open_positions_by_instrument(transactions)

    for instrument_id, quantity in open_positions.items():

        cursor.execute(CHECK_INSTRUMENT_ANY, (instrument_id,))
        instrument = cursor.fetchone()

        price = instrument["current_price"]

        cursor.execute(
            INSERT_SELL_TRANSACTION,
            (
                user_id,
                instrument_id,
                subscription_id,
                quantity,
                price
            )
        )

        _credit_subscription_pool(
            cursor, subscription_id, price * quantity
        )


def _settle_subscription(
    cursor,
    subscription_id: int,
    user_id: int,
    final_status: str
):
    """
    Closes a subscription: liquidates any open positions back into the
    pool, moves the remaining pool to the user's available balance, and
    sets the final status (CANCELLED on request, COMPLETED on expiry).
    """

    _liquidate_open_positions(cursor, subscription_id, user_id)

    cursor.execute(GET_SUBSCRIPTION_BY_ID, (subscription_id,))
    subscription = cursor.fetchone()

    pool = subscription["pool"] or Decimal("0")

    # Record the payout before the pool is zeroed so the money flow feed
    # can report the amount that actually reached the user's wallet.
    cursor.execute(
        RECORD_SUBSCRIPTION_SETTLEMENT,
        (pool, datetime.now(UTC), subscription_id)
    )

    if pool > Decimal("0"):
        _credit_available(cursor, user_id, pool)

    cursor.execute(ZERO_SUBSCRIPTION_POOL, (subscription_id,))

    if final_status == "CANCELLED":
        _cancel_subscription(cursor, subscription_id)
    else:
        _complete_subscription(cursor, subscription_id)
