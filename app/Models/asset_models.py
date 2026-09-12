from datetime import datetime

from pydantic import BaseModel


class AddAssetRequest(BaseModel):
    symbol: str
    name: str
    address: str | None = None
    is_active: bool


class UpdateAssetRequest(BaseModel):
    symbol: str
    name: str
    address: str | None = None
    is_active: bool


class AssetResponse(BaseModel):
    id: int
    symbol: str
    name: str
    address: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DeleteAssetResponse(BaseModel):
    id: int
    message: str
