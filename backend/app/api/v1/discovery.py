from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.water_body import WaterBodyRead
from app.services.discovery import (
    WaterBodyDiscoveryService,
    WaterBodyDiscoveryResult,
    DiscoverySearchResponse,
    ProviderListResponse,
    ProviderStatus,
)

router = APIRouter(prefix="/discovery", tags=["Discovery"])


def get_discovery_service(db: Session = Depends(get_db)) -> WaterBodyDiscoveryService:
    return WaterBodyDiscoveryService(db)


@router.get(
    "/providers",
    response_model=ProviderListResponse,
    summary="List available water body geographic data providers",
)
def list_discovery_providers(
    service: WaterBodyDiscoveryService = Depends(get_discovery_service),
) -> ProviderListResponse:
    providers = service.list_providers()
    return ProviderListResponse(providers=providers)


@router.get(
    "/water-bodies/search",
    response_model=DiscoverySearchResponse,
    summary="Search global water bodies from geographic provider",
)
async def search_water_bodies(
    q: str = Query(..., min_length=1, max_length=100, description="Search query string"),
    limit: int = Query(10, ge=1, le=20, description="Result limit (max 20)"),
    provider: Optional[str] = Query(None, description="Target provider (default: osm)"),
    service: WaterBodyDiscoveryService = Depends(get_discovery_service),
) -> DiscoverySearchResponse:
    return await service.search(query=q, limit=limit, provider_name=provider)


@router.post(
    "/water-bodies/import",
    response_model=WaterBodyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Import a discovered water body into local SQLite catalog",
)
def import_water_body(
    payload: WaterBodyDiscoveryResult,
    service: WaterBodyDiscoveryService = Depends(get_discovery_service),
) -> WaterBodyRead:
    return service.import_water_body(payload)
