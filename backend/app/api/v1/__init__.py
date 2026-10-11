from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.water_bodies import router as water_bodies_router
from app.api.v1.storage import router as storage_router
from app.api.v1.discovery import router as discovery_router
from app.api.v1.satellite import router as satellite_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(water_bodies_router)
api_v1_router.include_router(storage_router)
api_v1_router.include_router(discovery_router)
api_v1_router.include_router(satellite_router)
