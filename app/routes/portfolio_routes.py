from fastapi import APIRouter, Depends
from typing import List

from app.Models.portfolio_models import (
    BuyInstrumentRequest,
    TransactionResponse,
    SellInstrumentRequest,
    HoldingResponse,
    PortfolioOverviewResponse,
    PortfolioProfitLossResponse,
    TradeOverviewResponse,
    TradeResponse,
    TradeType
)

from app.services.portfolio_services import (
    buy_instrument,
    sell_instrument,
    compute_holdings,
    get_portfolio_overview,
    get_portfolio_profit_loss,
    get_paginated_trades,
    get_trades_overview
)

from app.utils.jwt import get_current_user


portfolio_router = APIRouter(
    prefix="/portfolio",
    tags=["Portfolio"]
)


@portfolio_router.post(
    "/buy",
    response_model=TransactionResponse
)
def buy(
    request: BuyInstrumentRequest,
    user=Depends(get_current_user)
):
    """
    Buy an instrument.
    """
    return buy_instrument(
        user_id=user.user_id,
        data=request
    )


@portfolio_router.post(
    "/sell",
    response_model=TransactionResponse
)
def sell(
    request: SellInstrumentRequest,
    user=Depends(get_current_user)
):
    """
    Sell an instrument.
    """
    return sell_instrument(
        user_id=user.user_id,
        data=request
    )


@portfolio_router.get("/holdings", response_model=List[HoldingResponse])
def get_holdings(user=Depends(get_current_user)):
    """
    Get holdings
    """
    print("We got started")
    return compute_holdings(
        user_id=user.user_id,
    )


@portfolio_router.get("/overview", response_model=PortfolioOverviewResponse)
def portfolio_overview(user=Depends(get_current_user)):
    """
    Get portfolio overview
    """

    return get_portfolio_overview(
        user_id=user.user_id,
    )


@portfolio_router.get("/profit-loss", response_model=PortfolioProfitLossResponse)
def portfolio_profit_loss(user=Depends(get_current_user)):
    """
    Get portfolio profit and loss breakdown for each instrument 
    and total for whole portfolio
    """
    return get_portfolio_profit_loss(user_id=user.user_id)


# ======================================================
# TRADES
# ======================================================


@portfolio_router.get("/trades/overview", response_model=TradeOverviewResponse)
def trades_overview(user=Depends(get_current_user)):
    """
    Get lifetime trade statistics: total trades, win rate and
    total net profit. Not filterable.
    """
    return get_trades_overview(user_id=user.user_id)


@portfolio_router.get("/trades", response_model=List[TradeResponse])
def get_trades_endpoint(
    instrument_id: int | None = None,
    type: TradeType | None = None,
    days: int | None = None,
    limit: int = 10,
    offset: int = 0,
    user=Depends(get_current_user)
):
    """
    Get a filtered, paginated list of the current user's trades.
    """
    return get_paginated_trades(
        user_id=user.user_id,
        instrument_id=instrument_id,
        trade_type=type,
        days=days,
        limit=limit,
        offset=offset
    )
