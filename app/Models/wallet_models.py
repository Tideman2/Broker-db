from enum import IntEnum, Enum
from decimal import Decimal
from pydantic import BaseModel
from datetime import datetime

# ======================================================
# DEPOSIT MODELS
# ======================================================


class PaymentMethod(IntEnum):
    CRYPTO = 1
    BANK = 2


class DepositStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"


class Deposit(BaseModel):
    amount: Decimal
    asset_id: int
    payment_method: PaymentMethod


class DepositFundsRequest(BaseModel):
    deposit: Deposit


class DepositFundsResponse(BaseModel):
    id: int

    amount: Decimal
    status: DepositStatus

    created_at: datetime
    confirmed_at: datetime | None = None

    asset_id: int
    asset_symbol: str
    asset_name: str

    payment_method_id: int
    payment_method_name: str
    payment_method_type: str

    bank_name: str | None = None
    account_name: str | None = None
    account_number: str | None = None


# ======================================================
# WITHDRAW MODELS
# ======================================================


class DestinationType(str, Enum):
    CRYPTO = "CRYPTO"
    BANK = "BANK"


class DestinationDetails(BaseModel):
    label: str
    type: DestinationType


class CryptoDestination(BaseModel):
    asset_id: int
    address: str


class BankDestination(BaseModel):
    bank_name: str
    account_name: str
    account_number: str


class AddBankDestinationRequest(BaseModel):
    destination_details: DestinationDetails
    bank_destination: BankDestination


class AddCryptoDestinationRequest(BaseModel):
    desination_details: DestinationDetails
    destination: CryptoDestination


class DestinationResponse(BaseModel):
    id: int
    label: str
    type: DestinationType

    asset_id: int | None = None
    asset_symbol: str | None = None
    asset_name: str | None = None
    address: str | None = None

    bank_name: str | None = None
    account_name: str | None = None
    account_number: str | None = None


class WithdrawFundsRequest(BaseModel):
    amount: Decimal
    destination_id: int


class WithdrawStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"


class WithdrawFundsResponse(BaseModel):
    id: int

    amount: Decimal
    status: WithdrawStatus

    created_at: datetime
    confirmed_at: datetime | None = None

    asset_id: int
    asset_symbol: str
    asset_name: str

    destination_id: int
    destination_label: str
    destination_type: str

    address: str | None = None

    bank_name: str | None = None
    account_name: str | None = None
    account_number: str | None = None


class Withdraw(BaseModel):
    user_id: int
    asset_id: int
    destination_id: int
    amount: Decimal
