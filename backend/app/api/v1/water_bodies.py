from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.water_body_service import WaterBodyService
from app.schemas.water_body import (
    WaterBodyCreate,
    WaterBodyUpdate,
    WaterBodyRead,
    WaterBodyListResponse,
)

router = APIRouter(prefix="/water-bodies", tags=["Water Bodies"])


def get_water_body_service(db: Session = Depends(get_db)) -> WaterBodyService:
    return WaterBodyService(db)


@router.post(
    "",
    response_model=WaterBodyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new water body",
)
def create_water_body(
    payload: WaterBodyCreate,
    service: WaterBodyService = Depends(get_water_body_service),
) -> WaterBodyRead:
    return service.create_water_body(payload)


@router.get(
    "",
    response_model=WaterBodyListResponse,
    summary="List water bodies with filtering and pagination",
)
def list_water_bodies(
    search: Optional[str] = Query(None, description="Search term for name or description"),
    country: Optional[str] = Query(None, description="Filter by country"),
    source: Optional[str] = Query(None, description="Filter by catalog source"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    service: WaterBodyService = Depends(get_water_body_service),
) -> WaterBodyListResponse:
    items, total = service.list_water_bodies(
        search=search,
        country=country,
        source=source,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return WaterBodyListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{water_body_id}",
    response_model=WaterBodyRead,
    summary="Get a water body by ID",
)
def get_water_body(
    water_body_id: str,
    service: WaterBodyService = Depends(get_water_body_service),
) -> WaterBodyRead:
    return service.get_water_body(water_body_id)


@router.patch(
    "/{water_body_id}",
    response_model=WaterBodyRead,
    summary="Update a water body",
)
def update_water_body(
    water_body_id: str,
    payload: WaterBodyUpdate,
    service: WaterBodyService = Depends(get_water_body_service),
) -> WaterBodyRead:
    return service.update_water_body(water_body_id, payload)


@router.delete(
    "/{water_body_id}",
    response_model=WaterBodyRead,
    summary="Deactivate a water body (soft deletion)",
)
def deactivate_water_body(
    water_body_id: str,
    service: WaterBodyService = Depends(get_water_body_service),
) -> WaterBodyRead:
    return service.deactivate_water_body(water_body_id)
