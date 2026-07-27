from decimal import Decimal
from fastapi import HTTPException

from app.db.connection import get_connection

from app.Models.portfolio_models import BuyInstrumentRequest, SellInstrumentRequest
from app.db.queries.instrument_queries import GET_USER_INSTRUMENT_TRANSACTIONS, GROUP_USER_INSTRUMENT, GET_INSTRUMENT_RISK_WEIGHT
from app.db.queries.transaction_queries import INSERT_BUY_TRANSACTION, INSERT_SELL_TRANSACTION

# from app.utils.wallet_helpers import _debit_available, _credit_available

from app.utils.wallet import (
    _credit_available,
    _debit_available
)

from app.utils.portfolio_helpers import _get_user, _get_instrument, _compute_net_quantity
from app.utils.portfolio_helpers import _validate_quantity, _compute_instrument_profit_loss


def buy_instrument(
    user_id: int,
    data: BuyInstrumentRequest
):
    """
    Creates a BUY transaction.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check user exists
        _get_user(cursor, user_id)

        # Check instrument exists
        instrument = _get_instrument(cursor, data.instrument_id)

        # Validate quantity
        _validate_quantity(data.quantity)
        price = instrument["current_price"]

        buy_cost = price * data.quantity

        _debit_available(cursor, user_id, buy_cost)

        # Insert BUY transaction
        cursor.execute(
            INSERT_BUY_TRANSACTION,
            (
                user_id,
                data.instrument_id,
                data.quantity,
                price
            )
        )

        conn.commit()

        return {
            "message": "Instrument purchased successfully.",
            "transaction_id": cursor.lastrowid
        }

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


def sell_instrument(
    user_id: int,
    data: SellInstrumentRequest
):
    """
    Creates a SELL transaction.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check user exists
        _get_user(cursor, user_id)

        # Check instrument exists
        instrument = _get_instrument(cursor, data.instrument_id)

        # Validate quantity
        _validate_quantity(data.quantity)

        # fetch transaction history
        cursor.execute(GET_USER_INSTRUMENT_TRANSACTIONS,
                       (user_id, data.instrument_id))
        instrument_transactions = cursor.fetchall()

        # Calculate net quantity
        net_quantity = _compute_net_quantity(instrument_transactions)

        # Validate Quantity againts net quantity
        if data.quantity > net_quantity:
            raise HTTPException(
                status_code=400,
                detail="Insufficient quantity."
            )
        price = instrument["current_price"]

        # Insert sell transaction
        cursor.execute(
            INSERT_SELL_TRANSACTION,
            (
                user_id,
                data.instrument_id,
                data.quantity,
                price
            )
        )

        sales_proceeds = price * data.quantity

        _credit_available(cursor, user_id, sales_proceeds)

        conn.commit()

        return {
            "message": "Instrument sold successfully.",
            "transaction_id": cursor.lastrowid
        }

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


def compute_holdings(user_id: int):
    """
    Returns all instruments currently held by the user.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    print("service started")
    try:
        # Check user exists
        _get_user(cursor, user_id)

        # Get grouped holdings
        cursor.execute(GROUP_USER_INSTRUMENT, (user_id,))
        instrument_groups = cursor.fetchall()
        holdings = []
        for instrument in instrument_groups:

            total_buy = instrument["total_buy"] or Decimal("0")
            total_sell = instrument["total_sell"] or Decimal("0")

            net_quantity = total_buy - total_sell

            # Skip closed positions
            if net_quantity <= 0:
                continue

            instrument_value = (
                net_quantity *
                instrument["current_price"]
            )

            holdings.append({
                "instrument_id": instrument["id"],
                "symbol": instrument["symbol"],
                "name": instrument["name"],
                "category": instrument["category"],
                "current_price": instrument["current_price"],
                "total_buy": total_buy,
                "total_sell": total_sell,
                "net_quantity": net_quantity,
                "instrument_value": instrument_value
            })

        return holdings

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


def get_portfolio_overview(user_id: int):
    """
    Returns portfolio overview.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        holdings = compute_holdings(user_id)
        portfolio_value = Decimal("0")

        # Calculate portfolio value
        for holding in holdings:
            portfolio_value += holding["instrument_value"]

        # Empty portfolio
        if portfolio_value == 0:
            return {
                "portfolio_value": Decimal("0"),
                "asset_allocation": [],
                "diversification_score": "N/A"
            }

        allocation = []
        largest_allocation = Decimal("0")

        # Calculate asset allocation
        for holding in holdings:

            percentage = (
                holding["instrument_value"] /
                portfolio_value
            ) * Decimal("100")

            largest_allocation = max(largest_allocation, percentage)

            allocation.append({
                "instrument_id": holding["instrument_id"],
                "symbol": holding["symbol"],
                "allocation_percentage": percentage
            })

        # Portfolio risk level
        portfolio_risk_level = Decimal("0")

        for holding in holdings:
            cursor.execute(GET_INSTRUMENT_RISK_WEIGHT,
                           (holding["instrument_id"],))
            category_weight = cursor.fetchone()

            allocation_percentage = (
                holding["instrument_value"] /
                portfolio_value
            ) * Decimal("100")

            portfolio_risk_level += (allocation_percentage *
                                     category_weight["risk_weight"])

        risk_score = portfolio_risk_level / Decimal("100")

        if risk_score < Decimal("2.1"):
            risk_label = "Low"
        elif risk_score < Decimal("3.6"):
            risk_label = "Moderate"
        else:
            risk_label = "High"

        # Diversification Score
        if largest_allocation > Decimal("70"):
            diversification_score = "Poor"

        elif largest_allocation > Decimal("40"):
            diversification_score = "Moderate"

        else:
            diversification_score = "Good"

        return {
            "portfolio_value": portfolio_value,
            "asset_allocation": allocation,
            "diversification_score": diversification_score,
            "portfolio_risk_score": risk_score,
            "portfolio_risk_label": risk_label
        }

    except Exception as e:
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e

    finally:
        cursor.close()
        conn.close()


def get_portfolio_profit_loss(user_id: int):
    """
    Returns portfolio realized, unrealized and total profit/loss.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Ensure user exists
        _get_user(cursor, user_id)

        holdings = compute_holdings(user_id)

        portfolio_realized = Decimal("0")
        portfolio_unrealized = Decimal("0")

        instrument_profit_loss = []

        for holding in holdings:

            cursor.execute(
                GET_USER_INSTRUMENT_TRANSACTIONS,
                (
                    user_id,
                    holding["instrument_id"]
                )
            )

            transactions = cursor.fetchall()

            result = _compute_instrument_profit_loss(
                transactions=transactions,
                current_price=holding["current_price"]
            )

            portfolio_realized += result["realized_profit"]

            portfolio_unrealized += result["unrealized_profit"]

            instrument_profit_loss.append({
                "instrument_id": holding["instrument_id"],
                "symbol": holding["symbol"],
                "realized_profit": result["realized_profit"].quantize(Decimal("0.01")),
                "unrealized_profit": result["unrealized_profit"].quantize(Decimal("0.01")),
                "total_profit_loss": result["total_profit_loss"].quantize(Decimal("0.01")),
                "remaining_quantity": result["remaining_quantity"],
                "remaining_cost_basis": result["remaining_cost_basis"]
            })

        return {
            "portfolio_realized_profit": portfolio_realized.quantize(Decimal("0.01")),
            "portfolio_unrealized_profit": portfolio_unrealized.quantize(Decimal("0.01")),
            "portfolio_total_profit_loss":
                (portfolio_realized + portfolio_unrealized).quantize(Decimal("0.01")),
            "instruments": instrument_profit_loss
        }

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
