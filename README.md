# JalNetra 2.0 (Phase 4: Interactive GIS Map & Satellite Raster Visualization)

**JalNetra 2.0** is an open-source, scalable geospatial platform engineered for monitoring water bodies, surface water extent, water quality indices, and hydrological anomalies using satellite observations and remote sensing telemetry.

## Current Development Phase: Phase 4 Complete

This repository has completed **Phase 4: Interactive GIS Map & Satellite Imagery Visualization**. It provides an operational GIS interface and safe backend raster alignment pipeline:
- **Interactive Monitoring Map**: Built using Leaflet and React-Leaflet with OpenStreetMap base tiles, dynamic auto-fitting camera bounds, layer toggles, and symbology legend.
- **Water Body Vector Layer**: GeoJSON polygon/centroid visualization of all tracked water bodies with click-to-inspect popups and zooming.
- **Scene Footprint Layer**: Visualizes Sentinel-2 scene spatial coverage boundaries distinct from water body geometries.
- **On-Demand Sentinel-2 RGB Rendering**: Aligns B04 (Red), B03 (Green), and B02 (Blue) GeoTIFFs, reprojects native UTM coordinates to EPSG:4326 (WGS84) via Rasterio `WarpedVRT`, handles NoData/invalid masks transparently, and applies 2nd-to-98th percentile contrast stretching.
- **Safe Raster Caching & Serving**: Saves optimized display products to `data/processed/map/{scene_id}/rgb.png` with metadata JSON. Cached products are instantly reused on subsequent requests. Original GeoTIFF assets are never modified.
- **Security & Path Traversal Prevention**: Only serves registered scenes through database UUID lookups; rejects arbitrary filesystem path requests.

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
