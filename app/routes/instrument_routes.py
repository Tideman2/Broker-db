from fastapi import APIRouter, Depends, Query

from app.services.instrument_services import (
    get_instruments,
    add_instrument,
    update_instrument,
    delete_instrument
)

from app.Models.instrument_models import (
    AddInstrumentRequest,
    UpdateInstrumentRequest,
    InstrumentResponse
)

from app.utils.jwt import require_admin


instrument_router = APIRouter(
    prefix="/instruments",
    tags=["Instruments"]
)


@instrument_router.get(
    "",
    response_model=list[InstrumentResponse]
)
def get_instruments_endpoint(
    is_active: bool | None = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(require_admin)
):
    """
    List paginated instruments for admin, optionally filtered
    by is_active. Inactive instruments are included by default.
    """
    return get_instruments(limit=limit, offset=offset, is_active=is_active)


@instrument_router.post(
    "",
    response_model=InstrumentResponse
)
def add_instrument_endpoint(
    request: AddInstrumentRequest,
    user=Depends(require_admin)
):
    """
    Add a new instrument.
    """
    return add_instrument(data=request)


@instrument_router.put(
    "/{instrument_id}",
    response_model=InstrumentResponse
)
def update_instrument_endpoint(
    instrument_id: int,
    request: UpdateInstrumentRequest,
    user=Depends(require_admin)
):
    """
    Update an instrument. Provided fields are merged;
    is_active toggles through this endpoint.
    """
    return update_instrument(instrument_id=instrument_id, data=request)


@instrument_router.delete(
    "/{instrument_id}",
    response_model=InstrumentResponse
)
def delete_instrument_endpoint(
    instrument_id: int,
    user=Depends(require_admin)
):
    """
    Soft delete an instrument by setting is_active to FALSE.
    Trade history is preserved.
    """
    return delete_instrument(instrument_id=instrument_id)
