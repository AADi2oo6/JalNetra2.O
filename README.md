# JalNetra 2.0 (Phase 0: Core Foundation)

**JalNetra 2.0** is an open-source, scalable geospatial platform engineered for monitoring water bodies, surface water extent, water quality indices, and hydrological anomalies using satellite observations and remote sensing telemetry.

## Current Development Phase: Phase 0

This repository is currently at **Phase 0: Core Development Foundation**. The goal is strictly to establish a robust, reliable, and clean architectural foundation with:
- Modular FastAPI backend
- Scalable SQLite/SQLAlchemy local storage architecture
- Reusable filesystem directory structures for satellite data processing
- Centralized logging, error handling, and test suites
- Clean React + TypeScript + Vite frontend styled for environmental monitoring operations

> Satellite acquisition, Sentinel-2 processing, ML classifiers, and IoT telemetry will be implemented incrementally in subsequent phases.

---

## Architecture Overview

```text
JalNetra2.O/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── health.py         # Versioned health check router
│   │   │       └── __init__.py
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic v2 settings management
│   │   │   ├── logging.py            # Centralized timestamped logging
│   │   │   └── paths.py              # Repository root & data path resolution
│   │   ├── db/
│   │   │   ├── models/               # SQLAlchemy models (Phase 1+)
│   │   │   └── database.py           # SQLite connection & sessionmaker
│   │   ├── schemas/                  # Pydantic v2 schemas
│   │   ├── services/                 # Modular business logic services
│   │   ├── __init__.py
│   │   └── main.py                   # FastAPI application factory & lifespan
│   ├── tests/                        # Pytest suite
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts             # Central API client
│   │   │   └── index.ts
│   │   ├── components/
│   │   │   ├── Header.tsx            # Header with live connection status
│   │   │   └── Navigation.tsx        # Module navigation tabs
│   │   ├── pages/
│   │   │   └── Dashboard.tsx         # System status & pipeline architecture
│   │   ├── App.tsx                   # Main application shell
│   │   ├── main.tsx                  # React entry point
│   │   └── index.css                 # Clean government-style CSS design tokens
│   ├── package.json
│   ├── vite.config.ts
│   └── .env.example
│
├── data/                             # Local geospatial data pipeline storage
│   ├── database/                     # SQLite database (jalnetra.db)
│   ├── water_bodies/                 # Spatial vector geometries
│   ├── scenes/                       # Raw satellite scenes (Sentinel-2)
│   ├── processed/                    # Spectral indices & masks
│   ├── tiles/                        # Map slippy tiles cache
│   ├── cache/                        # Download & calculation cache
│   ├── exports/                      # Reports & GeoJSON exports
│   └── manifests/                    # Pipeline run manifests
│
├── scripts/                          # Utility & automation scripts
├── docs/                             # Documentation
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

## Environment Variables

Copy the example environment file at the root or within `backend/`:

```bash
cp .env.example .env
```

Key variables:
- `APP_NAME`: Name of the API (`JalNetra API`)
- `APP_VERSION`: Current version (`2.0.0`)
- `ENVIRONMENT`: `development` | `production`
- `DEBUG`: `true` | `false`
- `DATABASE_URL`: SQLite URL (`sqlite:///./data/database/jalnetra.db`)
- `DATA_DIR`: Base storage path (`./data`)
- `FRONTEND_URL`: Allowed CORS origin (`http://localhost:5173`)

*Note: Future integration credentials (`SENTINEL_CLIENT_ID`, `OPENAI_API_KEY`, etc.) are optional placeholders and not required during Phase 0.*

---

## Getting Started

### 1. Backend Setup

```bash
cd backend
python -m venv .venv

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

Run the backend server:

```bash
uvicorn app.main:app --reload --port 8000
```

- Health Endpoint: [http://localhost:8000/health](http://localhost:8000/health)
- API v1 Health: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- Swagger OpenAPI Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will run on [http://localhost:5173](http://localhost:5173). It connects to the backend and displays the active connection status badge.

---

## Running Tests

### Backend Tests

From the `backend` directory (with virtual environment activated):

```bash
pytest
```

Runs tests verifying configuration loading, path resolution, database creation, Swagger documentation, and health endpoints.

### Frontend Production Build

From the `frontend` directory:

```bash
npm run build
```

---

## Roadmap & Future Phases

- **Phase 1**: Water-Body Catalog & Discovery (GeoJSON/Shapefile ingestion, bounding boxes, metadata).
- **Phase 2**: Sentinel-2 Imagery Acquisition & Tile Processing.
- **Phase 3**: Water Surface Extraction, Spectral Indices (NDWI, MNDWI), & Machine Learning Classification.
- **Phase 4**: Temporal Trend Analysis, Anomaly Detection, Alerting & Report Generation.
