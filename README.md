# JalNetra 2.0 (Phase 1: Local Database + Storage Foundation)

**JalNetra 2.0** is an open-source, scalable geospatial platform engineered for monitoring water bodies, surface water extent, water quality indices, and hydrological anomalies using satellite observations and remote sensing telemetry.

## Current Development Phase: Phase 1 Complete

This repository has completed **Phase 1: Local Database + Storage Foundation**. It establishes a production-grade local persistence and storage abstraction layer:
- **SQLite Database with Alembic Migrations**: Fully version-controlled schemas (`alembic upgrade head`) replacing runtime auto-generation.
- **Relational Domain Models**: `WaterBody`, `SatelliteScene`, `SatelliteAsset`, `AnalysisRun`, `CacheEntry` with clean foreign keys and indexes.
- **Layered Architecture**: API Routes &rarr; Service Layer &rarr; Repository Layer &rarr; SQLAlchemy 2.x &rarr; SQLite.
- **Local Storage Abstraction (`LocalStorageService`)**: Secure file path traversal prevention, atomic writes, SHA256 checksums, and deterministic directory structures.
- **Water Body CRUD & Storage Status APIs**: Fully tested RESTful endpoints with Pydantic v2 schemas and centralized exception handling.
- **Persistence Verification**: Tests validating data survival across engine disconnections and process restarts.

---

## Architecture Diagram

```text
Frontend (React + Vite)
   │
   ▼ HTTP / JSON
FastAPI API Layer (app/api/v1/)
   │
   ▼
Service Layer (app/services/)
   ├── WaterBodyService
   └── LocalStorageService ──▶ data/ (Local Filesystem: scenes, processed, cache, etc.)
   │
   ▼
Repository Layer (app/db/repositories/)
   ├── WaterBodyRepository
   ├── SatelliteSceneRepository
   ├── SatelliteAssetRepository
   ├── AnalysisRunRepository
   └── CacheRepository
   │
   ▼
SQLAlchemy 2.x / Alembic
   │
   ▼
SQLite Database (data/database/jalnetra.db)
```

---

## Directory Structure

```text
JalNetra2.O/
├── backend/
│   ├── alembic/                      # Alembic migrations directory
│   │   ├── versions/                 # Version-controlled schema scripts
│   │   └── env.py                    # Alembic runtime environment
│   ├── alembic.ini                   # Alembic configuration
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── health.py         # Service health check router
│   │   │       ├── water_bodies.py   # Water-body CRUD API router
│   │   │       ├── storage.py        # Storage and database status router
│   │   │       └── __init__.py
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic v2 settings management
│   │   │   ├── logging.py            # Centralized timestamped logging
│   │   │   └── paths.py              # Repository root & data path resolution
│   │   ├── db/
│   │   │   ├── models/               # SQLAlchemy 2 models
│   │   │   │   ├── water_body.py
│   │   │   │   ├── satellite_scene.py
│   │   │   │   ├── satellite_asset.py
│   │   │   │   ├── analysis_run.py
│   │   │   │   ├── cache_entry.py
│   │   │   │   └── __init__.py
│   │   │   ├── repositories/         # Repository pattern for DB operations
│   │   │   │   ├── water_body_repository.py
│   │   │   │   ├── satellite_scene_repository.py
│   │   │   │   ├── satellite_asset_repository.py
│   │   │   │   ├── analysis_run_repository.py
│   │   │   │   ├── cache_repository.py
│   │   │   │   └── __init__.py
│   │   │   └── database.py           # Engine & SessionLocal provider
│   │   ├── schemas/                  # Pydantic v2 validation DTOs
│   │   │   ├── water_body.py
│   │   │   ├── satellite_scene.py
│   │   │   ├── satellite_asset.py
│   │   │   ├── analysis_run.py
│   │   │   ├── cache.py
│   │   │   └── __init__.py
│   │   ├── services/                 # Business logic & filesystem abstraction
│   │   │   ├── water_body_service.py
│   │   │   ├── storage_service.py
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   └── main.py                   # FastAPI application factory
│   ├── tests/                        # Pytest suite (23 passing tests)
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                         # React 18 + TypeScript + Vite
│   ├── src/
│   │   ├── api/                      # Central API client
│   │   ├── components/               # Header and Navigation
│   │   ├── pages/                    # Dashboard & persistence tester
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css                 # Clean government environmental design tokens
│   ├── package.json
│   ├── vite.config.ts
│   └── .env.example
│
├── data/                             # Local data pipeline storage
│   ├── database/                     # SQLite database (jalnetra.db)
│   ├── water_bodies/                 # Spatial vector geometries
│   ├── scenes/                       # Raw satellite scenes (Sentinel-2)
│   ├── processed/                    # Spectral indices & masks
│   ├── tiles/                        # Map slippy tiles cache
│   ├── cache/                        # Download & calculation cache
│   ├── exports/                      # Reports & GeoJSON exports
│   └── manifests/                    # Pipeline run manifests
│
├── scripts/
├── docs/
├── .gitignore
├── .env.example
└── README.md
```

---

## Requirements

- **Python**: 3.11+ (tested on Python 3.13)
- **Node.js**: 18+ (tested on Node.js 24)
- **npm**: 9+

---

## Database Migrations (Alembic)

Alembic is the single source of truth for the database schema.

### Applying Migrations

From the `backend` directory:

```bash
alembic upgrade head
```

### Creating New Migrations

After modifying or adding models in `backend/app/db/models/`:

```bash
alembic revision --autogenerate -m "describe_changes"
```

Review the generated script in `backend/alembic/versions/` and apply with `alembic upgrade head`.

### Inspecting the Database

Inspect with SQLite CLI:

```bash
sqlite3 data/database/jalnetra.db ".tables"
```

Tables: `water_bodies`, `satellite_scenes`, `satellite_assets`, `analysis_runs`, `cache_entries`, `alembic_version`.

---

## API Endpoints

### Health & System
- `GET /health` & `GET /api/v1/health`: System health and version.
- `GET /api/v1/storage/status`: Health check of SQLite database and all data sub-directories.
- `GET /docs`: Interactive Swagger OpenAPI documentation.

### Water Bodies (`/api/v1/water-bodies`)
- `POST /api/v1/water-bodies`: Create a new water body record.
- `GET /api/v1/water-bodies`: List water bodies with filters (`search`, `country`, `source`, `is_active`, `limit`, `offset`).
- `GET /api/v1/water-bodies/{id}`: Retrieve a specific water body by UUID.
- `PATCH /api/v1/water-bodies/{id}`: Partially update a water body.
- `DELETE /api/v1/water-bodies/{id}`: Soft-delete (sets `is_active = false`).

---

## Local Storage Abstraction (`LocalStorageService`)

All binary and filesystem operations route through `LocalStorageService` (`backend/app/services/storage_service.py`):
- **Path Traversal Protection**: Rejects paths attempting to escape `data/` (e.g., `../../etc`).
- **Atomic File Writes**: Writes data to a temporary file in the destination folder before an atomic replace (`os.fsync` + `shutil.move`).
- **Checksums**: Computes streaming SHA256 hashes (`calculate_sha256`).
- **Deterministic Paths**:
  - Scenes: `data/scenes/{scene_id}/`
  - Processed outputs: `data/processed/{analysis_run_id}/`
  - Water bodies: `data/water_bodies/{water_body_id}/`
  - Cache: `data/cache/{cache_key}/`

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

Visit [http://localhost:5173](http://localhost:5173).

---

## Running Tests

From `backend` with the virtual environment activated:

```bash
pytest -v
```

Runs 23 tests verifying:
1. Health and configuration defaults.
2. Local storage directory management, atomic writes, streaming, SHA256 checksums, and path traversal prevention.
3. Database models, uniqueness constraints, and relationships.
4. Water body CRUD operations via repositories and service layer.
5. Live HTTP REST endpoints (`POST`, `GET`, `PATCH`, `DELETE`, `/storage/status`).
6. Full database session close/reopen cycle confirming persistent SQLite storage across process restarts.

---

## Roadmap

- **Phase 0**: Core Development Foundation (Complete)
- **Phase 1**: Local Database + Storage Foundation (Complete)
- **Phase 2**: Global Water-Body Discovery (Next)
- **Phase 3**: Sentinel-2 Acquisition & Tile Processing
- **Phase 4**: Spectral Indices & Water Detection
- **Phase 5**: Telemetry, Alerting & Reporting
