"""
Processing Service for JalNetra (Phase 5).
Coordinates SCL cloud masking, spectral water segmentation,
metadata persistence, visualization overlay generation, and disk caching.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
from datetime import datetime, timezone
from PIL import Image
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.satellite_scene import SatelliteScene
from app.db.models.satellite_asset import SatelliteAsset
from app.services.raster.models import GeoBounds
from app.services.processing.models import (
    CloudMaskMetadata,
    WaterDetectionMetadata,
    ProcessingStatusResponse,
    MaskVisualizationResponse,
)
from app.services.processing.cloud_mask import CloudMaskGenerator
from app.services.processing.water_detection import WaterDetector, DEFAULT_WATER_THRESHOLD


class ProcessingService:
    """Service orchestrating pixel-level cloud masking and water detection on Sentinel-2 scenes."""

    def __init__(self, data_dir: Optional[Path] = None):
        self._custom_data_dir = data_dir

    @property
    def data_dir(self) -> Path:
        return self._custom_data_dir or settings.resolved_data_dir

    @property
    def processed_dir(self) -> Path:
        d = self.data_dir / "processed"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_scene_processed_dir(self, scene_id: str) -> Path:
        d = self.processed_dir / scene_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_processing_status(self, db: Session, scene_id: str) -> ProcessingStatusResponse:
        """Inspects whether cloud mask and water mask have been generated for a scene."""
        scene = db.query(SatelliteScene).filter(
            (SatelliteScene.id == scene_id) | (SatelliteScene.external_scene_id == scene_id)
        ).first()
        if not scene:
            raise ValueError(f"Satellite scene not found: {scene_id}")

        scene_dir = self.get_scene_processed_dir(scene.id)
        meta_file = scene_dir / "processing_metadata.json"
        cloud_mask_file = scene_dir / "cloud_mask.tif"
        water_mask_file = scene_dir / "water_mask.tif"

        # Check required assets in DB
        assets = db.query(SatelliteAsset).filter(SatelliteAsset.scene_id == scene.id).all()
        present_keys = [a.asset_key for a in assets if a.status == "downloaded"]
        required_keys = ["SCL", "B03", "B08"]
        missing_keys = [k for k in required_keys if k not in present_keys]

        if meta_file.exists() and cloud_mask_file.exists() and water_mask_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                return ProcessingStatusResponse(
                    scene_id=scene.id,
                    external_scene_id=scene.external_scene_id,
                    status="ready",
                    cloud_mask_available=True,
                    water_mask_available=True,
                    cloud_mask=CloudMaskMetadata(**meta_data["cloud_mask"]),
                    water_detection=WaterDetectionMetadata(**meta_data["water_detection"]),
                    source_bands_present=present_keys,
                    missing_required_bands=missing_keys,
                    created_at=meta_data.get("created_at"),
                    cloud_mask_image_url=f"/api/v1/processing/scenes/{scene.id}/cloud-mask/image",
                    water_mask_image_url=f"/api/v1/processing/scenes/{scene.id}/water-mask/image",
                )
            except Exception:
                pass  # Fallback to unprocessed if JSON corrupted

        return ProcessingStatusResponse(
            scene_id=scene.id,
            external_scene_id=scene.external_scene_id,
            status="unprocessed" if not missing_keys else "missing_assets",
            cloud_mask_available=False,
            water_mask_available=False,
            source_bands_present=present_keys,
            missing_required_bands=missing_keys,
        )

    def process_scene(
        self,
        db: Session,
        scene_id: str,
        threshold: float = DEFAULT_WATER_THRESHOLD,
        force_recompute: bool = False,
    ) -> ProcessingStatusResponse:
        """
        Runs SCL cloud masking and spectral water detection pipeline.
        Saves cloud_mask.tif, water_mask.tif, processing_metadata.json,
        and generates visualization overlay PNGs.
        """
        scene = db.query(SatelliteScene).filter(
            (SatelliteScene.id == scene_id) | (SatelliteScene.external_scene_id == scene_id)
        ).first()
        if not scene:
            raise ValueError(f"Satellite scene not found: {scene_id}")

        scene_dir = self.get_scene_processed_dir(scene.id)
        meta_file = scene_dir / "processing_metadata.json"
        cloud_mask_file = scene_dir / "cloud_mask.tif"
        water_mask_file = scene_dir / "water_mask.tif"

        # If already processed and not force_recompute, return cached status
        if not force_recompute and meta_file.exists() and cloud_mask_file.exists() and water_mask_file.exists():
            return self.get_processing_status(db, scene.id)

        # Locate required assets (SCL, B03, B08)
        assets = db.query(SatelliteAsset).filter(SatelliteAsset.scene_id == scene.id).all()
        asset_map = {a.asset_key: a for a in assets}

        required = ["SCL", "B03", "B08"]
        missing = [k for k in required if k not in asset_map or asset_map[k].status != "downloaded"]
        if missing:
            raise FileNotFoundError(
                f"Cannot process scene: Missing required downloaded asset(s) {missing}. "
                f"Please download them in the Satellite tab first."
            )

        scl_path = self.data_dir / asset_map["SCL"].local_path
        b03_path = self.data_dir / asset_map["B03"].local_path
        b08_path = self.data_dir / asset_map["B08"].local_path

        # Step 1: Generate Cloud Mask GeoTIFF
        cloud_res = CloudMaskGenerator.generate_mask(
            scl_path=scl_path,
            output_mask_path=cloud_mask_file,
        )

        # Step 2: Generate Water Mask GeoTIFF
        water_res = WaterDetector.detect_water(
            green_path=b03_path,
            nir_path=b08_path,
            cloud_mask_path=cloud_mask_file,
            output_water_mask_path=water_mask_file,
            threshold=threshold,
        )

        # Step 3: Pre-render Visualization Overlays for Leaflet
        self._render_visualization_overlays(
            scl_path=scl_path,
            water_mask_path=water_mask_file,
            output_dir=scene_dir,
        )

        # Step 4: Write processing_metadata.json
        cloud_meta = CloudMaskMetadata(
            source_layer="SCL",
            masked_classes=cloud_res["masked_classes"],
            total_pixels=cloud_res["total_pixels"],
            valid_pixels=cloud_res["valid_pixels"],
            cloud_shadow_pixels=cloud_res["cloud_shadow_pixels"],
            valid_pixel_percentage=cloud_res["valid_pixel_percentage"],
            cloud_shadow_percentage=cloud_res["cloud_shadow_percentage"],
        )

        water_meta = WaterDetectionMetadata(
            method=water_res["method"],
            threshold=water_res["threshold"],
            source_bands=water_res["source_bands"],
            total_pixels=water_res["total_pixels"],
            valid_pixels_evaluated=water_res["valid_pixels_evaluated"],
            water_pixels=water_res["water_pixels"],
            water_extent_percentage_of_valid=water_res["water_extent_percentage_of_valid"],
            water_extent_percentage_of_total=water_res["water_extent_percentage_of_total"],
            estimated_water_area_sq_km=water_res["estimated_water_area_sq_km"],
        )

        payload = {
            "scene_id": scene.id,
            "external_scene_id": scene.external_scene_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "cloud_mask": cloud_meta.model_dump(),
            "water_detection": water_meta.model_dump(),
        }

        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return self.get_processing_status(db, scene.id)

    def _render_visualization_overlays(
        self,
        scl_path: Path,
        water_mask_path: Path,
        output_dir: Path,
        max_dimension: int = 1024,
    ) -> Dict[str, Any]:
        """
        Generates aligned semi-transparent RGBA PNG overlays for Leaflet ImageOverlay:
        - cloud_mask.png: Amber/Orange overlay for cloud/shadow pixels
        - water_mask.png: Vivid Cyan overlay for detected water pixels
        - overlay_bounds.json: EPSG:4326 geographic bounding box
        """
        with rasterio.open(scl_path) as src_scl, rasterio.open(water_mask_path) as src_wm:
            vrt_kwargs = {"crs": "EPSG:4326", "resampling": Resampling.nearest}
            with WarpedVRT(src_scl, **vrt_kwargs) as vrt_scl, WarpedVRT(src_wm, **vrt_kwargs) as vrt_wm:
                bounds = vrt_scl.bounds
                geo_bounds = GeoBounds(
                    west=float(bounds.left),
                    south=float(bounds.bottom),
                    east=float(bounds.right),
                    north=float(bounds.top),
                )

                aspect = vrt_scl.width / max(1, vrt_scl.height)
                if aspect >= 1.0:
                    out_w = max_dimension
                    out_h = max(1, int(max_dimension / aspect))
                else:
                    out_w = max(1, int(max_dimension * aspect))
                    out_h = max_dimension

                scl_grid = vrt_scl.read(1, out_shape=(out_h, out_w), resampling=Resampling.nearest)
                wm_grid = vrt_wm.read(1, out_shape=(out_h, out_w), resampling=Resampling.nearest)

                # 1. Cloud Overlay (Amber/Orange: R=245, G=158, B=11, Alpha=200 for cloud/shadow classes 3, 8, 9, 10)
                is_cloud_shadow = np.isin(scl_grid, [3, 8, 9, 10])
                cloud_rgba = np.zeros((out_h, out_w, 4), dtype=np.uint8)
                cloud_rgba[is_cloud_shadow] = [245, 158, 11, 200]
                img_cloud = Image.fromarray(cloud_rgba)
                img_cloud.save(output_dir / "cloud_mask.png", format="PNG", optimize=True)

                # 2. Water Overlay (Vivid Blue/Cyan: R=14, G=165, B=233, Alpha=210 for water pixels wm_grid == 1)
                is_water = (wm_grid == 1)
                water_rgba = np.zeros((out_h, out_w, 4), dtype=np.uint8)
                water_rgba[is_water] = [14, 165, 233, 210]
                img_water = Image.fromarray(water_rgba)
                img_water.save(output_dir / "water_mask.png", format="PNG", optimize=True)

                # 3. Cache overlay bounds
                bounds_data = {
                    "bounds": geo_bounds.model_dump(),
                    "width": out_w,
                    "height": out_h,
                    "crs": "EPSG:4326",
                }
                with open(output_dir / "overlay_bounds.json", "w", encoding="utf-8") as f:
                    json.dump(bounds_data, f, indent=2)

                return bounds_data

    def get_mask_visualization(
        self,
        db: Session,
        scene_id: str,
        mask_type: str,
    ) -> MaskVisualizationResponse:
        """Returns geographic bounds and image URL for Leaflet ImageOverlay."""
        scene = db.query(SatelliteScene).filter(
            (SatelliteScene.id == scene_id) | (SatelliteScene.external_scene_id == scene_id)
        ).first()
        if not scene:
            raise ValueError(f"Satellite scene not found: {scene_id}")

        scene_dir = self.get_scene_processed_dir(scene.id)
        bounds_file = scene_dir / "overlay_bounds.json"
        png_file = scene_dir / f"{mask_type}.png"

        if not bounds_file.exists() or not png_file.exists():
            # Trigger processing if not done yet
            self.process_scene(db, scene.id)

        if not bounds_file.exists() or not png_file.exists():
            raise FileNotFoundError(f"Visualization overlay {mask_type} could not be generated for scene {scene_id}")

        with open(bounds_file, "r", encoding="utf-8") as f:
            bounds_data = json.load(f)

        return MaskVisualizationResponse(
            scene_id=scene.id,
            mask_type=mask_type,
            crs="EPSG:4326",
            bounds=GeoBounds(**bounds_data["bounds"]),
            width=bounds_data["width"],
            height=bounds_data["height"],
            image_url=f"/api/v1/processing/scenes/{scene.id}/{mask_type.replace('_', '-')}/image",
            cached=True,
            description=f"Sentinel-2 georeferenced {mask_type.replace('_', ' ')} visualization layer",
        )

    def get_mask_image_path(self, db: Session, scene_id: str, mask_type: str) -> Path:
        """Returns path to the PNG image file for streaming, ensuring it is rendered."""
        scene = db.query(SatelliteScene).filter(
            (SatelliteScene.id == scene_id) | (SatelliteScene.external_scene_id == scene_id)
        ).first()
        if not scene:
            raise ValueError(f"Satellite scene not found: {scene_id}")

        scene_dir = self.get_scene_processed_dir(scene.id)
        png_path = scene_dir / f"{mask_type}.png"
        if not png_path.exists():
            self.process_scene(db, scene.id)

        if not png_path.exists():
            raise FileNotFoundError(f"Mask image {mask_type} not found for scene {scene_id}")

        return png_path
