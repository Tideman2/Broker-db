from decimal import Decimal
from typing import List
from pydantic import BaseModel


# ============================
# Request Models
# ============================

class BuyInstrumentRequest(BaseModel):
    instrument_id: int
    quantity: Decimal


class SellInstrumentRequest(BaseModel):
    instrument_id: int
    quantity: Decimal

# ============================
# Helper Models
# ============================


class InstrumentProfitLossResult(BaseModel):
    instrument_id: int | None = None
    symbol: str | None = None
    realized_profit: Decimal
    unrealized_profit: Decimal
    total_profit_loss: Decimal
    remaining_quantity: Decimal
    remaining_cost_basis: Decimal


# ============================
# Response Models
# ============================

class TransactionResponse(BaseModel):
    message: str
    transaction_id: int


class HoldingResponse(BaseModel):
    instrument_id: int
    symbol: str
    name: str
    category: str

    current_price: Decimal

    total_buy: Decimal
    total_sell: Decimal
    net_quantity: Decimal
    instrument_value: Decimal


class AssetAllocation(BaseModel):
    instrument_id: int
    symbol: str
    allocation_percentage: Decimal


class PortfolioProfitLossResponse(BaseModel):
    portfolio_realized_profit: Decimal
    portfolio_unrealized_profit: Decimal
    portfolio_total_profit_loss: Decimal

    instruments: List[InstrumentProfitLossResult]


class PortfolioOverviewResponse(BaseModel):
    portfolio_value: Decimal
    asset_allocation: List[AssetAllocation]
    diversification_score: str
    portfolio_risk_score: Decimal
    portfolio_risk_label: str
