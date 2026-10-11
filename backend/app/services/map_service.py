"""
Map Service for JalNetra.
Provides geographic payloads for water bodies, scene footprints, and coordinate bounding boxes.
"""
from typing import List, Dict, Any, Optional
import json
from sqlalchemy.orm import Session

from app.db.models.water_body import WaterBody
from app.db.models.satellite_scene import SatelliteScene
from app.db.models.satellite_asset import SatelliteAsset
from app.services.raster.service import RasterService


class MapService:
    """Service providing GIS vector data and scene lists for interactive mapping."""

    def __init__(self):
        self.raster_service = RasterService()

    def get_water_bodies_geojson(self, db: Session) -> Dict[str, Any]:
        """
        Builds a GeoJSON FeatureCollection of all active water bodies
        including their boundaries, centroids, names, and IDs for map visualization.
        """
        water_bodies = db.query(WaterBody).filter(WaterBody.is_active == True).all()
        features = []

        for wb in water_bodies:
            geom = None
            if wb.geometry_geojson:
                try:
                    geom = json.loads(wb.geometry_geojson)
                except Exception:
                    pass

            # Fallback to centroid Point geometry if polygon not present
            if not geom and wb.centroid_lat is not None and wb.centroid_lon is not None:
                geom = {
                    "type": "Point",
                    "coordinates": [wb.centroid_lon, wb.centroid_lat],
                }

            # Fallback to bbox Polygon if centroid also absent
            if not geom and wb.min_lat is not None and wb.min_lon is not None and wb.max_lat is not None and wb.max_lon is not None:
                geom = {
                    "type": "Polygon",
                    "coordinates": [[
                        [wb.min_lon, wb.min_lat],
                        [wb.max_lon, wb.min_lat],
                        [wb.max_lon, wb.max_lat],
                        [wb.min_lon, wb.max_lat],
                        [wb.min_lon, wb.min_lat],
                    ]]
                }

            if geom:
                features.append({
                    "type": "Feature",
                    "id": wb.id,
                    "geometry": geom,
                    "properties": {
                        "id": wb.id,
                        "name": wb.name,
                        "country": wb.country,
                        "state_province": wb.state_province,
                        "district": wb.district,
                        "city": wb.city,
                        "water_body_type": wb.water_body_type,
                        "source": wb.source,
                        "area_sq_km": wb.area_sq_km,
                        "centroid_lat": wb.centroid_lat,
                        "centroid_lon": wb.centroid_lon,
                        "bbox": [wb.min_lon, wb.min_lat, wb.max_lon, wb.max_lat] if wb.min_lat is not None else None,
                    }
                })

        return {
            "type": "FeatureCollection",
            "features": features,
        }

    def get_scenes_for_water_body(self, db: Session, water_body_id: str) -> List[Dict[str, Any]]:
        """
        Returns all registered satellite scenes for a water body,
        including footprint GeoJSON, acquisition status, and asset availability.
        """
        scenes = db.query(SatelliteScene).order_by(SatelliteScene.sensing_start.desc()).all()
        results = []

        for sc in scenes:
            footprint = None
            if sc.footprint_geojson:
                try:
                    footprint = json.loads(sc.footprint_geojson)
                except Exception:
                    pass

            # Assets
            assets = db.query(SatelliteAsset).filter(SatelliteAsset.scene_id == sc.id).all()
            downloaded_keys = [a.asset_key for a in assets if a.status == "downloaded"]
            has_rgb = {"B04", "B03", "B02"}.issubset(set(downloaded_keys))

            results.append({
                "scene_id": sc.id,
                "external_scene_id": sc.external_scene_id,
                "provider": sc.provider,
                "collection": sc.collection,
                "sensing_start": sc.sensing_start.isoformat(),
                "cloud_cover_percent": sc.cloud_cover_percent,
                "status": sc.status,
                "footprint": footprint,
                "bbox": [sc.bbox_min_lon, sc.bbox_min_lat, sc.bbox_max_lon, sc.bbox_max_lat] if sc.bbox_min_lat is not None else None,
                "downloaded_assets": downloaded_keys,
                "has_rgb": has_rgb,
            })

        return results
