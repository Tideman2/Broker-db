from decimal import Decimal
from fastapi import HTTPException

from app.db.queries.user_queries import GET_USER_BY_ID
from app.db.queries.instrument_queries import CHECK_INSTRUMENT
from app.db.queries.transaction_queries import GET_TRADES
from app.Models.portfolio_models import InstrumentProfitLossResult


def _get_trades(
    cursor,
    user_id: int,
    instrument_id: int | None,
    trade_type: str | None,
    days: int | None,
    limit: int,
    offset: int
) -> list[dict]:
    """
    Fetches a filtered, paginated page of a user's trades.
    """

    cursor.execute(
        GET_TRADES,
        (
            user_id,
            instrument_id,
            instrument_id,
            trade_type,
            trade_type,
            days,
            days,
            limit,
            offset
        )
    )

    return cursor.fetchall()


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


def _match_buy_lots(transactions):
    """
    Matches SELL transactions against BUY lots using FIFO.

    Returns
    -------
    round_trips : list
        One entry per matched lot, each carrying its own realized
        profit/loss. A SELL spanning several lots yields several
        entries.

    remaining_lots : list
        BUY lots still open once every transaction is replayed, in
        FIFO order. Each entry is mutated in place while matching, so
        this list reflects the unconsumed quantities.
    """

    buy_queue = []
    round_trips = []

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

                round_trips.append({
                    "quantity": consumed_quantity,
                    "buy_price": oldest_lot["price"],
                    "sell_price": price,
                    "profit_loss": (
                        (price - oldest_lot["price"])
                        * consumed_quantity
                    )
                })

                oldest_lot["quantity"] -= consumed_quantity

                remaining_sell -= consumed_quantity

                # Remove empty buy lot
                if oldest_lot["quantity"] == 0:
                    buy_queue.pop(0)

    return round_trips, buy_queue


def _compute_trade_overview(
    transactions_by_instrument
):
    """
    Aggregates lifetime trade statistics.

    A trade is a single FIFO round-trip, so only matched lots count.
    Buys that have not been sold against are not trades.
    """

    total_trades = 0
    winning_trades = 0
    total_net_profit = Decimal("0")

    for transactions in transactions_by_instrument:

        round_trips, _ = _match_buy_lots(transactions)

        for round_trip in round_trips:

            total_trades += 1
            total_net_profit += round_trip["profit_loss"]

            if round_trip["profit_loss"] > 0:
                winning_trades += 1

    # No closed trades means the rate is undefined, reported as zero.
    if total_trades == 0:
        win_rate = Decimal("0")
    else:
        win_rate = (
            Decimal(winning_trades)
            / Decimal(total_trades)
            * Decimal("100")
        )

    return {
        "total_trades": total_trades,
        "win_rate": win_rate.quantize(Decimal("0.01")),
        "total_net_profit": total_net_profit.quantize(
            Decimal("0.01")
        )
    }


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

    round_trips, buy_queue = _match_buy_lots(transactions)

    realized_profit = Decimal("0")

    for round_trip in round_trips:
        realized_profit += round_trip["profit_loss"]

    # ------------------------
    # Unrealized Profit
    # ------------------------

    remaining_quantity = Decimal("0")
    remaining_cost_basis = Decimal("0")
    unrealized_profit = Decimal("0")

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
