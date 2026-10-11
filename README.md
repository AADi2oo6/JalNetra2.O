# JalNetra 2.0 (Phase 3: Sentinel-2 Satellite Acquisition)

**JalNetra 2.0** is an open-source, scalable geospatial platform engineered for monitoring water bodies, surface water extent, water quality indices, and hydrological anomalies using satellite observations and remote sensing telemetry.

## Current Development Phase: Phase 3 Complete

This repository has completed **Phase 3: Sentinel-2 Satellite Data Acquisition**. It provides a fully decoupled, public STAC-driven scene discovery and atomic asset acquisition subsystem:
- **Provider Abstraction (`SatelliteProvider`)**: Decouples satellite catalogs from application logic. Initialized with **Earth Search (AWS Element84)** providing open public HTTP access to Sentinel-2 L2A Cloud-Optimized GeoTIFF (COG) data without requiring AWS credentials or SDK keys. (Copernicus Data Space or other STAC catalogs can be added cleanly as future providers).
- **Target Spatial STAC Search**: Constrained by the selected water body's GeoJSON geometry or bounding box, datetime intervals, and maximum cloud cover percentage.
- **Deterministic Multi-Factor Scene Ranking**: Scores candidate scenes based on cloud cover percentage (50%), spatial overlap with the target water body (30%), and sensing date recency (20%).
- **Controlled Asset Ingestion**: Normalizes canonical band mapping (`B02`, `B03`, `B04`, `B08`, `B11`, `B12`, `SCL`, `thumbnail`). Downloads requested spectral assets using streaming chunks, atomic temporary file replacement, and SHA256 verification.
- **Idempotency & Duplicate Prevention**: Re-downloading an existing asset whose local checksum matches is prevented.
- **Independent Scene Directories**: Avoids raster overwrite bugs by structuring storage under `data/scenes/{scene_id}/assets/{asset_key}.tif` with dedicated `metadata.json`.
- **Database Tracking**: Fully registers `SatelliteScene` and `SatelliteAsset` records in SQLite via SQLAlchemy repositories.
- **Developer UI**: Interactive satellite tab in React enabling water body selection, STAC querying, scene ranking inspection, and selective asset downloads.

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

## API Endpoints

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
