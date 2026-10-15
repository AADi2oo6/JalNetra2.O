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

## AI & Telegram Integration (Foundation Phase)

### 1. JalNetra AI Assistant (OpenAI)
- **Architecture**: Server-side proxy (`/api/v1/ai/analyze` and `/api/v1/ai/status`) utilizing official `openai` SDK with `gpt-4o-mini`.
- **Read-Only Invariant**: AI acts strictly as an observational assistant to interpret satellite-derived records and spectral indices (NDTI, NDCI, FAI, anomaly). Never converts remote sensing proxies into uncalibrated laboratory units (NTU, mg/L).
- **Per-Request Data Isolation**: Structured observation and spectral metadata are injected strictly per selected water body; prevents any cross-contamination.
- **Analysis Workstation UI**: Dedicated Section 6 on the Analysis Page with one-click quick actions (*Explain current water condition*, *Summarize changes over time*, *Explain spectral indicators*) and custom inquiry input.

### 2. Telegram Bot Integration
- **Direct Bot Link**: [https://t.me/jalNetra_Helperbot](https://t.me/jalNetra_Helperbot) (`@jalNetra_Helperbot`)
- **Architecture**: Async background long-polling service (`getUpdates`) via `httpx`. Non-crashing lifecycle — missing tokens or Telegram network issues never bring down FastAPI.
- **Available Commands**:
  - `/start`: Welcome message and capabilities overview.
  - `/help`: Detailed command reference.
  - `/ping`: Real-time connectivity health check for Telegram API and JalNetra backend.
  - `/status`: System readiness report (Backend, AI configuration, Telegram connectivity, Database).
  - `/ai <question>`: Query JalNetra AI directly from Telegram in scientifically cautious, read-only language.
- **Security & Authorization**: Rejects arbitrary administrative commands. Optional `TELEGRAM_ALLOWED_CHAT_IDS` whitelist for restricted access during development.

---

## Environment Variables

Configure these settings in `backend/.env` (refer to `backend/.env.example`):

```env
# AI Assistant (OpenAI)
AI_ENABLED=true
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
AI_MAX_OUTPUT_TOKENS=800

# Telegram Bot
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_USERNAME=jalNetra_Helperbot
TELEGRAM_ALLOWED_CHAT_IDS=
```

> **Security Note**: Never commit actual API keys or bot tokens. All credentials must remain in gitignored `.env` files.

---

## Running Tests

From `backend` with the virtual environment activated:

```bash
pytest backend/tests -v
```

Verifies all 129 unit and integration tests across storage, discovery, satellite acquisition, spectral indices, AI service, and Telegram bot.

---

## Roadmap

- **Phase 0**: Core Development Foundation (Complete)
- **Phase 1**: Local Database + Storage Foundation (Complete)
- **Phase 2**: Global Water-Body Discovery (Complete)
- **Phase 3**: Sentinel-2 Satellite Acquisition (Complete)
- **Phase 4**: Spectral Indices & Remote-Sensing Proxies (Complete)
- **Phase 5**: AI Assistant & Telegram Foundation (Complete)
- **Phase 6**: Autonomous Telemetry, Proactive Alerting & Remote Dispatch
