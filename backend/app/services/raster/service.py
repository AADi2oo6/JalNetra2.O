"""
Raster Orchestrator Service for JalNetra.
Coordinates metadata queries, cache lookup, on-demand RGB rendering, and bounds computation.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.satellite_scene import SatelliteScene
from app.db.models.satellite_asset import SatelliteAsset
from app.services.raster.models import (
    SceneRasterMetadataResponse,
    AssetMetadata,
    RGBVisualizationResponse,
    GeoBounds,
)
from app.services.raster.reader import RasterReader
from app.services.raster.renderer import RGBRenderer


class RasterService:
    """Service providing high-level raster metadata and RGB rendering for satellite scenes."""

    def __init__(self, data_dir: Optional[Path] = None):
        self._custom_data_dir = data_dir

    @property
    def data_dir(self) -> Path:
        return self._custom_data_dir or settings.resolved_data_dir

    @property
    def processed_dir(self) -> Path:
        d = self.data_dir / "processed" / "map"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_scene_metadata(self, db: Session, scene_id: str) -> SceneRasterMetadataResponse:
        """
        Inspects scene assets in SQLite and on disk.
        Returns comprehensive metadata including CRS, dimensions, resolution, and geographic bounds.
        """
        scene = db.query(SatelliteScene).filter(SatelliteScene.id == scene_id).first()
        if not scene:
            # Also try matching by external_scene_id for convenience
            scene = db.query(SatelliteScene).filter(SatelliteScene.external_scene_id == scene_id).first()
        if not scene:
            raise ValueError(f"Satellite scene not found: {scene_id}")

        assets = db.query(SatelliteAsset).filter(SatelliteAsset.scene_id == scene.id).all()
        
        asset_meta_list: List[AssetMetadata] = []
        primary_geo_bounds: Optional[GeoBounds] = None
        primary_crs: Optional[str] = None
        primary_native_bounds: Optional[dict] = None

        downloaded_band_keys = set()

        for asset in assets:
            is_downloaded = asset.status == "downloaded" and asset.local_path is not None
            file_path = (self.data_dir / asset.local_path) if asset.local_path else None
            exists = file_path.exists() if file_path else False

            meta = AssetMetadata(
                asset_key=asset.asset_key,
                asset_type=asset.asset_type,
                file_size_bytes=asset.file_size_bytes,
                is_downloaded=is_downloaded and exists,
            )

            # If it's a GeoTIFF and exists locally, inspect raster headers
            if exists and file_path and file_path.suffix.lower() in [".tif", ".tiff"]:
                downloaded_band_keys.add(asset.asset_key)
                try:
                    insp = RasterReader.inspect_file(file_path)
                    meta.crs = insp.get("crs")
                    meta.width = insp.get("width")
                    meta.height = insp.get("height")
                    meta.resolution_meters = insp.get("resolution_meters")
                    meta.nodata = insp.get("nodata")

                    if not primary_geo_bounds and insp.get("geographic_bounds"):
                        gb = insp["geographic_bounds"]
                        primary_geo_bounds = GeoBounds(
                            west=gb["west"],
                            south=gb["south"],
                            east=gb["east"],
                            north=gb["north"],
                        )
                    if not primary_crs:
                        primary_crs = insp.get("crs")
                    if not primary_native_bounds:
                        primary_native_bounds = insp.get("native_bounds")
                except Exception:
                    pass

            asset_meta_list.append(meta)

        # Fallback to scene's stored bbox if raster inspection did not set bounds
        if not primary_geo_bounds and scene.bbox_min_lat is not None:
            primary_geo_bounds = GeoBounds(
                west=scene.bbox_min_lon or 0.0,
                south=scene.bbox_min_lat or 0.0,
                east=scene.bbox_max_lon or 0.0,
                north=scene.bbox_max_lat or 0.0,
            )

        # Check if RGB bands (B04, B03, B02) are present
        rgb_available = {"B04", "B03", "B02"}.issubset(downloaded_band_keys)
        
        # Check if cached visualization exists
        cache_png = self.processed_dir / scene.id / "rgb.png"
        rgb_cached = cache_png.exists()

        return SceneRasterMetadataResponse(
            scene_id=scene.id,
            external_scene_id=scene.external_scene_id,
            provider=scene.provider,
            collection=scene.collection,
            sensing_start=scene.sensing_start.isoformat(),
            cloud_cover_percent=scene.cloud_cover_percent,
            crs=primary_crs,
            geographic_bounds=primary_geo_bounds,
            native_bounds=primary_native_bounds,
            available_assets=asset_meta_list,
            rgb_available=rgb_available,
            rgb_cached=rgb_cached,
            image_url=f"/api/v1/map/scenes/{scene.id}/rgb/image" if (rgb_available or rgb_cached) else None,
        )

    def get_or_render_rgb(
        self,
        db: Session,
        scene_id: str,
        force_regenerate: bool = False,
    ) -> RGBVisualizationResponse:
        """
        Retrieves cached RGB visualization or renders it on demand from B04, B03, and B02.
        Saves result to data/processed/map/{scene_id}/rgb.png and returns bounds.
        """
        scene = db.query(SatelliteScene).filter(SatelliteScene.id == scene_id).first()
        if not scene:
            scene = db.query(SatelliteScene).filter(SatelliteScene.external_scene_id == scene_id).first()
        if not scene:
            raise ValueError(f"Satellite scene not found: {scene_id}")

        scene_processed_dir = self.processed_dir / scene.id
        output_png = scene_processed_dir / "rgb.png"
        meta_json = scene_processed_dir / "rgb_meta.json"

        # Check existing cache
        if not force_regenerate and output_png.exists() and meta_json.exists():
            try:
                with open(meta_json, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                return RGBVisualizationResponse(
                    scene_id=scene.id,
                    external_scene_id=scene.external_scene_id,
                    crs="EPSG:4326",
                    bounds=GeoBounds(**cached_data["bounds"]),
                    width=cached_data["width"],
                    height=cached_data["height"],
                    image_url=f"/api/v1/map/scenes/{scene.id}/rgb/image",
                    cached=True,
                )
            except Exception:
                pass  # Fall through to re-render if cached meta is corrupted

        # Locate B04, B03, B02 assets
        assets = db.query(SatelliteAsset).filter(SatelliteAsset.scene_id == scene.id).all()
        asset_map = {a.asset_key: a for a in assets}

        missing = [b for b in ["B04", "B03", "B02"] if b not in asset_map or asset_map[b].status != "downloaded"]
        if missing:
            raise FileNotFoundError(
                f"Cannot render RGB visualization: Missing downloaded band(s) {missing}. "
                f"Please acquire these bands first."
            )

        b04_path = self.data_dir / asset_map["B04"].local_path
        b03_path = self.data_dir / asset_map["B03"].local_path
        b02_path = self.data_dir / asset_map["B02"].local_path

        # Render RGB visualization
        render_res = RGBRenderer.render_rgb(
            red_path=b04_path,
            green_path=b03_path,
            blue_path=b02_path,
            output_png_path=output_png,
        )

        # Cache metadata
        meta_to_save = {
            "scene_id": scene.id,
            "external_scene_id": scene.external_scene_id,
            "bounds": render_res["bounds"].model_dump(),
            "width": render_res["width"],
            "height": render_res["height"],
            "crs": render_res["crs"],
        }
        with open(meta_json, "w", encoding="utf-8") as f:
            json.dump(meta_to_save, f, indent=2)

        return RGBVisualizationResponse(
            scene_id=scene.id,
            external_scene_id=scene.external_scene_id,
            crs="EPSG:4326",
            bounds=render_res["bounds"],
            width=render_res["width"],
            height=render_res["height"],
            image_url=f"/api/v1/map/scenes/{scene.id}/rgb/image",
            cached=False,
        )

    def get_rgb_image_path(self, db: Session, scene_id: str) -> Path:
        """Returns the filesystem path to the rendered RGB PNG image, rendering if needed."""
        scene = db.query(SatelliteScene).filter(SatelliteScene.id == scene_id).first()
        if not scene:
            scene = db.query(SatelliteScene).filter(SatelliteScene.external_scene_id == scene_id).first()
        if not scene:
            raise ValueError(f"Satellite scene not found: {scene_id}")

        img_path = self.processed_dir / scene.id / "rgb.png"
        if not img_path.exists():
            # Trigger generation
            self.get_or_render_rgb(db, scene.id)

        if not img_path.exists():
            raise FileNotFoundError(f"RGB visualization could not be generated for scene {scene_id}")

        return img_path
