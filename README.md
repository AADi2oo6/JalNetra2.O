# JalNetra 2.0 (Phase 5: Cloud Masking & Water Detection)

**JalNetra 2.0** is an open-source, scalable geospatial platform engineered for monitoring water bodies, surface water extent, water quality indices, and hydrological anomalies using satellite observations and remote sensing telemetry.

## Current Development Phase: Phase 5 Complete

This repository has completed **Phase 5: Cloud Masking & Water Detection**. It provides an operational pixel-level preprocessing pipeline:
- **SCL Cloud and Shadow Masking**: Extracts clear observations using Sentinel-2 Scene Classification Layer (`SCL.tif`). Filters out cloud shadows (3), medium-probability clouds (8), high-probability clouds (9), thin cirrus (10), snow/ice (11), and NoData/defective pixels (0, 1), producing a georeferenced binary valid mask (`cloud_mask.tif`).
- **Deterministic Spectral Water Detection**: Aligns Sentinel-2 Green (`B03.tif`) and NIR (`B08.tif`) on the 20m SCL reference grid via Rasterio `WarpedVRT`. Evaluates normalized green-to-NIR contrast `(B03 - B08)/(B03 + B08) > 0.0` strictly over valid clear-sky pixels. Outputs a georeferenced binary water mask (`water_mask.tif`).
- **Processing Metrics & Metadata**: Persists pixel counts, valid observation percentages, and surface water extent in `data/processed/{scene_id}/processing_metadata.json`.
- **Integrated Interactive Map Overlays**: Renders semi-transparent amber cloud/shadow and cyan water detection overlays directly onto the Leaflet monitoring map.
- **Scientific Boundary Integrity**: Strictly limits segmentation to surface water identification; does NOT compute water quality, pollution indices (NDTI, NDCI), or ML anomalies.

---

## Satellite Acquisition Architecture

```text
User / Frontend
      │
      ▼ HTTP GET /api/v1/satellite/scenes/search?water_body_id=...
Satellite API Layer
      │
      ▼
SatelliteService
      │
      ├──▶ 1. Check SatelliteCacheService ──▶ Valid Cache? ──(YES)──▶ Return Cached
      │                                                │ (NO)
      ▼                                                ▼
SatelliteProvider (Earth Search STAC) ◀────────────────┘
      │
      ▼ (Raw STAC GeoJSON Features)
Scene Normalization & Canonical Band Mapping (B02..B12, SCL)
      │
      ▼
Deterministic Multi-Factor Ranking (Cloud 50% + Overlap 30% + Recency 20%)
      │
      ▼
Write to STAC Cache (data/cache/stac_*.json + SQLite cache_entries)
      │
      ▼ Return Ranked Scenes to User
User Selects Scene & Assets to Acquire
      │
      ▼ HTTP POST /api/v1/satellite/scenes/{id}/acquire
Streaming Download via Atomic Temp File & SHA256 Checksum
      │
      ▼ Save to data/scenes/{scene_id}/assets/{asset_key}.tif
Register / Update SQLite SatelliteScene & SatelliteAsset Records
```

---

## Local Scene Storage Structure

Each acquired scene is completely isolated:

```text
data/scenes/{scene_id}/
├── metadata.json
└── assets/
    ├── B02.tif        # Blue (10m)
    ├── B03.tif        # Green (10m)
    ├── B04.tif        # Red (10m)
    ├── B08.tif        # NIR (10m)
    ├── B11.tif        # SWIR1 (20m)
    ├── B12.tif        # SWIR2 (20m)
    ├── SCL.tif        # Scene Classification Layer
    └── thumbnail.jpg  # True color preview
```

---

## Configuration

The initial Sentinel-2 provider uses publicly accessible Sentinel-2 L2A data and **does not require AWS credentials**.

Configuration keys in `.env` (with sensible defaults in `config.py`):
```env
# Sentinel-2 Satellite Acquisition (Phase 3)
SATELLITE_PROVIDER=earth_search
SATELLITE_STAC_URL=https://earth-search.aws.element84.com/v1
SATELLITE_COLLECTION=sentinel-2-c1-l2a
SATELLITE_REQUEST_TIMEOUT_SECONDS=60.0
SATELLITE_CACHE_TTL_SECONDS=86400
```

---

### Preprocessing & Water Detection APIs (`/api/v1/processing`)
- `POST /api/v1/processing/scenes/{scene_id}`: Runs SCL cloud/shadow filtering and deterministic spectral water segmentation on a scene, saving `cloud_mask.tif`, `water_mask.tif`, `processing_metadata.json`, and overlay PNGs.
- `GET /api/v1/processing/scenes/{scene_id}`: Returns processing status, cloud/shadow coverage percentage, and detected water extent.
- `GET /api/v1/processing/scenes/{scene_id}/cloud-mask`: Returns geographic bounds (EPSG:4326) and image overlay URL for the cloud/shadow mask.
- `GET /api/v1/processing/scenes/{scene_id}/cloud-mask/image`: Streams the rendered semi-transparent amber cloud/shadow PNG overlay.
- `GET /api/v1/processing/scenes/{scene_id}/water-mask`: Returns geographic bounds (EPSG:4326) and image overlay URL for the detected water mask.
- `GET /api/v1/processing/scenes/{scene_id}/water-mask/image`: Streams the rendered semi-transparent cyan detected water PNG overlay.

### Interactive Map & Raster APIs (`/api/v1/map`)
- `GET /api/v1/map/water-bodies/geojson`: Returns GeoJSON FeatureCollection of all tracked water bodies with polygon geometry, centroids, and attributes.
- `GET /api/v1/map/scenes?water_body_id={id}`: Lists registered satellite scenes for the water body with footprint GeoJSON, acquisition status, and RGB readiness.
- `GET /api/v1/map/scenes/{scene_id}/metadata`: Inspects native CRS, geographic bounds (EPSG:4326), dimensions, and asset readiness without exposing internal filesystem paths.
- `GET /api/v1/map/scenes/{scene_id}/rgb?force_regenerate={bool}`: Triggers/retrieves aligned, reprojected, contrast-stretched True-Color RGB visualization bounds and image URL.
- `GET /api/v1/map/scenes/{scene_id}/rgb/image`: Streams the rendered RGBA PNG image overlay for Leaflet.

### Satellite API (`/api/v1/satellite`)
- `GET /api/v1/satellite/scenes/search?water_body_id={id}&start_date={iso}&end_date={iso}&max_cloud_cover={%}&limit={n}`: Search Sentinel-2 L2A scenes for a water body using STAC with automatic ranking and response caching.
- `POST /api/v1/satellite/scenes/{external_scene_id}/acquire`: Download selected spectral band assets for a scene to local storage and update database tracking.

### Discovery & Catalog APIs
- `GET /api/v1/discovery/water-bodies/search`: Search global water bodies from OpenStreetMap.
- `POST /api/v1/discovery/water-bodies/import`: Import a discovered water body into local SQLite.
- `GET /api/v1/water-bodies`: List cataloged water bodies.
- `GET /api/v1/storage/status`: Health check of SQLite database and all data sub-directories.
- `GET /docs`: Interactive Swagger OpenAPI documentation.

---

## Running the Application

### 1. Backend

```bash
cd backend
python -m venv .venv

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit [http://localhost:5173](http://localhost:5173). Navigate to the **SENTINEL-2 / SCENES (PHASE 3)** tab.

---

## Running Tests

From `backend` with the virtual environment activated:

```bash
pytest -v
```

Runs 41 tests verifying:
1. STAC Item normalization and canonical band mapping (`B02`, `B03`, `B04`, `B08`, `B11`, `B12`, `SCL`, `thumbnail`).
2. Deterministic scene ranking (cloud cover, spatial overlap, sensing recency).
3. File-backed STAC query caching and TTL invalidation.
4. Streaming asset downloading via atomic temporary files with SHA256 checksums.
5. Idempotent asset acquisition avoiding duplicate downloads.
6. HTTP REST API endpoints for scene search and acquisition.
7. Phase 0, 1, and 2 regressions (water body CRUD, storage status, OpenStreetMap discovery).

---

## Roadmap

- **Phase 0**: Core Development Foundation (Complete)
- **Phase 1**: Local Database + Storage Foundation (Complete)
- **Phase 2**: Global Water-Body Discovery (Complete)
- **Phase 3**: Sentinel-2 Satellite Acquisition (Complete)
- **Phase 4**: Spectral Indices & Water Detection (Next)
- **Phase 5**: Telemetry, Alerting & Reporting
