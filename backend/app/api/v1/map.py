"""
Map and Raster Visualization REST API router for JalNetra.
Provides vector GeoJSON layers, scene footprint layers, raster metadata, and RGB visualization images.
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.map_service import MapService
from app.services.raster.service import RasterService
from app.services.raster.models import (
    SceneRasterMetadataResponse,
    RGBVisualizationResponse,
)

router = APIRouter(prefix="/map", tags=["Interactive Map & Raster Visualization"])

map_service = MapService()
raster_service = RasterService()


@router.get(
    "/water-bodies/geojson",
    summary="Get all water bodies as GeoJSON FeatureCollection",
    response_model=Dict[str, Any],
)
def get_water_bodies_geojson(db: Session = Depends(get_db)):
    """Returns all active water body geometries in GeoJSON format for the map layer."""
    return map_service.get_water_bodies_geojson(db)


@router.get(
    "/scenes",
    summary="List registered satellite scenes for mapping",
    response_model=List[Dict[str, Any]],
)
def get_map_scenes(
    water_body_id: str = Query(..., description="Target water body UUID"),
    db: Session = Depends(get_db),
):
    """Returns registered satellite scenes with footprints and asset status for a water body."""
    return map_service.get_scenes_for_water_body(db, water_body_id)


@router.get(
    "/scenes/{scene_id}/metadata",
    summary="Get raster metadata and geographic bounds for a scene",
    response_model=SceneRasterMetadataResponse,
)
def get_scene_raster_metadata(scene_id: str, db: Session = Depends(get_db)):
    """
    Inspects CRS, dimensions, resolution, and geographic bounds of downloaded GeoTIFFs.
    Never exposes internal filesystem paths.
    """
    try:
        return raster_service.get_scene_metadata(db, scene_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to inspect raster: {str(e)}")


@router.get(
    "/scenes/{scene_id}/rgb",
    summary="Get RGB visualization metadata and display bounds",
    response_model=RGBVisualizationResponse,
)
def get_scene_rgb_visualization(
    scene_id: str,
    force_regenerate: bool = Query(False, description="Force re-rendering even if cached"),
    db: Session = Depends(get_db),
):
    """
    Aligns and reprojects B04, B03, B02 GeoTIFF bands, applies percentile contrast stretch,
    and returns geographic bounds and image URL for Leaflet ImageOverlay.
    """
    try:
        return raster_service.get_or_render_rgb(db, scene_id, force_regenerate=force_regenerate)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Raster processing failed: {str(e)}")


@router.get(
    "/scenes/{scene_id}/rgb/image",
    summary="Get raw RGB visualization PNG image for Leaflet overlay",
)
def get_scene_rgb_image(scene_id: str, db: Session = Depends(get_db)):
    """
    Safely streams the rendered RGBA PNG image for the scene.
    Validates scene ID against the database to prevent path traversal.
    """
    try:
        img_path = raster_service.get_rgb_image_path(db, scene_id)
        return FileResponse(
            path=img_path,
            media_type="image/png",
            filename=f"scene_{scene_id}_rgb.png",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to serve raster image: {str(e)}")
