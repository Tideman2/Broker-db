from decimal import Decimal

from app.Models.wallet_models import (
    DepositFundsResponse,
    DepositStatus
)


def _build_deposit_response(deposit: dict) -> DepositFundsResponse:

    return DepositFundsResponse(
        id=deposit["id"],
        amount=deposit["amount"].quantize(Decimal("0.01")),
        status=DepositStatus[deposit["status"]],

        created_at=deposit["created_at"],
        confirmed_at=deposit["confirmed_at"],

        asset_id=deposit["asset_id"],
        asset_symbol=deposit["asset_symbol"],
        asset_name=deposit["asset_name"],

        payment_method_id=deposit["payment_method_id"],
        payment_method_name=deposit["payment_method_name"],
        payment_method_type=deposit["payment_method_type"],

        bank_name=deposit["bank_name"],
        account_name=deposit["account_name"],
        account_number=deposit["account_number"],
    )
