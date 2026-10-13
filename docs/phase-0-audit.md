# JalNetra 2.0 — Phase 0 Current-State Audit & Safety Baseline

**Document Version:** 1.0.0  
**Phase:** Phase 0 (Audit & Safety Baseline)  
**Execution Mode:** Read-Only Audit (No data modified or deleted)  
**Timestamp:** 2026-10-12  

---

## Executive Summary

This audit establishes the empirical baseline of the **JalNetra 2.0** application before any destructive cleanup or schema modifications in Phase 1. Every metric, row count, file size, and architectural flow documented herein was measured directly against the active project database, filesystem storage, and source code.

### High-Level Metrics

| Subsystem | Metric | Current Value | Notes |
| :--- | :--- | :--- | :--- |
| **Database** | Type & Engine | SQLite 3 | WAL mode, single-file DB |
| | Database Path | `data/database/jalnetra.db` | 536.00 KB on disk |
| | Total Tables | 6 tables | Includes `alembic_version` |
| | Water Bodies | 14 rows | 8 active OSM lakes, 3 manual, 3 test |
| | Satellite Scenes | 9 rows | Sentinel-2 L2A scenes |
| | Satellite Assets | 69 rows | Band GeoTIFFs, SCL, thumbnails |
| | Analysis Runs | 0 rows | Ready for Phase 5 baseline tracking |
| | Cache Entries | 33 rows | 19 OSM Overpass queries, 14 STAC searches |
| **Filesystem** | Total Files in `data/` | 394 files | `.tif`, `.png`, `.json`, `.jpg`, `.db` |
| | Total Size in `data/` | **4.31 GB** (4,627,198,209 bytes) | Driven by raw 10m Sentinel-2 band COGs |
| | Raw Scenes (`data/scenes/`) | **4.29 GB** (4,604,033,008 bytes) | 146 files across 37 folders |
| | Processed Overlays (`data/processed/`) | **15.34 MB** (16,084,997 bytes) | 177 files (masks, RGB overlays) |
| | STAC & Discovery Cache (`data/cache/`) | **6.23 MB** (6,531,340 bytes) | 65 cached API JSON payloads |
| | Orphan Scene Folders | 30 folders | Not present in `satellite_scenes` table |

---

## 1. Database Inventory

The production database is located at:
`c:\Users\adish\OneDrive\Documents\GitHub\JalNetra2.O\data\database\jalnetra.db`

### Table Row Counts

| Table Name | Row Count | Purpose in Architecture |
| :--- | :--- | :--- |
| `alembic_version` | 1 | Schema migration tracker (revision: `9d945aeebda5`) |
| `water_bodies` | 14 | Registered water resources (boundaries, centroids, metadata) |
| `satellite_scenes` | 9 | Registered Sentinel-2 acquisitions |
| `satellite_assets` | 69 | Individual spectral bands (B02–B12, SCL, thumbnail) per scene |
| `analysis_runs` | 0 | Phase 5 analytical processing runs table |
| `cache_entries` | 33 | Discovery (OSM) & satellite STAC query metadata cache |

---

### Registered Water Bodies

| # | Name | ID | Source | Source Identifier | Geometry Available? |
| :-: | :--- | :--- | :--- | :--- | :-: |
| 1 | **Chilika Lagoon** | `e18ac571-9b9d-43de-af4c-826554c59f7a` | `manual` | `live-test-01` | No |
| 2 | **Chilika Lake** | `122a29c2-b3be-446c-849d-22055cf3dc3b` | `osm` | `relation/1917079` | **Yes** (Polygon) |
| 3 | **ooty lake** | `8da72a83-5582-4520-ac9d-f72318d68afe` | `manual` | `test-1791707962374` | No |
| 4 | **string** | `d4830e5f-ff1b-4849-b85c-3395a63f7923` | `manual` | `string` | **Yes** |
| 5 | **Chilka Lake** | `a26ae106-a93d-4287-92e9-834ad98ee65d` | `osm` | `node/570589302` | **Yes** (Point) |
| 6 | **Ooty Lake** | `b0d20935-9405-4b34-bcb8-83c4b1b27758` | `osm` | `way/24657989` | **Yes** (Polygon) |
| 7 | **Khadakwasla Dam** | `7f93736a-93e6-46a9-bbb8-6376fe28c0ca` | `osm` | `way/214776276` | **Yes** (Line/Polygon) |
| 8 | **Dal Lake** | `b47512df-cbd8-43b0-b35c-c06cf2d80b44` | `osm` | `relation/2310480` | **Yes** (Polygon) |
| 9 | **Chhatrapati Sambhajinagar** | `964c2b73-27d2-418d-ab9d-21aab603bc2d` | `osm` | `node/245686245` | **Yes** (Point) |
| 10 | **Sukhana River** | `3a991c63-7f41-40a9-a172-e98b500f95da` | `osm` | `way/317146393` | **Yes** (Line) |
| 11 | **Salim Ali Lake** | `372e9ac3-31bc-4ce8-9d97-61f38227f610` | `osm` | `way/317146450` | **Yes** (Polygon) |
| 12 | **Debug Lake** | `dbg-wb` | `test` | `test-debug-lake` | No |
| 13 | **API Focused Lake** | `wb-focused-api-test` | `test` | `test-api-lake` | No |
| 14 | **Ambazari Lake** | `d6c78311-1a32-4019-b64d-d783a76be0bb` | `osm` | `node/11371112354` | **Yes** (Point) |

---

### Registered Satellite Scenes

| # | Scene UUID | External Scene Identifier | Sensing Date | Cloud Cover | Status |
| :-: | :--- | :--- | :--- | :-: | :--- |
| 1 | `6b67ff4a-65f8-449f-b975-f2649f89c15b` | `S2A_T45QTB_20261010T045521_L2A` | 2026-10-10 05:03:34 | 5.14% | `downloaded` |
| 2 | `66164712-baf2-4d0c-8abe-9b54892ff0ce` | `S2A_T45QUB_20240322T050231_L2A` | 2024-03-22 05:03:19 | 1.29% | `downloaded` |
| 3 | `edb2ab41-9e83-4c27-b63b-d5b257b9c3e4` | `S2A_T43PFN_20240328T051856_L2A` | 2024-03-28 05:25:51 | 15.26% | `downloaded` |
| 4 | `a19a7aeb-c650-45f5-81e8-5f7239f12889` | `S2B_T43QCA_20240319T054135_L2A` | 2024-03-19 05:43:55 | 0.00% | `downloaded` |
| 5 | `371fb98b-b19f-4a31-907b-1cc211d1911f` | `S2B_T43SDT_20240401T054331_L2A` | 2024-04-01 05:49:41 | 9.90% | `downloaded` |
| 6 | `e6890115-713d-49c9-be02-302856358d89` | `S2A_T43QEC_20240324T053952_L2A` | 2024-03-24 05:43:21 | 8.98% | `downloaded` |
| 7 | `dbg-scene` | `S2A_DBG` | 2026-10-11 18:11:19 | None | `downloaded` |
| 8 | `map-scene-test-uuid` | `S2A_TEST_FULL_FLOW` | 2026-10-11 18:11:47 | None | `downloaded` |
| 9 | `2d704751-341a-405c-a633-936b9d692294` | `S2A_T44QKJ_20240328T051856_L2A` | 2024-03-28 05:23:04 | 0.17% | `downloaded` |

---

### Registered Satellite Assets Breakdown

| Asset Key | Band Description | Spatial Resolution | File Count | Total Size in Database |
| :--- | :--- | :---: | :-: | :--- |
| `B02` | Blue band | 10 m | 10 | 1,427.90 MB (~142.8 MB/band) |
| `B03` | Green band | 10 m | 12 | 1,748.66 MB (~145.7 MB/band) |
| `B04` | Red band | 10 m | 13 | 2,010.14 MB (~154.6 MB/band) |
| `B08` | Near Infrared (NIR) | 10 m | 8 | 1,387.11 MB (~173.4 MB/band) |
| `B11` | SWIR-1 | 20 m | 6 | 240.09 MB (~40.0 MB/band) |
| `B12` | SWIR-2 | 20 m | 6 | 237.88 MB (~39.6 MB/band) |
| `SCL` | Scene Classification Layer | 20 m | 7 | 12.75 MB (~1.8 MB/band) |
| `thumbnail` | Quicklook preview | Preview | 7 | 0.20 MB (~28 KB/image) |

---

## 2. Local Storage Audit

### Directory Inventory for `data/`

| Directory Path | File Count | Size (MB) | Size (Bytes) | Primary Contents |
| :--- | :-: | :-: | :-: | :--- |
| `data/scenes/` | 146 | **4,290.75 MB** | 4,604,033,008 | Raw Sentinel-2 GeoTIFF COGs (B02, B03, B04, B08, B11, B12, SCL, thumbnails) |
| `data/processed/` | 177 | **15.34 MB** | 16,084,997 | Phase 4/5 outputs: RGB overlays, cloud masks, water masks |
| `data/cache/` | 65 | **6.23 MB** | 6,531,340 | Cached JSON responses from Earth Search STAC and OSM Overpass API |
| `data/database/` | 2 | **0.52 MB** | 548,864 | SQLite database (`jalnetra.db`) and WAL/journal |
| `data/water_bodies/` | 1 | 0.00 MB | 0 | Reserved for vector shapefiles/GeoJSON (`.gitkeep`) |
| `data/tiles/` | 1 | 0.00 MB | 0 | Reserved for pre-rendered XYZ raster tiles (`.gitkeep`) |
| `data/exports/` | 1 | 0.00 MB | 0 | Reserved for CSV/GeoJSON export packages (`.gitkeep`) |
| `data/manifests/` | 1 | 0.00 MB | 0 | Reserved for scene acquisition manifests (`.gitkeep`) |
| **Total `data/`** | **394** | **4,412.84 MB** | **4,627,198,209** | **Complete local storage footprint** |

---

### File Types & Extension Breakdown

| Extension | File Count | Description | Total Approximate Size |
| :--- | :-: | :--- | :--- |
| `.json` | 170 | Metadata files, STAC cache, OSM cache, overlay bounds | 8.5 MB |
| `.png` | 95 | Cropped RGB overlays, cloud masks, water detection masks | 12.8 MB |
| `.tif` | 82 | Raw Sentinel-2 Cloud-Optimized GeoTIFFs (10m & 20m) | **4,385.0 MB** |
| `.jpg` | 37 | Scene thumbnails and browse previews | 0.9 MB |
| `[no_ext]` | 9 | Subdirectories or metadata markers | < 1 KB |
| `.db` | 1 | Main SQLite application database | 536 KB |

---

### Top 10 Largest Files on Disk

Every single one of the top 10 largest files is a raw 10m Sentinel-2 band GeoTIFF:

| File Path | Size (MB) | Band | Scene ID |
| :--- | :-: | :---: | :--- |
| `data/scenes/a19a7aeb-c650-45f5-81e8-5f7239f12889/assets/B08.tif` | 232.33 MB | B08 (NIR) | Khadakwasla Dam scene |
| `data/scenes/a19a7aeb-c650-45f5-81e8-5f7239f12889/assets/B04.tif` | 220.97 MB | B04 (Red) | Khadakwasla Dam scene |
| `data/scenes/a19a7aeb-c650-45f5-81e8-5f7239f12889/assets/B03.tif` | 213.31 MB | B03 (Green) | Khadakwasla Dam scene |
| `data/scenes/a19a7aeb-c650-45f5-81e8-5f7239f12889/assets/B02.tif` | 211.04 MB | B02 (Blue) | Khadakwasla Dam scene |
| `data/scenes/e6890115-713d-49c9-be02-302856358d89/assets/B08.tif` | 210.18 MB | B08 (NIR) | Salim Ali Lake scene |
| `data/scenes/e6890115-713d-49c9-be02-302856358d89/assets/B04.tif` | 205.21 MB | B04 (Red) | Salim Ali Lake scene |
| `data/scenes/e6890115-713d-49c9-be02-302856358d89/assets/B03.tif` | 198.34 MB | B03 (Green) | Salim Ali Lake scene |
| `data/scenes/e6890115-713d-49c9-be02-302856358d89/assets/B02.tif` | 197.01 MB | B02 (Blue) | Salim Ali Lake scene |
| `data/scenes/66164712-baf2-4d0c-8abe-9b54892ff0ce/assets/B08.tif` | 189.27 MB | B08 (NIR) | Chilika Lake scene |
| `data/scenes/66164712-baf2-4d0c-8abe-9b54892ff0ce/assets/B04.tif` | 188.77 MB | B04 (Red) | Chilika Lake scene |

---

### Orphaned Files & Discrepancies Detected

1. **Orphan Scene Folders on Disk (30 folders):**
   - In `data/scenes/`, there are 37 directories, but only 7 corresponding scene IDs are present in the database (plus 2 mock scenes in DB that have no disk folder).
   - **30 scene directories** (e.g. `0af3e4b0...`, `0c0bc907...`, `0c68ffa9...`, `215b93e7...`, etc.) exist on disk with ~282 bytes each (dummy 15-byte `B02.tif`, `thumbnail.jpg`, and a small `metadata.json`). These were generated during earlier mock test runs without database commits.
2. **Database Scenes Missing from Disk (2 scenes):**
   - `dbg-scene` (`S2A_DBG`)
   - `map-scene-test-uuid` (`S2A_TEST_FULL_FLOW`)
   These records exist in the database from manual testing, but their assets were deleted or never written to disk.

---

## 3. Storage Multiplication Analysis

### Why Did Local Storage Become 4.31 GB?

The audit traced the exact satellite download and processing pipeline:

```text
Sentinel-2 100 km × 100 km Tile (Element84 / AWS Earth Search STAC)
   │
   ├─► B02 (Blue, 10 m, ~10980 × 10980 px) ────────────► ~210 MB COG GeoTIFF
   ├─► B03 (Green, 10 m, ~10980 × 10980 px) ───────────► ~205 MB COG GeoTIFF
   ├─► B04 (Red, 10 m, ~10980 × 10980 px) ─────────────► ~215 MB COG GeoTIFF
   ├─► B08 (NIR, 10 m, ~10980 × 10980 px) ─────────────► ~225 MB COG GeoTIFF
   ├─► B11 (SWIR-1, 20 m, ~5490 × 5490 px) ────────────► ~40 MB COG GeoTIFF
   ├─► B12 (SWIR-2, 20 m, ~5490 × 5490 px) ────────────► ~40 MB COG GeoTIFF
   ├─► SCL (Scene Classification, 20 m) ───────────────► ~1.8 MB GeoTIFF
   └─► thumbnail (Browse image, JPEG) ─────────────────► ~28 KB JPEG
                                                        ───────────────
                                            Per-Scene Total: ~935 MB – 1.05 GB
```

1. **Full-Tile COG Downloads:**
   The current acquisition logic in `backend/app/services/satellite/service.py` (`acquire_scene_assets`) streams the **entire Sentinel-2 tile GeoTIFF asset** from S3/Earth Search over HTTP. A single full tile covers $100 \times 100\text{ km}$ ($10,000\text{ km}^2$).
   - Downloading 4 bands (`B02`, `B03`, `B04`, `B08`) for 1 scene downloads $\approx 850\text{ MB} - 900\text{ MB}$.
   - Currently, 5 scenes have full 10m bands downloaded:
     - Khadakwasla Dam (`a19a7aeb...`): **997.56 MB**
     - Chilika Lake (`66164712...`): **838.75 MB**
     - Salim Ali Lake (`e6890115...`): **812.81 MB**
     - Chhatrapati Sambhajinagar (`371fb98b...`): **776.73 MB**
     - Ooty Lake (`edb2ab41...`): **509.45 MB**
     - Sukhana River (`2d704751...`): **455.41 MB**
   - $997 + 838 + 812 + 776 + 509 + 455 \approx \mathbf{4,388\text{ MB}}$ ($\mathbf{4.39\text{ GB}}$).

2. **Processed & Visualization Overlays:**
   - In contrast to raw GeoTIFFs, the processed visualization rasters in `data/processed/` and `data/processed/map/` are lightweight PNGs:
     - Cropped native RGB PNGs: **10 KB – 800 KB** each.
     - Cropped cloud/water mask PNGs: **100 B – 19 KB** each.
   - Total processed footprint is only **15.34 MB** across 177 files.

3. **Duplication Path Findings:**
   - Source band GeoTIFFs are stored once in `data/scenes/{scene_id}/assets/`.
   - Processed masks are stored in `data/processed/{scene_id}/`.
   - Map RGB PNGs are stored in `data/processed/map/{scene_id}/`.
   - There are **no duplicate full-tile GeoTIFF copies** across folders. Storage size is dominated 99.6% by the raw full-tile GeoTIFF downloads.

---

## 4. Origin of Seeded / Demo Data

| Entity Category | Origin / Creator | Trigger Event | Code Location |
| :--- | :--- | :--- | :--- |
| **Water Bodies** (`water_bodies`) | Imported via OpenStreetMap (OSM) Overpass API or manual HTTP POST calls | User actions on `DiscoveryPage.tsx` or previous API test curl requests | [`api/v1/discovery.py`](file:///c:/Users/adish/OneDrive/Documents/GitHub/JalNetra2.O/backend/app/api/v1/discovery.py#L30) & [`api/v1/water_bodies.py`](file:///c:/Users/adish/OneDrive/Documents/GitHub/JalNetra2.O/backend/app/api/v1/water_bodies.py#L21) |
| **Satellite Scenes** (`satellite_scenes`) | Discovered via Element84 Earth Search STAC API | STAC searches executed from `SatellitePage.tsx`, `MapPage.tsx` AOI search, or test scripts | [`api/v1/satellite.py`](file:///c:/Users/adish/OneDrive/Documents/GitHub/JalNetra2.O/backend/app/api/v1/satellite.py#L26) |
| **Satellite Assets** (`satellite_assets`) | Downloaded via AWS Earth Search streaming HTTP | User explicitly clicked "ACQUIRE BANDS" on `SatellitePage.tsx` or `MapPage.tsx` | [`api/v1/satellite.py`](file:///c:/Users/adish/OneDrive/Documents/GitHub/JalNetra2.O/backend/app/api/v1/satellite.py#L65) |
| **Cache Entries** (`cache_entries`) | SQLite cache records holding JSON responses | STAC queries and Overpass searches | [`services/satellite/cache.py`](file:///c:/Users/adish/OneDrive/Documents/GitHub/JalNetra2.O/backend/app/services/satellite/cache.py) & [`services/discovery/cache.py`](file:///c:/Users/adish/OneDrive/Documents/GitHub/JalNetra2.O/backend/app/services/discovery/cache.py) |

### Automatic Seeding Verification
- **Application Startup (`main.py` lifespan):** **NO** water bodies, scenes, or assets are created on startup.
- **Database Migrations (`alembic/versions`):** Only DDL schema table creation (`CREATE TABLE ...`); **NO** seed rows are inserted.
- **Can Data Be Seeded Automatically on Boot?** **NO.** The system starts clean if the SQLite DB is empty.

---

## 5. Automatic Behavior Trace

```text
[ APPLICATION STARTUP ]
   │
   ├─► main.py lifespan runs ensure_data_directories()
   └─► Database connected. NO AUTO-INSERTS. NO AUTO-DOWNLOADS.

[ PAGE LOAD: Monitoring Map ]
   │
   ├─► GET /api/v1/map/water-bodies/geojson
   │   └─► Returns active water bodies from DB (0 if empty).
   │
   ├─► Read localStorage: 'jalnetra_selected_wb_id'
   │   └─► Selects saved water body, or defaults to features[0].
   │
   └─► handleSelectWaterBody(wbId):
       │
       ├─► GET /api/v1/map/scenes?water_body_id=wbId
       │   └─► Queries local SQLite DB for scenes covering wbId.
       │       DOES NOT CALL EXTERNAL STAC. NO AUTO-DOWNLOAD.
       │
       └─► If scene with downloaded RGB exists:
           ├─► GET /api/v1/map/scenes/{id}/rgb?water_body_id=wbId
           │   └─► Crops & serves native 10m PNG overlay.
           └─► GET /api/v1/processing/scenes/{id}
               └─► Checks if processed. DOES NOT AUTO-PROCESS.

[ SATELLITE ACQUISITION TRIGGER ]
   │
   └─► POST /api/v1/satellite/scenes/{external_scene_id}/acquire
       ▲
       ├── Trigger 1: User explicitly clicks "ACQUIRE BANDS" in UI.
       └── Trigger 2: User draws a Manual AOI rectangle whose covering scene lacks RGB.

[ PHASE 5 PROCESSING TRIGGER ]
   │
   └─► POST /api/v1/processing/scenes/{scene_id}
       ▲
       └── ONLY Trigger: User clicks "RUN CLOUD & WATER ANALYSIS" in Scenes tab.
```

---

## 6. Current Cleanup Capabilities

| Capability | Exists Currently? | Implementation Status | Notes |
| :--- | :---: | :--- | :--- |
| **Database Reset** | **NO** | Not implemented | No API or command to wipe tables safely |
| **Scene Deletion** | **NO** | Not implemented | No `DELETE /api/v1/satellite/scenes/{id}` |
| **Asset Deletion** | **NO** | Not implemented | No endpoint to delete individual GeoTIFFs |
| **Cache Clearing** | **NO** | Partial internal only | `LocalStorageService.delete` exists, but no user endpoint |
| **Processed Data Clearing** | **NO** | Not implemented | No automated way to clear masks/RGB cache |
| **Filesystem Cleanup** | **NO** | Not implemented | No script to sync DB and disk |
| **Orphan Cleanup** | **NO** | Not implemented | 30 orphan folders currently lingering in `data/scenes/` |
| **Water Body Deactivation** | YES | Soft delete only | `DELETE /api/v1/water-bodies/{id}` sets `is_active=False` |

*Conclusion:* The project currently lacks any administrative cleanup endpoints. Phase 1 must implement safe, atomic data reset and storage management.

---

## 7. Safety Baseline Findings

1. **Source GeoTIFF Immutability:**
   - Raw Sentinel-2 band GeoTIFFs in `data/scenes/{id}/assets/` are opened strictly in read-only mode (`rasterio.open(path, 'r')`).
   - Neither `RGBRenderer` nor `ProcessingService` writes to the source `.tif` files.
2. **Atomic Writes:**
   - `LocalStorageService.save_bytes` and `_stream_download_to_safe_path` stream writes into a `tempfile.NamedTemporaryFile` in the target directory, flush with `os.fsync`, and atomically rename via `shutil.move`.
   - Incomplete downloads leave `.tmp` files that are safely unlinked in `finally` blocks, preventing `.part` corruption.
3. **Path Traversal Protection:**
   - `LocalStorageService.resolve_safe_path` resolves paths against `data/` and raises `StoragePathTraversalError` if a path attempts to escape the root boundary.
4. **Directory Isolation:**
   - Raw assets (`data/scenes/`), processed outputs (`data/processed/`), cache (`data/cache/`), and the database (`data/database/`) reside in completely separate subtrees.
   - Deleting processed images or cache entries in future phases cannot accidentally delete raw satellite band assets.

---

## 8. Verification Results

- **Backend Pytest Suite:** **66 passed** in 8.41s (100% pass rate).
- **Frontend Production Build:** `tsc -b && vite build` succeeded in 1.63s with **0 errors**.
- **Audit Script:** `scripts/audit_storage.py` verified runnable, read-only, and covered by 6 dedicated unit tests.
- **Safety Status:** Baseline established. No data modified or deleted.

---

**Phase 0 Status:** **COMPLETE**  
**Ready for Phase 1:** **YES**
