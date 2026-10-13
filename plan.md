# JalNetra 2.0 — Complete Implementation Plan

## Overall architecture after all phases

```text
                    JALNETRA 2.0
                         │
          ┌──────────────┴──────────────┐
          │                             │
   WATER BODY DISCOVERY           MONITORING MAP
          │                             │
   Search city / area             Show water bodies
   Radius / polygon               Show boundaries
   Discover nearby lakes          Show names/labels
          │                             │
          ▼                             ▼
     User selects ───────────────► Add to Database
                                      │
                                      ▼
                              NO SATELLITE DATA YET
                                      │
                              User clicks Analyze
                                      │
                                      ▼
                              Sentinel-2 Search
                                      │
                              Latest suitable scene
                                      │
                                      ▼
                              Targeted AOI download
                                      │
                                      ▼
                              Cloud Masking
                                      │
                              Water Detection
                                      │
                              Spectral Analysis
                                      │
                 ┌────────────────────┼───────────────────┐
                 ▼                    ▼                   ▼
             Turbidity          Chlorophyll          Algal Activity
             Sediment           indicators           indicators
                 │                    │                   │
                 └────────────────────┼───────────────────┘
                                      ▼
                              Temporal Baseline
                                      │
                                      ▼
                              Anomaly Detection
                                      │
                                      ▼
                                Alerts / Reports
                                      │
                                      ▼
                           IoT + AI + Telegram
```

---

# Phase 0 — Current-State Audit & Safety Baseline

**Purpose:** Before changing anything, Antigravity should inspect the existing implementation so we don't accidentally break Phases 1–5.

### Tasks

- Audit current:
  - database models
  - satellite acquisition
  - map rendering
  - water detection
  - processing pipeline
  - filesystem storage
  - frontend state
- Identify every location where:
  - water bodies are seeded
  - satellite scenes are automatically downloaded
  - RGB images are generated
  - processing is automatically triggered
- Document current database/storage usage.
- Verify that raw Sentinel-2 files are never modified.
- Create a safe backup/export mechanism before destructive operations.

### Important

No new analysis functionality here.

### Completion criteria

Antigravity should provide:

```text
Current DB records:
Current satellite scenes:
Current satellite assets:
Current processed files:
Current cache:
Approximate disk usage:
Automatic download triggers:
Automatic processing triggers:
```

---

# Phase 1 — Complete Data Reset & Storage Management

This is the first actual implementation phase.

## Goal

Remove the unwanted preloaded water bodies and satellite data and give you full control over the local database.

### 1. Remove seeded/demo water bodies

The project should start with:

```text
Water bodies: 0
Satellite scenes: 0
Satellite assets: 0
Analysis runs: 0
```

unless you manually import something.

Do **not** delete database tables themselves.

---

## 2. Add Database & Storage Management

Create an admin/system management section.

Example:

```text
SYSTEM STORAGE

Database
Water bodies       0
Scenes             0
Assets             0
Analysis runs      0

Local Storage
Raw satellite      0 MB
Processed          0 MB
Cache              0 MB
Total              0 MB

[ CLEAR SATELLITE DATA ]
[ CLEAR PROCESSED DATA ]
[ CLEAR CACHE ]
[ CLEAR WATER BODIES ]
[ RESET EVERYTHING ]
```

Dangerous operations require confirmation.

---

## 3. Selective cleanup

Implement separate cleanup operations:

```text
clear_water_bodies
clear_scenes
clear_assets
clear_processed
clear_cache
clear_all
```

`clear_all` must:

- delete DB records
- delete associated filesystem data
- remove orphaned files
- preserve application code
- preserve database schema
- preserve `.env`
- preserve migrations

---

## 4. Storage accounting

Add an API such as:

```text
GET /api/v1/system/storage
```

Return:

```json
{
  "database": {},
  "satellite": {},
  "processed": {},
  "cache": {},
  "total_bytes": 0
}
```

### Why this phase matters

Your current large storage is mainly caused by downloading **large Sentinel-2 raster tiles**, especially 10 m bands.

A Sentinel-2 scene isn't a tiny image of the lake. A band can cover an entire satellite tile.

So:

```text
Small lake
      ↓
10 m Sentinel band
      ↓
entire satellite tile
      ↓
large GeoTIFF
      ↓
multiple bands
      ↓
hundreds of MB
```

This is why several scenes can quickly approach ~1 GB.

The new architecture should eventually download/process **only the required AOI whenever technically possible**, instead of treating the entire Sentinel tile as the working image.

---

# Phase 2 — Area-Based Water Body Discovery on Monitoring Map

This is a major change to the existing Phase 2.

Instead of having a giant preloaded catalog, the **Monitoring Map itself becomes the water-body discovery interface.**

## User workflow

User opens:

**MONITORING MAP**

Then:

```text
SEARCH WATER BODIES

Location:
[ Delhi                         ]

Search radius:
[ 1 km ]

[ SEARCH AREA ]
```

Map moves to Delhi.

Then the map displays:

```text
        ○ Lake 1
             ○ Lake 2

      ○ Lake 3

              ○ Lake 4
```

with:

- water-body boundary
- name
- type
- approximate area
- source
- selection status

---

## Search modes

Support:

### A. City/place search

```text
Delhi
Pune
Nagpur
Chhatrapati Sambhajinagar
Mumbai
```

### B. Radius search

```text
Delhi
Radius = 1 km
```

### C. Map-based search

Eventually:

```text
Draw area on map
        ↓
Search water bodies inside polygon
```

---

## Important provider architecture

Do not rely on a single provider.

Create:

```text
WaterBodyDiscoveryProvider
        │
        ├── OSM / Overpass
        ├── Nominatim geocoding
        └── Future providers
```

Nominatim can locate the searched place, while an appropriate geographic data provider should discover **all water bodies in the area**.

---

# Phase 3 — Water Body Selection & Import

The discovery map should **not automatically add everything to the database.**

This is extremely important.

### Workflow

```text
Search Delhi
     ↓
Show nearby water bodies
     ↓
User clicks water body
     ↓
Details panel opens
     ↓
[ ADD TO JALNETRA ]
```

Only after clicking:

**ADD TO JALNETRA**

does it enter the database.

---

## Water-body popup

Example:

```text
SALIM ALI LAKE

Type:
Lake

Source:
OpenStreetMap

Area:
...

Coordinates:
19.xxxx, 75.xxxx

[ ADD TO MONITORING ]
```

After import:

```text
✓ Added to JalNetra

[ VIEW WATER BODY ]
[ ANALYZE SATELLITE ]
```

### Critical rule

Adding a water body **must NOT download satellite imagery.**

That keeps storage under control.

---

# Phase 4 — Correct Targeted Sentinel-2 Acquisition

This phase fixes the current large-box problem.

The current issue is essentially:

```text
Water body
     ↓
entire Sentinel tile
     ↓
huge raster
     ↓
large dashed box
     ↓
resized image
     ↓
blurry lake
```

We want:

```text
Water body
     ↓
small AOI
     ↓
Sentinel scene
     ↓
crop around AOI
     ↓
10 m imagery
     ↓
clear image
```

---

## New acquisition workflow

User selects:

**Salim Ali Lake**

Then:

```text
[ ANALYZE SATELLITE ]
```

JalNetra:

1. Gets water-body geometry.
2. Creates a small AOI around it.
3. Searches Sentinel-2.
4. Selects latest suitable scene.
5. Downloads only required assets/data.
6. Crops/resamples to the AOI.
7. Stores the targeted result.
8. Displays it.

---

## Date selection

Default:

```text
Latest suitable scene
```

with configurable:

```text
Date from
Date to
Maximum cloud %
```

Example:

```text
Latest available
Cloud < 20%
```

---

## Important distinction

Do **not** simply resize a giant Sentinel tile into a small PNG.

The correct sequence is:

```text
Native raster
       ↓
AOI crop
       ↓
proper reprojection/resampling
       ↓
visualization
       ↓
web image
```

This is critical for image quality.

---

# Phase 5 — Manual AOI Selection

This is specifically for the requirement you described for Chilika.

Add:

```text
AOI
```

tab/control.

User can:

- draw rectangle
- draw polygon
- possibly adjust existing AOI

Example:

```text
Chilika Lake
       ↓
User draws small rectangle
       ↓
Old imagery disappears
       ↓
New AOI becomes active
       ↓
Fetch/analyze imagery for NEW AOI
```

---

## Water-body boundary must remain

This is important.

There are two separate geometries:

```text
Water Body Boundary
        ≠
Analysis AOI
```

For example:

```text
     ┌─────────────────────────┐
     │     Water body          │
     │                         │
     │    ┌──────────┐         │
     │    │ Manual   │         │
     │    │ AOI      │         │
     │    └──────────┘         │
     │                         │
     └─────────────────────────┘
```

The orange/official water-body boundary remains visible.

Only the **analysis imagery/AOI** changes.

---

# Phase 6 — Proper Processing Progress System

This should fix the current:

> "Processing..." forever

problem.

Instead of buttons changing to vague processing states, create a proper processing lifecycle.

## Backend states

```text
QUEUED
SEARCHING
SCENE_FOUND
DOWNLOADING
DOWNLOADED
CROPPING
PROCESSING
READY
FAILED
CANCELLED
```

---

## Frontend

Example:

```text
SATELLITE ANALYSIS

✓ Searching Sentinel-2
✓ Scene selected
██████████████░░░░ 75%

Downloading imagery...
```

Then:

```text
████████████████████ 100%

✓ Analysis Ready
```

---

## Each operation should show status

For example:

```text
SEARCH SCENES
[████████████████] 100% ✓

ACQUIRE IMAGE
[██████████░░░░░░] 62%

CLOUD MASK
[████████████████] 100% ✓

WATER DETECTION
[██████████████░░] 82%
```

Failures should say what failed.

---

# Phase 7 — Latest Satellite Data System

This directly addresses the 2024 imagery issue.

The system should **not hard-code or prefer old demo scenes**.

## Scene ranking

Prioritize:

1. latest valid acquisition date
2. low cloud cover
3. spatial overlap
4. processing availability

Example:

```text
Latest scene:
12 Oct 2026
Cloud: 4%
```

rather than automatically displaying:

```text
22 Mar 2024
```

---

## Scene selection UI

Show:

```text
AVAILABLE SENTINEL-2 SCENES

Date          Cloud       Score
--------------------------------
12 Oct 2026   4%          98.4
07 Oct 2026   9%          94.1
02 Oct 2026   2%          91.8
```

User can select another date manually.

---

## Important

"Latest" doesn't mean blindly downloading the newest scene.

If the newest scene has:

```text
90% cloud
```

a slightly older scene with:

```text
3% cloud
```

may be much more useful.

So use:

**latest suitable scene**, not simply latest scene.

---

# Phase 8 — Cloud Masking & Water Detection Refinement

We already have Phase 5 functionality, so this phase should be a refinement rather than rebuilding it.

The pipeline becomes:

```text
Target AOI
    ↓
Sentinel-2 bands
    ↓
SCL cloud/shadow mask
    ↓
valid pixels
    ↓
water detection
    ↓
water mask
```

Make sure the masks are calculated only over the **selected AOI**, not the giant Sentinel tile.

---

# Phase 9 — Spectral Analysis

This is the major next scientific feature from the original JalNetra plan.

The purpose is to move from:

> "Where is water?"

to:

> "What optical characteristics does the water show?"

But we must be careful:

**Satellite spectral indicators are proxies, not laboratory water-quality measurements.**

---

## 9.1 MNDWI — Open Water / Surface Separation

Use:

```text
MNDWI = (Green - SWIR1)
        ----------------
         (Green + SWIR1)
```

Sentinel-2:

```text
Green  = B03
SWIR1  = B11
```

Useful for improving open-water separation.

---

# 9.2 Turbidity Indicator

Create a turbidity-related optical indicator using appropriate visible bands.

Display:

```text
TURBIDITY INDICATOR

Low ─────────────── High
```

Do not call the output:

> "NTU"

unless we later calibrate it against actual field measurements.

Instead:

> **Relative Turbidity Indicator**

---

# 9.3 Suspended Sediment Indicator

Generate a spectral indicator related to suspended material.

Display:

```text
SUSPENDED SEDIMENT
Low → Moderate → High
```

Again:

**relative indicator**, not laboratory concentration.

---

# 9.4 Chlorophyll-Related Indicator

For this, the acquisition system must ensure the necessary Sentinel-2 red-edge band(s), particularly B05 where required by the selected formula.

This means Phase 9 should first verify/acquire the required bands.

Display:

```text
CHLOROPHYLL-RELATED INDICATOR

Low
Medium
High
```

Do not claim:

> "Chlorophyll = 43 mg/L"

without calibration.

---

# 9.5 Algal Activity Indicator

Build an optical proxy based on suitable red/red-edge bands.

Display:

```text
ALGAL ACTIVITY

Normal
Elevated
High
```

The wording should explicitly state:

> Satellite-derived optical proxy.

---

# 9.6 Surface Anomaly Indicator

There are two different meanings of anomaly.

### Spatial anomaly

Within the current image:

```text
Most water pixels
       ↓
find unusual spectral regions
       ↓
highlight them
```

Example:

```text
NORMAL WATER
████████████████

UNUSUAL PATCH
███████▓▓██████
```

This can be part of spectral analysis.

### Temporal anomaly

Compare:

```text
October 2026
       vs
October 2025
       vs
October 2024
```

That belongs in the next phase.

---

# Phase 10 — Spectral Analysis Dashboard

The map should become much more useful.

Add a panel:

```text
SPECTRAL ANALYSIS
────────────────────────

Scene
12 Oct 2026

Cloud-free pixels
94.8%

Water coverage
81.3%

MNDWI
0.42

Turbidity Indicator
0.31

Suspended Sediment
0.28

Chlorophyll Proxy
0.17

Algal Activity
LOW

Surface Anomaly
2.8%
```

And corresponding map layers:

```text
☑ RGB
☑ Water Mask
☐ MNDWI
☐ Turbidity
☐ Suspended Sediment
☐ Chlorophyll Proxy
☐ Algal Activity
☐ Surface Anomaly
```

---

# Phase 11 — Historical Baseline & Temporal Anomaly Detection

Now we start answering the really valuable question:

> **Is this water body changing?**

Store observations for every analyzed scene.

Example:

```text
Salim Ali Lake

2024
Water extent: 72%
Turbidity: 0.21

2025
Water extent: 68%
Turbidity: 0.26

2026
Water extent: 55%
Turbidity: 0.41
```

Then calculate baseline statistics.

---

## Anomaly engine

Example:

```text
Current value
     ↓
historical baseline
     ↓
difference
     ↓
anomaly score
```

Output:

```text
Water extent anomaly: HIGH
Turbidity anomaly: HIGH
Algal activity anomaly: MODERATE
```

This is where the project starts becoming a **monitoring system**, rather than simply a satellite viewer.

---

# Phase 12 — Alerts

Once anomaly detection is reliable, introduce alerts.

Example:

```text
⚠ WATER QUALITY ALERT

Salim Ali Lake

Turbidity indicator increased
42% above historical baseline.

Severity:
HIGH

Detected:
12 Oct 2026
```

Alert types:

- water extent reduction
- sudden water expansion
- turbidity increase
- suspended sediment increase
- chlorophyll-related increase
- algal activity increase
- unusual spectral anomaly
- persistent cloud/data issue

---

# Phase 13 — Reports & Validation

Generate a professional water-body report.

Example:

```text
JALNETRA WATER BODY REPORT

Salim Ali Lake
12 October 2026

────────────────────────

Satellite observation
Cloud cover
Water extent

────────────────────────

WATER QUALITY PROXIES

Turbidity
Suspended sediment
Chlorophyll proxy
Algal activity

────────────────────────

CHANGE DETECTION

30 days
90 days
1 year

────────────────────────

ANOMALIES

⚠ Turbidity elevated
✓ Water extent normal

────────────────────────

DISCLAIMER

Satellite-derived indicators are
remote-sensing proxies and should
be validated against field/laboratory
measurements where required.
```

---

# Phase 14 — IoT Integration

Only after the satellite pipeline is stable.

Your existing IoT concept can then be connected.

```text
IoT Device
   │
   ├── pH
   ├── Temperature
   ├── TDS
   ├── Turbidity
   └── other sensors
        │
        ▼
      JalNetra
        │
        ├──────── Satellite
        │
        ▼
   Combined Analysis
```

Now you can compare:

```text
Satellite turbidity proxy
          +
IoT turbidity sensor
          ↓
cross-validation
```

This is much stronger scientifically.

---

# Phase 15 — AI/ML Layer

**Do not add this now.**

Once enough historical observations exist, ML can become meaningful.

The eventual workflow can be:

```text
Historical satellite images
          ↓
Cloud removal/masking
          ↓
Spectral features
          ↓
Water-quality indicators
          ↓
Historical trends
          ↓
ML model
          ↓
Future anomaly prediction
```

This is much better than simply saying:

> "We use AI to analyze satellite images."

We will have an actual data pipeline for the model.

---

# Phase 16 — Notifications

Finally:

```text
JalNetra
   │
   ├── Dashboard
   ├── Email
   ├── Telegram
   └── Mobile/Web notification
```

Example:

> ⚠️ High turbidity anomaly detected in Salim Ali Lake. Satellite observation indicates a significant increase compared with the historical baseline.

---

# Final Phase Structure for Antigravity

So I recommend giving Antigravity the phases in this exact order:

| Phase | Main implementation |
|---|---|
| **1** | Data reset + database/storage management |
| **2** | Monitoring Map area-wise water-body discovery |
| **3** | Water-body selection/import workflow |
| **4** | Targeted Sentinel-2 AOI acquisition |
| **5** | Manual AOI selection + precise imagery |
| **6** | Processing progress/status system |
| **7** | Latest suitable Sentinel-2 scene selection |
| **8** | AOI-based cloud masking + water detection refinement |
| **9** | Spectral analysis indicators |
| **10** | Spectral analysis dashboard/map layers |
| **11** | Historical baseline + temporal anomalies |
| **12** | Alerts |
| **13** | Reports + validation |
| **14** | IoT integration |
| **15** | AI/ML layer |
| **16** | Telegram/notification system |
| **17** | Final hardening/demo optimization |

### One important change from the old roadmap

Your old Phase 6 was spectral analysis, and I recommend **keeping that**. The new data-management and discovery work should be treated as improvements to Phases 1–5 rather than pushing spectral analysis further away.

So the project's core progression remains:

**Discover → Select → Acquire → Crop → Process → Analyze → Compare → Alert → Validate → IoT → AI.**

And the most important architectural rule from now onward is:

> **Never download or process satellite imagery merely because a water body exists in the database. Satellite data is fetched only when the user explicitly requests analysis, and it is targeted to the selected water body/AOI.**

That will solve a large part of both your **~1 GB storage problem** and the **huge/blurry imagery problem** at the architectural level, rather than repeatedly patching the frontend.