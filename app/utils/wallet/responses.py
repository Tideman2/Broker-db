from decimal import Decimal

from app.Models.wallet_models import (
    DepositFundsResponse,
    DepositStatus,
    WithdrawFundsResponse,
    WithdrawStatus,
    DestinationResponse,
    DestinationType,
    UserWithdrawalRecordsResponse
)

from app.Models.asset_models import (
    AssetResponse,
    DeleteAssetResponse
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


def _build_withdraw_response(
    withdraw: dict
) -> WithdrawFundsResponse:

    return WithdrawFundsResponse(
        id=withdraw["id"],
        amount=withdraw["amount"].quantize(Decimal("0.01")),
        status=WithdrawStatus[withdraw["status"]],

        created_at=withdraw["created_at"],
        confirmed_at=withdraw["confirmed_at"],

        asset_id=withdraw["asset_id"],
        asset_symbol=withdraw["asset_symbol"],
        asset_name=withdraw["asset_name"],

        destination_id=withdraw["destination_id"],
        destination_label=withdraw["destination_label"],
        destination_type=withdraw["destination_type"],

        address=withdraw["address"],

        bank_name=withdraw["bank_name"],
        account_name=withdraw["account_name"],
        account_number=withdraw["account_number"],
    )


def _build_destination_response(
    destination: dict
) -> DestinationResponse:

    return DestinationResponse(
        id=destination["id"],
        label=destination["label"],
        type=DestinationType[destination["type"]],

        asset_id=destination["asset_id"],
        asset_symbol=destination["asset_symbol"],
        asset_name=destination["asset_name"],
        address=destination["address"],

        bank_name=destination["bank_name"],
        account_name=destination["account_name"],
        account_number=destination["account_number"],
    )


def _build_withdrawals_response(
    withdrawals: list[dict]
) -> list[UserWithdrawalRecordsResponse]:
    return [
        UserWithdrawalRecordsResponse(
            id=withdrawal["id"],
            amount=withdrawal["amount"],
            status=withdrawal["status"],
            created_at=withdrawal["created_at"],
            asset_symbol=withdrawal["asset_symbol"],
            asset_name=withdrawal["asset_name"],
            destination_type=withdrawal["destination_type"],
        )
        for withdrawal in withdrawals
    ]


def _build_user_withdraw_destinations(
    destinations: list[dict]
) -> list[DestinationResponse]:
    return [
        DestinationResponse(
            id=destination["id"],
            label=destination["label"],
            type=DestinationType[destination["type"]],

            asset_id=destination["asset_id"],
            asset_symbol=destination["asset_symbol"],
            asset_name=destination["asset_name"],
            address=destination["address"],

            bank_name=destination["bank_name"],
            account_name=destination["account_name"],
            account_number=destination["account_number"],
        )
        for destination in destinations
    ]


# ASSETS

def _build_assets_response(
    assets: list[dict]
) -> list[AssetResponse]:
    return [
        AssetResponse(
            id=asset["id"],
            symbol=asset["symbol"],
            name=asset["name"],
            address=asset["address"],
            is_active=asset["is_active"],
            created_at=asset["created_at"],
            updated_at=asset["updated_at"],
        )
        for asset in assets
    ]


def _build_asset_response(
    asset: dict
) -> AssetResponse:
    return AssetResponse(
        id=asset["id"],
        symbol=asset["symbol"],
        name=asset["name"],
        address=asset["address"],
        is_active=asset["is_active"],
        created_at=asset["created_at"],
        updated_at=asset["updated_at"],
    )


def _build_delete_asset_response(
    asset_id: int
) -> DeleteAssetResponse:
    return DeleteAssetResponse(
        id=asset_id,
        message="Asset deleted successfully."
    )
