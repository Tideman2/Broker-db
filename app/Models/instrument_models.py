from decimal import Decimal
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class AddInstrumentRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    category_id: int
    current_price: Decimal


class UpdateInstrumentRequest(BaseModel):
    symbol: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category_id: Optional[int] = None
    current_price: Optional[Decimal] = None
    is_active: Optional[bool] = None


class InstrumentResponse(BaseModel):
    id: int
    symbol: str
    name: str
    category_id: int
    category: str
    current_price: Decimal
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
