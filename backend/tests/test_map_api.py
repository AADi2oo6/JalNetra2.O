"""
Integration tests for Map API endpoints (Phase 4).
"""
from datetime import datetime, timezone
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.water_body import WaterBody
from app.db.models.satellite_scene import SatelliteScene
from app.db.models.satellite_asset import SatelliteAsset
from tests.test_raster_service import create_synthetic_geotiff


def test_map_api_water_bodies_geojson(client: TestClient, db_session: Session):
    """Verifies GET /api/v1/map/water-bodies/geojson returns a valid GeoJSON FeatureCollection."""
    wb = WaterBody(
        name="Map Test Lake",
        normalized_name="map test lake",
        country="India",
        source="manual",
        source_id="map-wb-1",
        centroid_lat=20.0,
        centroid_lon=85.0,
        min_lat=19.9,
        min_lon=84.9,
        max_lat=20.1,
        max_lon=85.1,
        geometry_geojson='{"type": "Polygon", "coordinates": [[[84.9, 19.9], [85.1, 19.9], [85.1, 20.1], [84.9, 20.1], [84.9, 19.9]]]}',
    )
    db_session.add(wb)
    db_session.commit()

    resp = client.get("/api/v1/map/water-bodies/geojson")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 1
    feat = next(f for f in data["features"] if f["properties"]["id"] == wb.id)
    assert feat["properties"]["name"] == "Map Test Lake"
    assert feat["geometry"]["type"] == "Polygon"


def test_map_api_scenes_list(client: TestClient, db_session: Session):
    """Verifies GET /api/v1/map/scenes?water_body_id=... returns registered scenes."""
    scene = SatelliteScene(
        provider="earth_search",
        collection="sentinel-2-c1-l2a",
        external_scene_id="S2A_MAP_SCENE_TEST",
        sensing_start=datetime.now(timezone.utc),
        cloud_cover_percent=1.2,
        status="downloaded",
        bbox_min_lat=19.0,
        bbox_min_lon=85.0,
        bbox_max_lat=20.0,
        bbox_max_lon=86.0,
        footprint_geojson='{"type": "Polygon", "coordinates": [[[85.0, 19.0], [86.0, 19.0], [86.0, 20.0], [85.0, 20.0], [85.0, 19.0]]]}',
    )
    db_session.add(scene)
    db_session.commit()

    resp = client.get(f"/api/v1/map/scenes?water_body_id=dummy-id")
    assert resp.status_code == 200
    scenes = resp.json()
    assert len(scenes) >= 1
    found = next(s for s in scenes if s["external_scene_id"] == "S2A_MAP_SCENE_TEST")
    assert found["cloud_cover_percent"] == 1.2
    assert found["footprint"] is not None


def test_map_api_raster_metadata_and_rgb(client: TestClient, db_session: Session, tmp_path: Path, monkeypatch):
    """Verifies /api/v1/map/scenes/{scene_id}/metadata and /rgb endpoints."""
    import app.services.raster.service as raster_svc_module

    # Monkeypatch data_dir in raster service
    monkeypatch.setattr(raster_svc_module.settings, "DATA_DIR", str(tmp_path))

    scene_id = "map-scene-test-uuid"
    scene_dir = tmp_path / "scenes" / scene_id / "assets"
    
    scene = SatelliteScene(
        id=scene_id,
        provider="earth_search",
        collection="sentinel-2-c1-l2a",
        external_scene_id="S2A_TEST_FULL_FLOW",
        sensing_start=datetime.now(timezone.utc),
        status="downloaded",
    )
    db_session.add(scene)

    for band in ["B04", "B03", "B02"]:
        tif = scene_dir / f"{band}.tif"
        create_synthetic_geotiff(tif, width=32, height=32)
        asset = SatelliteAsset(
            scene_id=scene_id,
            asset_key=band,
            asset_type="image/tiff",
            local_path=f"scenes/{scene_id}/assets/{band}.tif",
            status="downloaded",
            file_size_bytes=tif.stat().st_size,
        )
        db_session.add(asset)
    db_session.commit()

    # 1. Metadata check
    meta_resp = client.get(f"/api/v1/map/scenes/{scene_id}/metadata")
    assert meta_resp.status_code == 200
    meta = meta_resp.json()
    assert meta["rgb_available"] is True
    assert meta["geographic_bounds"] is not None

    # 2. RGB rendering check
    rgb_resp = client.get(f"/api/v1/map/scenes/{scene_id}/rgb")
    assert rgb_resp.status_code == 200
    rgb_data = rgb_resp.json()
    assert rgb_data["crs"] == "EPSG:4326"
    assert rgb_data["width"] > 0
    assert "image_url" in rgb_data

    # 3. Stream RGB image check
    img_resp = client.get(f"/api/v1/map/scenes/{scene_id}/rgb/image")
    assert img_resp.status_code == 200
    assert img_resp.headers["content-type"] == "image/png"
    assert len(img_resp.content) > 0


def test_map_api_security_path_traversal(client: TestClient):
    """Verifies that arbitrary path traversal attempts return 404/rejection."""
    resp = client.get("/api/v1/map/scenes/../../etc/passwd/rgb/image")
    assert resp.status_code in [404, 422]
