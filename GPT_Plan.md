# JalNetra — Complete Project Rebuild Plan

The right approach is to rebuild JalNetra from a clean foundation, not rebuild every part of the old codebase exactly as it exists today. We should preserve its valuable features, simplify its architecture, and test every major module before moving to the next one.

I inspected the GitHub repository at [surajgharde/JalNetra](https://github.com/surajgharde/JalNetra), including its backend API, imagery integration, configuration, storage and caching, water-body discovery, and documented processing pipeline. I have also taken our earlier discussions about JalNetra into account.

The existing project already documents a significant amount of functionality, including satellite ingestion, water-body detection, spectral indicators, anomaly detection, alerts, validation, reports, and IoT telemetry. The README also identifies a real multi-tile processing issue that we should explicitly prevent in the rebuild. These are useful requirements to preserve, even though we should simplify how they are implemented.&#x20;

## 1. Our vision for the new JalNetra

[swissEO S2-SR](https://images.openai.com/static-rsc-4/SGcvZ_0fs8Mu8Dnf6V6yEvPHtZkw9pFTaIhIW-zy74H4grx7W6t8R0DvGgUKuFfre5ISTjxaW-jo20haek5_b4G_OhDxadqJ0WV9rbjhVKe849L6pxDui5uxf40tNBT_c0FRDKGQs8QSRVxeWTNcvOn8PrS_G4QmjPVp6bCKyWU?purpose=inline)

[Introducing BlueDot — Water Resources Monitoring from Space | Sinergise](https://images.openai.com/static-rsc-4/p_-nz7O7cEyrcg3zOk8Wk1R4wDExTGaPgo4WJwDWMUE4uZtqCErAP9tVuxjTJb4VoAdiJz9Akd8gMx0esAPlr-i14PwTbwOH2ImucEbZwNtDatCCmF6Ev3fUcETc3lCW5sPF4UkrtVa8bXUIot5BNojlMZbM5zX0ZP4jmyKn_0Y?purpose=inline)

[H2O Quality Quantity — Visual Eco Geo](https://images.openai.com/static-rsc-4/UnNxCYTkZJiHvgXeWzH0fcLWTGM3As_h7CryM8UO1y8AUMN4xYG_dD-AWCP2GNzt1EhvIhqJqvxh61IZAYp711ZKyM00z3xaa_zlchEAFMB-5vkiuS_irJSUeeUBMInmaOx08jjBidvLiM_x22fTI8LODk8TgyMvD4P4CbBXZbE?purpose=inline)

11

JalNetra will be a web-based water-monitoring and geospatial analysis platform that uses Sentinel-2 satellite data to discover water bodies worldwide, view them on an interactive map, analyze their historical and recent conditions, and save processed data locally for fast access.

### Core principles

- Backend: FastAPI with a clean modular Python architecture.
- Frontend: A modern, responsive, light-themed website with a green-and-orange color palette.
- Mapping: A real interactive geographic map with switchable base maps, satellite imagery, water bodies, and analysis overlays.
- Satellite data: Sentinel-2 imagery, with cloud-aware scene selection and processing.
- Water-body imagery: Satellite imagery and water-specific analysis should focus on the selected water body's actual geographic boundary.
- Local storage: Save downloaded metadata, processed measurements, imagery and reusable results on your computer.
- Performance: Once compatible data has been downloaded and processed, reuse it instead of downloading it again unnecessarily.
- Global discovery: Search by country, city, lake, reservoir, river or map coordinates, rather than restricting the application to predefined water bodies.
- Extensibility: Keep storage and processing interfaces modular so we can add cloud storage, such as object storage in the cloud, later without rewriting the application.

### Design requirements

Official geospatial dashboard

Real map, clear data panels, compact navigation, readable typography and well-organized controls.

Green-and-orange visual identity

White or off-white backgrounds, green for water and healthy-state indicators, orange for attention and selected actions.

Sharp, practical interface

Square-corner panels, rectangular buttons, purposeful spacing and minimal decorative effects. No dark theme or rounded-card-heavy design.

The website should feel like an official water-resource monitoring tool, not a generic AI-generated dashboard.

## 2. Repository audit: what we are preserving

The current repository contains a backend with versioned FastAPI endpoints, a React/TypeScript frontend, satellite processing services, database models and migrations, background jobs, and automated tests. Its documented implementation is organized into thirteen principal processing layers, with additional discovery functionality.

The new project should keep the capabilities, but not necessarily the old infrastructure.

| Existing capability                                  | Rebuild decision                                    |
| ---------------------------------------------------- | --------------------------------------------------- |
| Water-body registry and geographic boundaries        | Keep                                                |
| Search and discovery of water bodies                 | Keep and extend globally                            |
| Sentinel-2 search and imagery acquisition            | Keep                                                |
| Live satellite imagery and map tiles                 | Keep, simplify integration                          |
| Cloud masking and water detection                    | Keep                                                |
| Spectral indicators and historical charts            | Keep                                                |
| Seasonal baselines and anomaly detection             | Keep, introduce incrementally                       |
| Anomaly scoring and explanations                     | Keep                                                |
| Alerts, status management and investigation evidence | Keep                                                |
| Field validation and feedback                        | Keep                                                |
| PDF and CSV reports                                  | Keep                                                |
| IoT data integration                                 | Preserve as an optional module                      |
| Saved and recent water bodies                        | Keep                                                |
| API documentation, health checks and tests           | Keep                                                |
| Background task processing                           | Add only when needed                                |
| PostgreSQL, Redis, MinIO and separate services       | Replace initially with a simpler local architecture |
| Cloud storage                                        | Future extension, not a first-stage dependency      |

The previous codebase should serve as the functional reference, rather than becoming a dependency of the new application. We will implement and validate each feature in the rebuilt project independently.

## 3. Recommended technology stack

For the first version, use a local-first architecture that is easy to run, debug and rebuild on your computer.

JalNetra frontend

React · TypeScript · Vite · Leaflet

Map, search, layer controls, charts and reports

REST API · JSON · image/tile URLs

FastAPI backend

Search · Satellite service · Processing · Cache · API validation

SQLite

Water-body records, observations, job status, saved searches and metadata.

Local data directory

Downloaded imagery, processed rasters, derived images, cache manifests and exports.

External geospatial data services

Sentinel-2 catalog · Copernicus data access · Optional Google Earth Engine · Global water-body datasets

### Why this stack?

| Component          | Recommendation                                                                     | Reason                                                                    |
| ------------------ | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Backend            | FastAPI + Pydantic                                                                 | Clear APIs, request validation and built-in interactive API documentation |
| Database           | SQLite + SQLAlchemy                                                                | No separate database server required at the start                         |
| Geographic queries | Shapely + GeoJSON; add GeoPackage/Spatialite if justified                          | Manage water boundaries and geographic intersections                      |
| Raster processing  | Rasterio, NumPy and GDAL-compatible tooling                                        | Read, process, mask and export satellite bands                            |
| Satellite catalog  | STAC-compatible client                                                             | Search scenes by location, date and cloud coverage                        |
| Frontend           | React + TypeScript + Vite                                                          | Maintainable website structure and typed API integration                  |
| Interactive maps   | Leaflet                                                                            | Layers, vector boundaries, markers, selection and map controls            |
| Charts             | Recharts or a lightweight charting library                                         | Historical trends, indicators and water-extent changes                    |
| Images and exports | Local files with indexed metadata                                                  | Reuse previously acquired data without repeated downloads                 |
| Task execution     | FastAPI background tasks for small operations; a persistent job runner when needed | Start with fewer moving parts without blocking expensive processing       |

Important distinction: the local database and the local file cache serve different purposes. SQLite tracks what data exists and where it is stored. The filesystem holds the larger image and raster files. This keeps the application simpler and makes a future cloud-storage migration much easier.

We should not start by adding PostgreSQL, Redis, MinIO, Celery, Docker-only requirements, Grafana and several independent workers. The existing code documents all of these, but they are unnecessary dependencies for validating the rebuilt local version. Some may become useful when JalNetra needs concurrent users, large processing queues or remote deployment.

## 4. Architecture and folder structure

Keep one Python backend and one frontend, with clear boundaries between data discovery, satellite acquisition, processing, persistence and user-facing APIs.

```

JalNetra/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── paths.py
│   │   │   └── logging.py
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── health.py
│   │   │       ├── search.py
│   │   │       ├── water_bodies.py
│   │   │       ├── imagery.py
│   │   │       ├── observations.py
│   │   │       ├── indicators.py
│   │   │       ├── alerts.py
│   │   │       ├── jobs.py
│   │   │       ├── reports.py
│   │   │       └── iot.py
│   │   ├── schemas/
│   │   ├── db/
│   │   │   ├── models/
│   │   │   ├── session.py
│   │   │   └── migrations/
│   │   ├── services/
│   │   │   ├── discovery/
│   │   │   ├── satellite/
│   │   │   ├── processing/
│   │   │   ├── water_detection/
│   │   │   ├── indicators/
│   │   │   ├── anomaly/
│   │   │   └── reports/
│   │   └── tests/
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── features/
│   │   │   ├── map/
│   │   │   ├── search/
│   │   │   ├── water-bodies/
│   │   │   ├── imagery/
│   │   │   ├── indicators/
│   │   │   ├── alerts/
│   │   │   └── reports/
│   │   ├── store/
│   │   ├── styles/
│   │   └── App.tsx
│   └── package.json
├── data/
│   ├── jalnetra.db
│   ├── water_bodies/
│   ├── scenes/
│   ├── processed/
│   ├── tiles/
│   ├── cache/
│   ├── exports/
│   └── manifests/
├── scripts/
├── docs/
├── .gitignore
└── README.md

```

The exact modules can evolve, but we should establish the boundaries early. The frontend must not contain satellite-processing logic, and API route files should not become giant files that perform HTTP requests, raster processing and database writes all at once.

One especially important rule: every feature must be usable through a service interface, so switching from a local data folder to cloud object storage later does not require rewriting map components or analytical logic.

## 5. Phased implementation roadmap

We will build and test the project one phase at a time. A phase is complete only when its acceptance checks pass on your computer. We will not build the entire system in one large code-generation step.

## Phase 0 — Clean setup and working foundation

Foundation

Establish the new repository, Python environment, frontend development server, configuration and local data paths.

Tasks

- Create clean `backend`, `frontend`, `data`, `scripts` and `docs` directories.
- Set up FastAPI and its health endpoint.
- Set up React, TypeScript, Vite and the light-theme design tokens.
- Configure environment variables, logging, error responses and CORS.
- Add `.gitignore` rules for downloaded scenes, databases, generated images and secrets.

Acceptance check: both servers start, the website loads, `/health` responds correctly and the frontend can call the backend.

## Phase 1 — Local database and file cache

Define what is stored, where it lives and how it is reused.

Tasks

- Create models for water bodies, geographic boundaries, satellite scenes, downloaded assets, analysis runs, observations and cached products.
- Build database initialization and migrations.
- Implement a local asset registry and checksums or other integrity checks.
- Store creation time, source, acquisition date, processing version, coverage and asset paths.
- Handle incomplete downloads and interrupted processing safely.

Acceptance check: fetch or register one sample asset, restart the backend and load the same record and file without losing state.

## Phase 2 — Global water-body discovery

Build discovery independently of satellite downloading.

Tasks

- Add place-name search and geographic autocomplete.
- Discover water polygons from appropriate global and regional datasets.
- Support selection by coordinates, bounding box and map click.
- Return names when known, location, area, geometry, source and an available-data status.
- Deduplicate matches using source identifiers and geometry overlap.
- Paginate large result sets and cache discovery responses.

Acceptance check: discover water bodies in multiple countries and open their geographic outlines without requiring preloaded JalNetra records.

Design note: we should combine data sources rather than assume one dataset contains every water body. Source coverage, licensing, naming and polygon completeness vary.

## Phase 3 — Sentinel-2 catalog and scene acquisition

Implement satellite searching before complex analytics.

Tasks

- Query a STAC-compatible catalog for Sentinel-2 Level-2A scenes.
- Search by selected water-body boundary, dates, coverage and cloud metadata.
- Display available acquisitions and allow date selection.
- Download only the required spectral bands and geographic window.
- Track per-band resolution, CRS, transform, nodata values and processing metadata.
- Prevent duplicate downloads of the same asset revision.

Acceptance check: select a known water body and date range, identify suitable scenes, download a test product and reload it from local storage.

Important: Sentinel-2's nominal revisit and cloud conditions do not guarantee a clear observation on a specific date. The interface must distinguish no acquisition, cloud-obscured imagery and usable imagery.

## Phase 4 — Actual map and satellite imagery

Build the interactive map around the newly validated data pipeline.

Tasks

- Add geographic base maps and map navigation.
- Draw water-body boundaries and selection highlights.
- Display Sentinel-2 true-colour imagery and additional visualization layers.
- Restrict the displayed water-analysis image to the selected water body's boundary, without losing its surrounding geographic context on the base map.
- Implement layer visibility, opacity, date selection, legend and zoom-to-body.
- Add image-loading states, missing-tile handling and attribution.

Acceptance check: click a discovered lake, switch basemaps, load imagery for a selected acquisition and toggle overlays without breaking the map.

## Phase 5 — Cloud masking and water detection

Turn satellite pixels into valid water-specific data products.

Tasks

- Align all bands to a defined analysis grid.
- Mask cloud, cirrus, cloud shadow, snow and invalid pixels using scene classification and quality checks.
- Compute MNDWI for water detection.
- Apply thresholding, morphology and the selected water-body geometry as constraints.
- Store water-mask rasters and measurements such as water area, valid-pixel proportion and estimated cloud coverage.
- Handle water bodies spanning multiple Sentinel-2 tiles or scenes by mosaicking compatible data before processing.

Acceptance check: inspect the output against a sample scene, check water boundaries visually and numerically, and confirm that invalid or badly obscured scenes are marked unusable rather than silently treated as good data.

## Phase 6 — Spectral indicators and history

Implement reproducible scientific calculations with explicit limitations.

Tasks

- Add the existing NDTI-based turbidity proxy, NDCI-based chlorophyll proxy, FAI floating-algae indicator, sediment proxy and MNDWI-derived water extent.
- Store aggregate measurements per observation, and optionally per zone.
- Add time-series queries, observation comparison and seasonal plots.
- Keep missing values separate from numeric zero.
- Display source date, cloud-free coverage, spatial resolution and indicator explanation.

Acceptance check: compute indicators for a known scene, verify calculations against independent numerical fixtures, and plot observations from multiple dates.

## Phase 7 — Baselines and anomaly analysis

Reintroduce the former project's most important intelligence features after the underlying measurements are reliable.

Tasks

- Build historical and seasonal reference ranges.
- Compare current observations with relevant historical observations.
- Add robust temporal deviation scores, spatial cluster detection and a multivariate detector when sufficient history is available.
- Incorporate rainfall as contextual evidence.
- Combine detector results into a transparent priority score.
- Track uncertainty, baseline sufficiency and reasons for suppressed findings.

Acceptance check: test normal, unusual and insufficient-history cases with controlled fixtures. Do not allow a lack of historical data to produce a confident anomaly.

## Phase 8 — Alerts and investigation workflow

Turn useful anomaly signals into traceable investigation records.

Tasks

- Create alerts from qualifying candidates.
- Show location, time, evidence, confidence, indicators and comparison with baseline.
- Track open, investigating, validated and dismissed statuses.
- Deduplicate repeated signals into ongoing episodes.
- Include a clear explanation and the limitations of satellite-based screening.
- Keep an audit history of status changes.

Acceptance check: simulate a confirmed anomaly case, verify alert creation, update its status and make sure repeated observations do not create needless duplicate alerts.

## Phase 9 — Reports and field validation

- Export observations to CSV and generate PDF investigation reports.
- Include a satellite image, water mask, indicator summaries, trends and evidence dates.
- Add field measurements, optional photos and validation outcomes.
- Compare field validation against alerting rules without allowing unverified values to silently retrain an ML model.

Acceptance check: export a report from a real stored analysis and confirm its measurements match the database.

## Phase 10 — IoT, notifications and advanced features

- Add the existing water-quality sensor data integration as a separate feature.
- Normalize incoming readings and store device, timestamp and measurement metadata.
- Support configurable notification channels such as email or Telegram if still required.
- Connect in-situ readings with nearby water-body and satellite observations where the spatial and temporal relationship is valid.
- Add improved ML scoring only when reliable validation data exists.

Acceptance check: test the feature with sample telemetry, including missing fields, disconnections, out-of-range readings and duplicate messages.

## Phase 11 — Hardening and release

- Verify the complete workflow on a clean computer setup.
- Add unit, API and integration tests for real data flows.
- Check data persistence, cache hits, disk usage, large-map performance and interrupted tasks.
- Document setup, environment variables, data-source attribution and troubleshooting.
- Keep sensitive credentials and large generated products out of version control.
- Design a storage adapter for a future cloud backend.

Acceptance check: a new clone can be installed, configured and started using the README, and a previously acquired dataset can be reused without a fresh download.

### Recommended implementation priority

The first milestone should be deliberately small: Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4. That produces a stable, globally searchable satellite-map application with local persistence before we attempt the more demanding analysis and anomaly-detection layers.

## 6. Worldwide water-body discovery: how it should work

This is one of the most important technical decisions in JalNetra.

The system needs two separate capabilities:

[New global database will help scientists track role of lakes in Earth's ecology](https://images.openai.com/static-rsc-4/-gQMUfZ_adqW6_BJHlel-U3inW0xNQQb2A7gWJOpORbiCVWmZR2xJGyiplO4DMX8Ieg4rRAe4LNEQCrQf6fYcknautfrS9-McnmyiNxUqbra5nqXPsTRCfyWLnw7lnxRsMcT8GV9Vj2X6VfgeV3diTUpgjj_o9zHlXBFo_fZl08?purpose=inline)

A. Find water bodies

Use geographic datasets, place-name search and map coordinates to discover candidate lakes, reservoirs, rivers and other water features. Save the selected feature's geometry and source metadata locally.

[Exploring Earth From Space: Lake Trasimeno – The Fourth Largest Lake in Italy](https://images.openai.com/static-rsc-4/00iSoidaZN6AV-aSpZfI4gmbh6H3PBmG-_Fac5l3YHxhEPbqVKAZ-nCy60dn12MCUJGl9A-12omh5HYoA-x9NagCSw2ULM5bMh6JLEFSHWQxn1Cykz0J-BsCAuttcNLrSBOFF7fkl8bBAI1DZELIzOxFSLPNI2TErXl7Jn7nzsU?purpose=inline)

B. Retrieve satellite data

Use the selected water body's boundary to query available Sentinel-2 scenes, acquire the required assets, process them and cache the results. The same data should be reused for a matching future request.

These must remain separate services. Discovering a lake should be quick and should not automatically download years of satellite imagery.

### Search behavior we should build

1. The user types a place name, water-body name or coordinate.
2. JalNetra returns matching locations and water-body candidates.
3. The map zooms to the selected feature and displays its boundary.
4. The user selects a date range and requests satellite data.
5. JalNetra checks its local index for reusable scenes, assets and processed results.
6. Only missing or outdated data is requested from the configured satellite source.
7. The data is processed, indexed and added to the map.
8. A repeat request loads valid cached data first and fetches only what is missing.

For rivers, very large reservoirs and water bodies spanning multiple satellite tiles, we must divide processing into manageable geographic windows and assemble compatible results.

Global coverage limitation: no single water-body dataset should be assumed to include every small pond, seasonal water feature or unnamed river segment. We should use multiple data sources where appropriate and clearly communicate incomplete coverage.

## 7. Local storage and caching strategy

We want repeat searches to be fast without creating a confusing collection of duplicate files.

| Data category                                 | Location                         | Reuse rule                                                    |
| --------------------------------------------- | -------------------------------- | ------------------------------------------------------------- |
| Water-body names, boundaries and metadata     | SQLite                           | Query locally; refresh source metadata when required          |
| Satellite scene catalogue results             | SQLite + cache manifest          | Reuse according to defined freshness rules                    |
| Downloaded spectral bands                     | `data/scenes/`                   | Reuse when the source asset and processing requirements match |
| Water masks and indicator rasters             | `data/processed/`                | Reuse when scene, boundary and algorithm versions match       |
| Rendered image tiles                          | `data/tiles/` or cache directory | Reuse compatible tiles                                        |
| Analysis observations and alert history       | SQLite                           | Retain, update through versioned analysis runs                |
| CSV and PDF exports                           | `data/exports/`                  | Keep for later download                                       |
| Search responses and small temporary metadata | `data/cache/`                    | Expire or refresh according to cache policy                   |

### Cache keys and invalidation

A cache entry should not simply be identified by the lake name. We should use stable identifiers based on the water-body geometry, satellite scene identifier, relevant source asset revision, requested date range, processing version and visualization settings.

For processed products, the application should check:

- Does the required local file actually exist?
- Is the file complete and readable?
- Does its metadata match the requested scene and water-body geometry?
- Was it created with the current processing version?
- Does it provide adequate valid-pixel coverage for the requested analysis?

If a water-body boundary or algorithm changes, only affected products need to be regenerated.

We should also track storage size, provide a way to clear disposable cached items and distinguish those items from records that the user has deliberately saved.

### Future cloud migration

Introduce a small storage interface now, for example `LocalAssetStore`, with operations to save, retrieve, test existence and delete an asset. A later cloud implementation can follow the same interface.

The cloud migration should not require rewriting the satellite pipeline, database models or frontend.

## 8. Satellite layers to implement

The map should be the central working area, with clearly named layers grouped by purpose.

Group 1 — Base map

Geographic context independent of the satellite-analysis product.

Road/street map, terrain where available, satellite basemap and water-body boundaries.

Group 2 — Satellite imagery

Actual Sentinel-2 acquisitions and image composites.

True colour, false colour, selected acquisition date and cloud-aware imagery. Add alternate composites only when supported by the data and desired workflow.

Group 3 — Water and analysis overlays

Computed products, with distinct legends and explicit processing dates.

Water mask, MNDWI, NDTI turbidity proxy, NDCI chlorophyll proxy, FAI floating-algae indicator, sediment proxy, water-extent changes, anomaly zones and validated alert areas.

The interface should have a layer panel, opacity controls, legend, acquisition-date selection and a way to return to the selected water body's default view.

Not every layer will be available for every scene. The application must disable unavailable layers or explain why data is missing instead of showing misleading blank overlays.

One particularly important distinction: Sentinel-2 true-colour imagery, a third-party satellite basemap and a derived water-analysis raster are different products. We should label them correctly and preserve the acquisition date and data-source attribution.

## 9. Features from the earlier JalNetra project

We should maintain a central feature inventory so nothing valuable is forgotten during the rebuild.

## Feature checklist

0/30 marked complete

### Discovery and maps

Global place and water-body search

Dynamic water-body discovery and registration

Saved and recently viewed water bodies

Interactive map and layer controls

Satellite acquisition timeline

### Satellite processing

Sentinel-2 scene search and download

Cloud and shadow masking

Water-body-specific imagery

MNDWI water detection and extent

NDTI, NDCI, FAI and sediment proxy indicators

Multi-tile mosaicking and zonal analysis

### Water intelligence

Historical charts and seasonal baselines

Temporal and spatial anomaly detection

Multivariate anomaly detection

Rainfall contextual analysis

Priority score and explanation

### Investigation

Alert queue and status tracking

Alert deduplication and evidence timeline

PDF and CSV reports

Field validation and photo upload

Validation metrics and cautious model improvement

### Integrations

IoT buoy live telemetry

Optional AI-assisted telemetry summary

Email or Telegram notification delivery

Health endpoint and structured logs

### Reliability

Local persistent storage

Reusable data and image cache

Job progress and failure recovery

API validation and automated tests

Storage adapter for future cloud use

Reset checklistCopy status

Use this inventory as a feature tracker, not as an instruction to build every feature immediately. Optional integrations, model training and production monitoring come after the central satellite workflow is stable.

## 10. Improvements we should make to the old implementation

The README documents one especially relevant failure: a water body spanning two Sentinel-2 tiles can have two scenes on the same date, causing a later raster to overwrite an earlier result and producing a shape mismatch during subsequent processing.

The new implementation should address that class of problem through explicit scene grouping, grid normalization and a well-defined mosaicking stage.

| Risk                                         | Required improvement                                                |
| -------------------------------------------- | ------------------------------------------------------------------- |
| Re-downloading the same images               | Indexed asset manifests and source-aware caching                    |
| Partial or interrupted downloads             | Temporary files, integrity verification and atomic finalization     |
| Misaligned spectral bands                    | One declared analysis grid and explicit resampling rules            |
| Multi-tile bodies                            | Deterministic mosaicking before calculating indicators              |
| Cloudy scenes interpreted as water change    | Valid-pixel masks and quality thresholds                            |
| Analysis run duplicated after restart        | Idempotent processing jobs and persistent job state                 |
| Old derived images shown after a code change | Version-aware product cache keys                                    |
| Very long downloads blocking the API         | Persistent job execution and progress reporting                     |
| Unreliable anomaly claims                    | Separate data quality, anomaly strength and confidence              |
| Global search overwhelming the machine       | Bounded result counts, windowed downloads and explicit cache limits |

### Do not overpromise scientific conclusions

Sentinel-2 can reveal changes in observable spectral characteristics and water extent, but those measurements are not direct proof of all forms of contamination. The indicators in the earlier repository are proxies; their scientific interpretation depends on the water body, sensor conditions and validation data.

JalNetra should report potential anomalies and their evidence, rather than automatically stating that pollution has been confirmed. Field measurements and reliable reference data remain important.

Also, the previously discussed satellite-image comparison/ML workflow should be treated as a later analytical feature. First establish reproducible satellite acquisition, cloud handling, water-body masks and historical observations. These will provide the consistent data that a future change-detection or machine-learning workflow needs.

## 11. Testing strategy

Every module should have a small, explicit set of tests before we progress.

| Test category     | What it must establish                                                                                           |
| ----------------- | ---------------------------------------------------------------------------------------------------------------- |
| Unit tests        | Geographic geometry, band alignment, formulas, cloud masks, cache keys and data validation behave correctly.     |
| API tests         | Endpoints return the correct schema, meaningful errors and valid pagination.                                     |
| Persistence tests | Restarting the application preserves saved data, and invalid cached files are not treated as valid assets.       |
| Integration tests | A selected water body can be discovered, associated with a satellite scene, downloaded and processed end to end. |
| UI tests          | Search, layer switching, date selection, empty states and error states work on the real API.                     |
| Scientific tests  | Calculations match independent numerical examples and synthetic edge cases.                                      |
| Regression tests  | Known earlier problems, including multi-tile boundaries, do not return.                                          |

We should keep a small reproducible fixture dataset for automated tests. Live calls to satellite providers should be reserved for explicit integration tests because service availability, credentials and download time can vary.

### Definition of done for the first complete milestone

JalNetra's initial end-to-end version is complete when you can:

- Run the backend and frontend locally with documented commands.
- Search for a water body in more than one country and see its boundary.
- Select a body and search for suitable Sentinel-2 acquisitions.
- Download actual data for the selected area, not mock imagery.
- View its satellite image on the interactive map with working layer controls.
- Compute an initial water mask and at least one validated spectral indicator.
- Restart the application and retrieve the saved body, asset and analysis results from local storage.
- Request the same data again and see that compatible cached files are reused.
- Inspect any failed or unavailable operation without losing existing data.

## 12. The immediate build order

This is the practical sequence we should follow when we start coding:

1. Create the clean project and development environment. Confirm Python and Node.js versions, install dependencies and configure the two servers.
2. Implement the backend foundation and local storage. Add SQLite models, persistent data paths, asset manifests and basic health checks.
3. Build a small frontend shell. Implement the header, sidebar/navigation, light green-and-orange theme and an actual Leaflet map.
4. Connect water-body search. Search geographic sources, place discovered water bodies on the map and save selected bodies.
5. Implement the Sentinel-2 catalog and acquisition service. Prove the real satellite-data workflow with a known water body before building advanced overlays.
6. Add local asset reuse and map imagery. Restart the application, load the same scene from disk and confirm that compatible assets are not downloaded again.
7. Add cloud masking, water detection and spectral indicators. Verify every output visually and numerically.
8. Reintroduce the remaining analytics and integrations. Baselines, anomaly detection, alerts, reporting, validation, IoT and optional notifications follow in dependency order.

The guiding rule throughout the rebuild is simple: one working feature, one verification step, then the next feature. We should not move to advanced analytics while the satellite data, map display or local cache is unreliable.

The next concrete deliverable should be the Phase 0 project setup specification: exact dependency choices, environment configuration, initial folders, backend entry point, frontend entry point and commands to verify that both servers communicate successfully. After that foundation works, we can begin implementing the system module by module.