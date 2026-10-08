# StreetSmart: Detailed System Design, Part 1 (Design D1)

**Team Members:** Advait Vagerwal, Sahil Thakare, Raihan Rafeek  
**Course:** CS 5001 - Computer Science Senior Design  
**Advisor:** Eric Jamison  
**Assignment:** Assignment 6 — Detailed System Design, Part 1 (Design D1)  
**Date:** October 8, 2026  
**Document Version:** 1.0  

---

# 1. Header, Scope, and Conventions

## 1.1 Project Title

**StreetSmart: Automated Public Infrastructure Damage Detection and Geospatial Reporting System**

## 1.2 Goal Statement

StreetSmart is an automated public infrastructure inspection system that analyzes vehicle-mounted camera footage and synchronized GPS data to detect, geotag, and classify roadway damage such as potholes. The system provides municipal personnel and downstream city systems with a centralized geospatial database, interactive visualization dashboard, and standardized API integration to accelerate road maintenance and improve public transit safety.

## 1.3 Scope

This document details three D0 components: the **PostgreSQL Database** (including schema, spatial indexing, and evidence-image storage), the **Ingestion Pipeline** (focusing on its confidence aggregation algorithm, spatial pothole deduplication matching algorithm, and privacy redaction storage flow), and the **Backend API** (specifying REST endpoints, request/response contracts, and error handling); while **Model Training**, **Trained Model Storage**, **Model Inference**, and the **Current Infrastructure Map** are deferred to D2.

## 1.4 Diagram Conventions

The visual conventions for the D1 Entity-Relationship Diagram (Figure 1) are defined as follows:

* **Entity Boxes:** Rectangular boxes represent database entities (PostgreSQL tables). Attributes are listed inside the box with their exact PostgreSQL/PostGIS data types.
* **Key Designations:** Primary key attributes are annotated with `PK` and uniquely identify each record in the entity. Foreign key attributes are annotated with `FK` and enforce referential integrity by referencing the primary key of a parent entity.
* **Connector Lines:** Solid lines represent foreign-key relationships and data associations between entities.
* **Cardinality Notation:** Cardinality is drawn on both ends of every connector line using standard Crow's Foot notation:
  * Exactly One (`||`): Indicates a mandatory singular parent record.
  * Zero, One, or Many (`o{`): Indicates an optional child relationship where a parent record may be associated with zero or multiple child records.
  * For example, `POTHOLE ||--o{ DETECTION` indicates that exactly one canonical `POTHOLE` record groups zero or more individual `DETECTION` records, and every `DETECTION` record references exactly one `POTHOLE`.
* **Geospatial Reference:** Geographic point coordinates use longitude and latitude defined in the WGS84 spatial reference system (`EPSG:4326`).
* **Binary Artifact Decoupling:** Large binary images (camera frame crops) are stored externally in Supabase Object Storage; PostgreSQL stores only relative URI paths to maintain low storage footprint and high query throughput.

---

# 2. Data Model, the D1 Diagram

## 2.1 Entity-Relationship Diagram

Figure 1 illustrates the core data model for StreetSmart. Physical roadway potholes are strictly decoupled from individual point detections. As an inspection vehicle drives over a road defect, the camera captures multiple consecutive frames; each observation is recorded as a `DETECTION`, while the canonical `POTHOLE` record aggregates the detection count, recalculates overall confidence, and maintains the estimated geographic location.

```mermaid
erDiagram
    VIDEO_RUN ||--o{ DETECTION : produces
    POTHOLE ||--o{ DETECTION : groups
    DETECTION ||--o{ EVIDENCE_IMAGE : has

    VIDEO_RUN {
        uuid id PK
        text source_video_name
        timestamptz started_at
        timestamptz completed_at
        text processing_status
    }

    POTHOLE {
        uuid id PK
        geometry location
        float aggregated_confidence
        integer observation_count
        text status
        timestamptz first_detected_at
        timestamptz last_detected_at
    }

    DETECTION {
        uuid id PK
        uuid video_run_id FK
        uuid pothole_id FK
        float model_confidence
        timestamptz detected_at
        integer frame_index
        geometry observed_location
    }

    EVIDENCE_IMAGE {
        uuid id PK
        uuid detection_id FK
        text storage_path
        timestamptz created_at
    }
```

*Figure 1: StreetSmart D1 Entity-Relationship Diagram.*

## 2.2 Entity Descriptions

| Entity | Purpose & Behavioral Attributes |
| :--- | :--- |
| `VIDEO_RUN` | Represents a single video processing batch ingested by the system. Tracks the source video container name (`source_video_name`), execution start timestamp (`started_at`), completion timestamp (`completed_at`), and run state (`processing_status`, e.g., `'PROCESSING'`, `'COMPLETED'`, `'FAILED'`). |
| `POTHOLE` | Represents a unique, physical roadway hazard. Maintains its centroid geographic coordinate (`location` as `GEOMETRY(Point, 4326)`), running aggregate confidence score (`aggregated_confidence`), total observation tally (`observation_count`), municipal workflow state (`status`, e.g., `'UNRESOLVED'`, `'VERIFIED'`, `'REPAIRED'`), and temporal bounds (`first_detected_at`, `last_detected_at`). |
| `DETECTION` | Represents a single observation of roadway damage identified in a specific video keyframe. Contains the foreign key to the originating run (`video_run_id`), foreign key to the grouped pothole (`pothole_id`), raw neural network inference confidence (`model_confidence`), capture timestamp (`detected_at`), sequential frame offset (`frame_index`), and interpolated GPS coordinate (`observed_location`). |
| `EVIDENCE_IMAGE` | Stores metadata references for redacted photographic evidence supporting a detection. Contains the foreign key to the detection (`detection_id`), object storage relative key (`storage_path`), and creation timestamp (`created_at`). |

## 2.3 Structural Decisions

| Structural Decision | Decision Type | Rationale & Justification | Requirement Traceability |
| :--- | :--- | :--- | :--- |
| **Separate `POTHOLE` and `DETECTION` Entities** | Entity vs. Attribute | A physical pothole appears in multiple consecutive frames of a single run and across multiple separate patrol dates. Collapsing detections into attributes on a pothole would lose historical sensor telemetry and prevent incremental confidence updates. Conversely, treating each detection as an independent pothole would produce hundreds of duplicate hazard pins for a single street defect. | **US-01, US-02, US-03, AC-01.1** |
| **Separate `VIDEO_RUN` Entity** | Entity vs. Attribute | One video run produces hundreds of detections. Storing video container name, processing status, and run timestamps directly on each detection row would duplicate strings across thousands of rows. A dedicated `VIDEO_RUN` entity provides run-level lifecycle auditing, batch failure isolation, and performance monitoring. | **US-01, AC-01.1, AC-01.2** |
| **Separate `EVIDENCE_IMAGE` Entity** | Entity vs. Attribute | Normalizes image storage metadata. Not every detection produces an evidence crop (e.g., distant low-resolution detections), and future extensions may store multiple crops (e.g., wide overview and zoomed-in texture). Decoupling image paths keeps detection rows narrow and simplifies independent redaction pipelines. | **US-04, AC-01.1** |
| **`VIDEO_RUN` to `DETECTION` is 1-to-Many (`1:N`)** | Cardinality (`1:N` vs. `M:N`) | A single video processing run produces zero or many point detections, but every detected video frame originates from exactly one physical video file and ingest run. A many-to-many relationship is structurally invalid and unnecessary. | **US-01, AC-01.1** |
| **`POTHOLE` to `DETECTION` is 1-to-Many (`1:N`)** | Cardinality (`1:N` vs. `M:N`) | A physical pothole groups one or more observations over time ($n \ge 1$), but each individual localized frame detection represents a single point in space and time that belongs to exactly one physical pothole entity. | **US-02, US-03, AC-01.1** |
| **`DETECTION` to `EVIDENCE_IMAGE` is 1-to-Many (`1:N`)** | Cardinality (`1:N` vs. `M:N`) | A detection has zero or more associated image crops (typically one cropped bounding box), and each image file belongs to exactly one detection event. | **US-04, AC-01.1** |
| **Relational Model (PostgreSQL/PostGIS) vs. Simpler Store** | Database Architecture | StreetSmart selects a relational model over NoSQL document stores or key-value stores. Relational tables enforce strict referential integrity across runs, detections, and evidence links. Furthermore, PostGIS provides native Open Geospatial Consortium (OGC) spatial operations (`ST_DWithin`, `ST_MakeEnvelope`) and R-tree spatial indexing (`GIST`), which are essential for $O(\log N)$ radius matching and RFC 7946 GeoJSON export. Simpler key-value or document stores lack native spatial indexing and require custom application-level joins and spatial filtering. | **US-01, US-02, US-05, AC-02.1** |

## 2.4 Indexing Decisions

To guarantee low-latency spatial queries and prevent performance degradation as inspection datasets grow, the following indexes are defined:

| Table | Indexed Field | Index Type | Rationale & Justification | Requirement Traceability |
| :--- | :--- | :--- | :--- | :--- |
| `POTHOLE` | `location` | `GIST` (Generalized Search Tree) | PostGIS spatial R-tree index. Enables sub-millisecond $O(\log N)$ bounding-box filtering (`ST_MakeEnvelope`) for map viewport rendering and radial distance searches (`ST_DWithin`) during pothole deduplication, avoiding a full table scan of tens of thousands of records. | **US-01, US-05, AC-02.1** |
| `DETECTION` | `pothole_id` | `B-Tree` | Foreign key index. Accelerates $O(\log n)$ retrieval and aggregation of all historical observations belonging to a given pothole when re-evaluating aggregate confidence or displaying inspection history. | **US-02, AC-01.1** |
| `DETECTION` | `video_run_id` | `B-Tree` | Foreign key index. Accelerates run-level batch queries, status auditing, and transactional cleanup of failed video processing runs. | **US-01, AC-01.2** |
| `POTHOLE` | `aggregated_confidence` | `B-Tree` | Scalar index. Accelerates filtering queries requesting high-confidence roadway defects ($C \ge 0.70$) without scanning unconfirmed low-confidence candidates. | **US-02, AC-01.1, AC-02.1** |
| `POTHOLE` | `status` | `B-Tree` | Low-cardinality scalar index. Enables rapid filtering by municipal workflow status (`'UNRESOLVED'`, `'VERIFIED'`, `'REPAIRED'`) for maintenance work-order generation. | **US-01, US-03** |

## 2.5 Video and Evidence-Image Storage Lifecycle

1. **Persistent Source Footage:** Raw vehicle dashcam video files remain on local persistent disk or staging volumes.
2. **Incremental Frame Extraction:** The Go inference service decodes video streams incrementally into memory buffers (frame-by-frame), strictly avoiding loading entire multi-gigabyte video files into RAM.
3. **Inference Execution:** Frames are preprocessed (scaled to $3 \times 640 \times 640$) and evaluated via ONNX Runtime.
4. **Evidence Cropping & Redaction:** When a pothole is detected with confidence $\ge 0.70$, the pipeline extracts a cropped region of interest around the bounding box. The bounding box is rendered onto the image crop, and an automated privacy filter blurs any detected vehicle license plates or pedestrian faces (**US-04**).
5. **Object Storage Upload:** The redacted JPEG image is uploaded to Supabase Storage via its REST API under path `/evidence/{run_id}/{detection_id}.jpg`.
6. **Database Persistence:** PostgreSQL commits the `DETECTION` row and creates an associated `EVIDENCE_IMAGE` row recording the storage path.
7. **Failure Isolation:** If an image upload fails (e.g., network timeout), the transaction logs an error and rolls back the evidence reference, preventing broken image links from entering the database.

---

# 3. Core Algorithms

## 3.1 Algorithm A: Weighted Pothole Confidence Aggregation

### 1. Purpose and Problem Solved
Single-frame computer vision detections suffer from transient uncertainty caused by motion blur, camera vibration, sun glare, and asphalt shadow patterns. Storing isolated raw detections creates duplicate hazard alerts and false positives. Algorithm A aggregates multiple consecutive observations of the same pothole into a single robust, monotonically calibrated confidence metric, balancing raw visual model certainty with physical recurrence frequency.

### 2. Inputs and Outputs with Exact Types

**Inputs:**
* `current_avg_confidence`: `float64` — Average model confidence of existing accepted detections, range $[0.0, 1.0]$.
* `current_observation_count`: `int32` — Number of previously accepted observations ($n \ge 0$).
* `new_model_confidence`: `float64` — Model confidence of the newly matched detection, range $[0.0, 1.0]$.
* `repeat_weight`: `float64` — Weight assigned to repeated detections ($w \in [0.0, 1.0]$, system default $w = 0.30$).

**Outputs:**
* `updated_aggregated_confidence`: `float64` — Recalculated composite confidence score, range $[0.0, 1.0]$.
* `updated_observation_count`: `int32` — Incremented count of observations ($n + 1$).
* `updated_avg_confidence`: `float64` — Updated mean model confidence across all accepted detections.

**Mathematical Formulation:**
The aggregate confidence score $C_{\text{final}}$ is computed via a weighted linear combination of the running mean model confidence $\bar{C}_{\text{model}}$ and a non-linear repeat score $C_{\text{repeat}}$:

$$C_{\text{final}} = (1 - w) \cdot \bar{C}_{\text{model}} + w \cdot C_{\text{repeat}}$$

where the running average model confidence updates incrementally:
$$\bar{C}_{\text{model}} = \frac{n_{\text{prev}} \cdot \bar{C}_{\text{prev}} + C_{\text{new}}}{n_{\text{prev}} + 1}$$

and the repeat score implements diminishing marginal returns normalized to $[0, 1)$:
$$C_{\text{repeat}} = \frac{n}{n + 1}$$
where $n = n_{\text{prev}} + 1$ is the total observation count.

*Example:* A pothole is detected across 3 video frames with model confidences $0.90$, $0.92$, and $0.88$ ($\bar{C}_{\text{model}} = 0.90$, $n = 3$, $w = 0.30$).
$$C_{\text{repeat}} = \frac{3}{3 + 1} = 0.75$$
$$C_{\text{final}} = (0.70)(0.90) + (0.30)(0.75) = 0.630 + 0.225 = 0.855$$
The visual confidence provides the baseline certainty, while multi-frame repetition reinforces the score.

### 3. Expected Complexity at Realistic Data Size and 100x Scale
* **Realistic Data Size:** In a typical 60-minute municipal inspection run (approx. 10–20 miles), a dashcam captures footage at 30 fps (~108,000 frames). A single pothole remains in the camera's field of view across 3 to 15 keyframes ($n \approx 3\text{--}15$).
* **Time Complexity:** Because the algorithm maintains a running sum and count, updating $\bar{C}_{\text{model}}$, $C_{\text{repeat}}$, and $C_{\text{final}}$ requires only 5 basic floating-point arithmetic operations, executing in $O(1)$ constant time ($< 0.05\ \mu\text{s}$). If calculated from scratch across all $n$ historical detections, time complexity is $O(n)$, executing in $\approx 0.1\ \mu\text{s}$ for $n = 10$.
* **At 100x Data Size:** If a permanent pothole is observed across 100 vehicle passes over a year ($n = 1,000$), incremental updates remain strictly $O(1)$ ($< 0.05\ \mu\text{s}$). Recomputing from scratch would take $O(100n) = O(1,000)$, requiring $< 10\ \mu\text{s}$.
* **Does the Difference Matter?** No. In both realistic ($n = 10$) and 100x ($n = 1,000$) scenarios, the calculation takes microseconds and is completely negligible compared to network I/O (~5 ms) and model inference (~15 ms).
* **Space Complexity:** $O(1)$ auxiliary memory.

### 4. Why This Approach Rather than Alternatives
* **Alternative 1: Simple Arithmetic Mean ($\bar{C} = \frac{1}{n} \sum C_i$):** Passed over because a single false-positive detection with high confidence (e.g., $0.91$ on an oil stain) would receive the exact same score as a genuine pothole verified across 10 frames with $0.91$ confidence. The simple average fails to reward physical confirmation over time.
* **Alternative 2: Bayesian Probability Updating:** Passed over because Bayesian updating assumes independent evidence events. Consecutive video frames recorded 33 ms apart share identical lighting, viewing angles, and road geometry; assuming conditional independence causes the posterior probability to artificially saturate to $0.9999$ after only 3–4 frames.
* **Alternative 3: Maximum Confidence ($\max(C_i)$):** Passed over because it is highly vulnerable to transient neural network misclassifications and sensor noise spikes.
* **Why Chosen Option Won:** The weighted formulation explicitly balances visual certainty with observation count, provides intuitive parameter tuning via $w$, bounds output strictly to $[0.0, 1.0]$, and enforces diminishing returns via $\frac{n}{n+1}$.

### 5. Edge Cases
* **First Observation ($n=0$):** Handled cleanly with $n=1$, $\bar{C}_{\text{model}} = C_{\text{new}}$, and $C_{\text{repeat}} = \frac{1}{2} = 0.50$. For a $0.90$ detection, $C_{\text{final}} = 0.7(0.9) + 0.3(0.5) = 0.78 \ge 0.70$. Directly satisfies **AC-01.1**.
* **Out-of-Bounds Model Confidence:** Inputs where $C_{\text{new}} < 0.0$ or $C_{\text{new}} > 1.0$ are rejected by the Ingestion Pipeline validation layer with an error log, preventing corrupt numbers from entering calculations (Interfaces **I6**, **I7**).
* **Duplicate Frame Reprocessing:** If a frame with the same `(video_run_id, frame_index)` is retransmitted, the ingestion layer detects the duplicate key and skips the confidence calculation, avoiding artificial score inflation (**AC-01.1**).
* **Observation Saturation ($n \to \infty$):** As $n$ grows large, $\frac{n}{n+1} \to 1.0$, preventing numeric overflow and capping repeat contribution to $w$.
* **Decaying Confidence on Subsequent Passes:** If subsequent detections have lower confidence (e.g., a closer camera view reveals the defect is minor), $\bar{C}_{\text{model}}$ drops, appropriately reducing $C_{\text{final}}$ and preventing false-positive escalation (**US-02**).

---

## 3.2 Algorithm B: Spatial Matching of Repeated Detections to Pothole Records

### 1. Purpose and Problem Solved
As an inspection vehicle drives along a street at 25–35 mph, a pothole remains in the camera's field of view across multiple frames over 0.5–2 seconds. Furthermore, municipal vehicles traverse the same street on subsequent patrol days. If every detection created a new database record, the system would produce hundreds of duplicate records for the same physical pothole. Algorithm B determines whether an incoming detection belongs to an existing pothole record or constitutes a newly discovered hazard.

### 2. Inputs and Outputs with Exact Types

**Inputs:**
* `observed_location`: `geometry(Point, 4326)` — Longitude and latitude of the incoming detection (`lat: float64` $\in [-90.0, 90.0]$, `lon: float64` $\in [-180.0, 180.0]$).
* `matching_radius_meters`: `float64` — Search radius in meters ($R = 5.0\text{m}$, matching the GPS tolerance in AC-01.1).
* `video_run_id`: `UUID` — Identifier of the active video run.
* `detected_at`: `timestamptz` — Capture timestamp of the frame.

**Outputs:**
* `match_decision`: `MatchResult` struct:
  * `action`: `string` — Enum: `'MERGE_EXISTING'`, `'CREATE_NEW'`, or `'FLAG_AMBIGUOUS'`.
  * `target_pothole_id`: `UUID` — Identifier of the matched or newly created pothole.
  * `distance_meters`: `float64` — Geodesic distance to matched centroid (meters).

**Algorithmic Steps:**
1. **Spatial Candidate Query:** Query PostGIS using the spatial index to find all existing potholes within radius $R = 5.0\text{m}$ using geodetic distance:
   ```sql
   SELECT id, location, aggregated_confidence, observation_count,
          ST_Distance(location::geography, ST_SetSRID(ST_MakePoint($lon, $lat), 4326)::geography) AS dist_meters
   FROM POTHOLE
   WHERE ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint($lon, $lat), 4326)::geography, 5.0)
   ORDER BY dist_meters ASC;
   ```
2. **Case A (Zero Candidates, $k = 0$):** No existing potholes exist within 5 meters. Create a new `POTHOLE` record with a generated UUID, set `location = observed_location`, set `observation_count = 1`, and return `'CREATE_NEW'`.
3. **Case B (Single Candidate, $k = 1$):** Exactly one existing pothole is within 5 meters. Match the detection to this pothole, associate the foreign key, update the pothole centroid location via a running weighted average, update temporal bounds (`last_detected_at`), and return `'MERGE_EXISTING'`.
4. **Case C (Multiple Candidates, $k > 1$):** Multiple potholes exist within 5 meters (e.g., a pothole cluster).
   * Evaluate the distance ratio between the nearest candidate ($d_1$) and the second-nearest candidate ($d_2$).
   * If $d_1 < 2.0\text{m}$ and $d_2 - d_1 \ge 1.5\text{m}$, match unambiguously to candidate 1 (`'MERGE_EXISTING'`).
   * If candidate distances are closely tied ($|d_2 - d_1| < 1.0\text{m}$), flag the match as ambiguous (`'FLAG_AMBIGUOUS'`), associate the detection with the nearest record, and log an audit warning to prevent corrupting cluster records.

### 3. Expected Complexity at Realistic Data Size and 100x Scale
* **Realistic Data Size:** A medium-sized city like Cincinnati maintains approximately 10,000 to 25,000 active roadway defects across its road network at any given time ($N = 25,000$). In a localized 5-meter neighborhood, roadway density yields $k = 0$ to $2$ existing potholes.
* **Time Complexity:**
  * *Without Index (Naive Scan):* Calculating Haversine distance across all $N$ potholes requires $O(N)$ comparisons. For $N = 25,000$, a linear scan requires 25,000 trigonometric distance evaluations per detection (~8 ms), which would consume significant compute during batch ingestion.
  * *With PostGIS GiST Index:* The spatial R-tree index prunes bounding boxes hierarchically, executing candidates in $O(\log N)$ time, followed by exact geodetic distance evaluation on the candidate set of size $k$ ($O(k)$). For $N = 25,000$, $O(\log_2(25,000) + k) \approx 15 + 2 = 17$ checks, executing in $< 0.8\ \text{ms}$.
* **At 100x Data Size:** At $N = 2,500,000$ potholes (representing a statewide or multi-year historical dataset):
  * The GiST tree depth increases by only $\log_2(100) \approx 6.6$ levels ($O(\log(100N)) \approx 22$ checks), executing in $< 1.5\ \text{ms}$.
  * In contrast, an unindexed linear scan would require 2,500,000 distance evaluations (~800 ms per detection), completely crashing the ingestion pipeline.
* **Does the Difference Matter?** Yes! With the GiST spatial index, the 100x scale increase introduces virtually zero latency penalty, easily satisfying the 20-minute video ingestion budget (**AC-01.1**). Without the spatial index, the 100x scale would break the product.
* **Space Complexity:** $O(N)$ memory for the spatial GiST index in PostgreSQL; $O(k)$ working memory for the candidate array in the Go service.

### 4. Why This Approach Rather than Alternatives
* **Alternative 1: Visual Feature Matching / Re-Identification (Re-ID Embeddings):** Passed over because asphalt road textures lack distinctive visual landmarks, lighting conditions shift between vehicle passes, and running a secondary deep neural network for feature extraction requires $>50\ \text{ms}$ per candidate, violating the batch processing timing budget of 1,200s for a 60-minute video (**AC-01.1**).
* **Alternative 2: Fixed Spatial Tile Binning (Geohash or S2 Cells):** Passed over due to the "boundary problem": a pothole positioned 10 cm from a cell boundary will fail to match a detection 20 cm away in the adjacent cell unless complex multi-cell perimeter queries are executed.
* **Why Chosen Option Won:** PostGIS geodetic radius matching (`ST_DWithin`) operates smoothly across arbitrary geographic boundaries, natively accounts for the ellipsoidal curvature of the Earth, leverages hardware-accelerated R-trees, and directly aligns with the $\pm 5\text{m}$ GPS accuracy specification in **AC-01.1**.

### 5. Edge Cases
* **Missing or Unresolved GPS Fix:** If `observed_location` has null coordinates or $(0.0, 0.0)$, the spatial query cannot execute. The Ingestion Pipeline intercepts the detection, flags the record with `status: LOCATION_UNRESOLVED`, halts matching, and logs an HTTP 422 error within 3.0 seconds, directly fulfilling **AC-01.2** and Interfaces **I5**, **I7**.
* **Zero Candidates ($k = 0$):** PostGIS returns an empty set. The system smoothly instantiates a new `POTHOLE` record with a new UUID and sets initial temporal bounds (**US-01, AC-01.1**).
* **Equidistant Ambiguous Candidates ($k > 1$, $|d_1 - d_2| < 1.0\text{m}$):** Handled via the `'FLAG_AMBIGUOUS'` condition, preventing arbitrary record thrashing and preserving data integrity (**US-02**).
* **Rapid Consecutive Frames in Same Run ($dt < 0.2\text{s}$):** Checked via `(pothole_id, video_run_id)`. Detections from adjacent frames merge into the active pothole and update its centroid without double-counting observation tallies (**AC-01.1**).
* **GPS Multi-Path Reflection Jump:** If a vehicle GPS receiver experiences a momentary multipath reflection causing coordinates to jump $> 5.0\text{m}$, the detection is treated as an isolated candidate rather than erroneously shifting the existing pothole centroid (**US-02**).

---

# 4. Build-versus-Reuse Decisions

Table 1 details the build-versus-reuse decisions for every significant piece of the detailed components, checking maturity, licensing, performance, and fit for every candidate library or service.

| Component / Subsystem | Build or Reuse | Library or Service | License | Justification (Maturity, Licensing, Performance, and Fit) |
| :--- | :--- | :--- | :--- | :--- |
| **Relational Database Engine** | Reuse | PostgreSQL 16 | PostgreSQL License | Highly mature ACID relational database with robust connection pooling and enterprise reliability; permissive license permits unrestricted municipal deployment. |
| **Geospatial Engine** | Reuse | PostGIS 3.4 | GPL-2.0-or-later | Industry-standard spatial extension providing optimized R-tree GiST indexing and OGC-compliant geodetic operators for sub-millisecond radius matching. |
| **Database & Blob Storage Hosting** | Reuse | Supabase Cloud | Apache-2.0 / Hosted Terms | Fully managed cloud PostgreSQL, PostGIS, and S3-compatible blob storage, eliminating complex database DevOps and infrastructure management for the prototype. |
| **Deep Learning Inference Engine** | Reuse | Microsoft ONNX Runtime (Go binding) | MIT License | High-performance, mature cross-platform inference engine supporting hardware execution providers (CUDA/CPU) with minimal runtime overhead. |
| **Video Decoding & Frame Extraction** | Reuse | GoCV / OpenCV 4.x (via Go bindings) | Apache-2.0 | Battle-tested, mature C++/Go library providing hardware-accelerated video demuxing, frame extraction, and image manipulation. |
| **REST Web Framework & HTTP Router** | Reuse | Gin Web Framework (`gin-gonic/gin`) | MIT License | Mature, high-performance HTTP web framework in Go with low memory footprint (<30 MB RAM) and fast radix-tree routing for REST APIs. |
| **Geospatial & GeoJSON Serialization** | Reuse | `paulmach/orb` / `go-geom` | MIT License | Mature Go geospatial library providing fast 2D geometry manipulation, WKB parsing, and standard RFC 7946 GeoJSON serialization. |
| **Automated PII Privacy Redaction** | Reuse | Haar Cascade / Lightweight YOLOv8-Nano PII Model | MIT License | Fast, mature pre-persistence face and license plate blurring filter preventing PII storage in compliance with municipal mandates (**US-04**). |
| **Object Storage Client SDK** | Reuse | `supabase-community/storage-go` | MIT License | Production-ready HTTP client SDK for multipart file uploads, signed URL generation, and error handling for image persistence. |
| **Date/Time & Coordinate Validation** | Reuse | Go Standard Library (`time`, `math`) | BSD-3-Clause | Battle-tested standard library functions for RFC 3339 timestamp parsing and bounding-box validation, avoiding hand-rolled date routines. |
| **Ingestion Orchestration Pipeline** | Build | Custom Go Service (`internal/ingestion`) | Team Project License | Implements StreetSmart's end-to-end ingestion pipeline, coordinating video frame reading, GPS correlation, and DB writes. |
| **Confidence Aggregation Engine** | Build | Custom Go Module (`internal/scoring`) | Team Project License | Implements StreetSmart's weighted diminishing-returns confidence algorithm balancing model certainty and repeat detections. |
| **Spatial Pothole Matching Module** | Build | Custom Go Module with PostGIS (`internal/matcher`) | Team Project License | Implements StreetSmart's 5-meter radius spatial deduplication and ambiguous cluster resolution logic using PostGIS. |

*Table 1: Build-versus-Reuse Decisions for Detailed Components.*

---

# 5. API Contract

The detailed components (Backend API and Ingestion Pipeline) expose four primary RESTful endpoints.

## 5.1 Endpoint Specifications

### 1. `POST /api/v1/runs`
Initializes a new video processing run batch in the system.

* **Inputs:**
  * `source_video_name`: `string` (Required, valid length 1–255 characters, filename format, e.g., `"route04_20261002.mp4"`).
  * `started_at`: `string` (Required, ISO 8601 / RFC 3339 UTC timestamp, e.g., `"2026-10-02T14:00:00Z"`).
  * `device_id`: `string` (Optional, alphanumeric string 1–64 characters, e.g., `"dashcam-unit-04"`).
* **Outputs:**
  * HTTP `201 Created`:
    ```json
    {
      "run_id": "e32a71db-a9bf-4dc5-ae3d-57e16ed23c11",
      "status": "QUEUED",
      "started_at": "2026-10-02T14:00:00Z"
    }
    ```
    *Units:* `run_id` is a UUIDv4 string; `status` is an enum string (`'QUEUED'`, `'PROCESSING'`); `started_at` is an RFC 3339 UTC timestamp.
* **Error Responses:**
  * HTTP `400 Bad Request`: Returned when required fields are missing or `started_at` is not a valid RFC 3339 timestamp.
  * HTTP `409 Conflict`: Returned when `source_video_name` has already been submitted for processing.
  * HTTP `500 Internal Server Error`: Returned when an unhandled database transaction exception occurs.
  * HTTP `503 Service Unavailable`: Returned when PostgreSQL database connection pool is exhausted.

---

### 2. `POST /api/v1/detections`
Ingests an individual damage detection event generated by computer vision inference, correlates it with an existing pothole or creates a new one, and updates aggregate metrics.

* **Inputs:**
  * `run_id`: `string` (Required, valid UUIDv4 string referencing active `VIDEO_RUN`).
  * `frame_index`: `integer` (Required, integer $\ge 0$, sequential frame number in video).
  * `detected_at`: `string` (Required, RFC 3339 UTC timestamp).
  * `model_confidence`: `number` (Required, float in range $[0.0, 1.0]$).
  * `damage_type`: `string` (Required, enum: `"pothole"`).
  * `latitude`: `number` (Required, float in range $[-90.0, 90.0]$ degrees WGS84).
  * `longitude`: `number` (Required, float in range $[-180.0, 180.0]$ degrees WGS84).
  * `image_path`: `string` (Optional, relative storage URI string, max 500 characters).
* **Outputs:**
  * HTTP `201 Created`:
    ```json
    {
      "detection_id": "4a7f9218-c2b3-4f9e-a81d-6120531e21b0",
      "pothole_id": "f71f1e42-9b8d-47c8-8ed8-3f35f023be18",
      "match_action": "MERGED",
      "aggregated_confidence": 0.855,
      "observation_count": 3,
      "distance_to_centroid_meters": 1.42
    }
    ```
    *Units:* `detection_id` and `pothole_id` are UUIDv4 strings; `match_action` is enum (`'CREATED'`, `'MERGED'`); `aggregated_confidence` is dimensionless float $[0.0, 1.0]$; `observation_count` is integer count; `distance_to_centroid_meters` is float distance in meters.
* **Error Responses:**
  * HTTP `400 Bad Request`: Returned when JSON payload is malformed or numerical values fall outside valid bounds.
  * HTTP `404 Not Found`: Returned when `run_id` does not match any existing `VIDEO_RUN` record.
  * HTTP `409 Conflict`: Returned when a detection for `(run_id, frame_index)` has already been recorded.
  * HTTP `422 Unprocessable Entity`: Returned when GPS coordinates are missing, corrupted, or unresolved (`status: LOCATION_UNRESOLVED`), satisfying **AC-01.2**.
  * HTTP `500 Internal Server Error`: Returned when database query or PostGIS spatial evaluation fails.
  * HTTP `503 Service Unavailable`: Returned when database or storage backend is unreachable.

---

### 3. `GET /api/v1/potholes`
Retrieves roadway potholes within a specified geographic bounding box, serialized as an RFC 7946 GeoJSON FeatureCollection for map rendering or municipal GIS export.

* **Inputs (Query Parameters):**
  * `bbox`: `string` (Required, comma-separated bounding box `min_lon,min_lat,max_lon,max_lat` in decimal degrees EPSG:4326; valid ranges: `min_lon, max_lon` in $[-180.0, 180.0]$, `min_lat, max_lat` in $[-90.0, 90.0]$ with `min_lon <= max_lon` and `min_lat <= max_lat`).
  * `min_confidence`: `number` (Optional, float in range $[0.0, 1.0]$, default `0.70`).
  * `status`: `string` (Optional, enum: `"UNRESOLVED"`, `"VERIFIED"`, `"REPAIRED"`, `"ALL"`, default `"ALL"`).
  * `limit`: `integer` (Optional, integer in range $[1, 500]$, default `100`, max 500 per **AC-02.1**).
* **Outputs:**
  * HTTP `200 OK`: Standardized RFC 7946 GeoJSON FeatureCollection:
    ```json
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "id": "f71f1e42-9b8d-47c8-8ed8-3f35f023be18",
          "geometry": {
            "type": "Point",
            "coordinates": [-84.516028, 39.132145]
          },
          "properties": {
            "aggregated_confidence": 0.855,
            "observation_count": 3,
            "status": "UNRESOLVED",
            "first_detected_at": "2026-10-02T14:32:08Z",
            "last_detected_at": "2026-10-02T14:32:10Z",
            "evidence_image_urls": [
              "https://storage.supabase.co/v1/object/public/evidence/route04/det01.jpg"
            ]
          }
        }
      ],
      "total_features": 1
    }
    ```
    *Units:* `coordinates` are `[longitude, latitude]` in decimal degrees; `aggregated_confidence` is float $[0.0, 1.0]$; `observation_count` is integer; timestamps are RFC 3339 UTC.
* **Error Responses:**
  * HTTP `400 Bad Request`: Returned when `bbox` is missing, malformed, or coordinates violate WGS84 ranges, returning RFC 7807 problem details within 1.0s (**AC-02.2**).
  * HTTP `401 Unauthorized`: Returned when authentication token or API key is invalid or absent.
  * HTTP `503 Service Unavailable`: Returned when database query times out or PostgreSQL is unreachable.

---

### 4. `GET /api/v1/potholes/{id}`
Retrieves detailed information and historical detection evidence for a specific pothole record.

* **Inputs:**
  * `id`: `string` (Required, path parameter, valid UUIDv4 string format).
* **Outputs:**
  * HTTP `200 OK`:
    ```json
    {
      "id": "f71f1e42-9b8d-47c8-8ed8-3f35f023be18",
      "location": {
        "latitude": 39.132145,
        "longitude": -84.516028
      },
      "aggregated_confidence": 0.855,
      "observation_count": 3,
      "status": "UNRESOLVED",
      "first_detected_at": "2026-10-02T14:32:08Z",
      "last_detected_at": "2026-10-02T14:32:10Z",
      "evidence_images": [
        {
          "image_id": "9b12a34c-d56e-78f9-0123-456789abcdef",
          "detection_id": "4a7f9218-c2b3-4f9e-a81d-6120531e21b0",
          "storage_url": "https://storage.supabase.co/v1/object/public/evidence/route04/det01.jpg",
          "captured_at": "2026-10-02T14:32:10Z"
        }
      ]
    }
    ```
    *Units:* `latitude` and `longitude` are decimal degrees; `aggregated_confidence` is float $[0.0, 1.0]$; timestamps are RFC 3339 UTC.
* **Error Responses:**
  * HTTP `400 Bad Request`: Returned when path parameter `id` is not a syntactically valid UUID.
  * HTTP `404 Not Found`: Returned when no pothole record exists matching the specified UUID.
  * HTTP `503 Service Unavailable`: Returned when database is unreachable.

---

## 5.2 Example Request and Response Code Block

The code block below demonstrates an authenticated detection ingestion request (`POST /api/v1/detections`) and the corresponding success response:

```http
POST /api/v1/detections HTTP/1.1
Host: streetsmart.internal:8080
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

{
  "run_id": "e32a71db-a9bf-4dc5-ae3d-57e16ed23c11",
  "frame_index": 14280,
  "detected_at": "2026-10-02T14:32:10.420Z",
  "damage_type": "pothole",
  "model_confidence": 0.942,
  "latitude": 39.132145,
  "longitude": -84.516028,
  "image_path": "evidence/e32a71db/4a7f9218.jpg"
}
```

```http
HTTP/1.1 201 Created
Content-Type: application/json
Location: /api/v1/detections/4a7f9218-c2b3-4f9e-a81d-6120531e21b0

{
  "detection_id": "4a7f9218-c2b3-4f9e-a81d-6120531e21b0",
  "pothole_id": "f71f1e42-9b8d-47c8-8ed8-3f35f023be18",
  "match_action": "MERGED",
  "aggregated_confidence": 0.855,
  "observation_count": 3,
  "distance_to_centroid_meters": 1.42
}
```

## 5.3 Versioning and Breaking Change Policy

The StreetSmart API is versioned via URI path prefix (`/api/v1`), where any modification that renames or removes response fields, alters existing field data types or coordinate units, adds mandatory request parameters, or changes HTTP status code behavior constitutes a breaking change requiring an increment to `/api/v2`.

---

# 6. Technology Choices with Justification

## 6.1 Database: PostgreSQL and PostGIS

PostgreSQL 16 with the PostGIS 3.4 spatial extension is the selected database platform for StreetSmart. **Team skill fit:** This selection directly leverages **Raihan's** core experience as a backend engineer specializing in database design and software development, allowing the team to design normalized relational schemas, configure foreign key constraints, write complex spatial SQL queries, and optimize spatial indexes without an exploratory learning curve. **Licensing:** PostgreSQL is distributed under the permissive open-source PostgreSQL License, and PostGIS is licensed under GNU GPL v2+, ensuring complete freedom from commercial licensing fees and full legal compliance for municipal deployment. **Community support:** Both projects possess massive global developer communities, comprehensive documentation, and dedicated spatial GIS support forums, guaranteeing rapid resolution of spatial query edge cases. **Performance:** PostGIS provides native R-tree Generalized Search Tree (`GIST`) indexing, which executes 5-meter radial proximity checks (`ST_DWithin`) and bounding-box queries in under 1 ms ($O(\log N)$), avoiding expensive table scans across tens of thousands of pothole records. **Cost and hosting:** PostgreSQL and PostGIS are completely free and open-source, deployable on low-cost managed cloud instances (Supabase free/pro tier) or zero-cost local developer environments. **Evaluated alternative:** The team evaluated MongoDB with 2dsphere indexing as an alternative; however, MongoDB was passed over because it lacks native Open Geospatial Consortium (OGC) standard spatial functions (`ST_DWithin`, `ST_MakeEnvelope`), cannot enforce relational foreign key integrity across runs, detections, and potholes, and incurs higher memory overhead for spatial joins.

## 6.2 Backend Language and Framework: Go with Gin

Go 1.22 combined with the Gin Web Framework is the selected backend language and application framework for the Ingestion Pipeline and Backend API services. **Team skill fit:** Go directly matches **Raihan's** software development and backend engineering background, while **Sahil's** DevOps experience enables efficient containerization of single-binary Go binaries into minimal Docker images and automated CI/CD deployment pipelines. **Licensing:** Go is distributed under the permissive BSD-3-Clause license, and Gin is open-source under the MIT License, imposing zero restrictive commercial obligations or proprietary royalties. **Community support:** Go and Gin boast extensive industry adoption, mature documentation, and a robust ecosystem of production-grade libraries for HTTP routing, JSON marshaling, and high-performance database drivers (`pgx`). **Performance:** Go compiles to native standalone machine code with an ultra-lightweight goroutine concurrency model, delivering sub-millisecond HTTP routing latency, minimal memory usage (<30 MB RAM per microservice), and high throughput for streaming video frame buffers and concurrent GPS coordinate ingestion. **Cost and hosting:** Due to Go's minimal CPU and memory footprints, the entire backend service can be hosted on economical entry-level Linux VPS instances (e.g., $5/month virtual servers or university-provided virtual machines) without requiring costly multi-core server tiers. **Evaluated alternative:** The team evaluated Python with FastAPI as an alternative; however, Python was passed over because its Global Interpreter Lock (GIL) and significant memory overhead create performance bottlenecks during concurrent high-throughput video frame ingestion, whereas Go provides native multi-core concurrency and single-binary deployment.

## 6.3 Front End: React with TypeScript and MapLibre GL

React 18 with TypeScript and MapLibre GL is the chosen technology stack for the Current Infrastructure Map dashboard. **Team skill fit:** This selection directly aligns with **Sahil's** dedicated specialization in frontend development, UI/UX design, and web engineering, allowing Sahil to craft a responsive, accessible (WCAG 2.1 AA), and interactive geospatial inspection portal for municipal staff. **Licensing:** React and TypeScript are licensed under the permissive MIT License, and MapLibre GL is open-source under the BSD-3-Clause license, ensuring complete freedom from commercial restrictions and eliminating proprietary map tile vendor lock-in. **Community support:** React is the most widely adopted frontend library in the world, backed by extensive documentation, comprehensive UI component libraries, and active developer forums, while MapLibre GL has strong open-source backing from the MapLibre community. **Performance:** React's virtual DOM reconciliation combined with MapLibre GL's WebGL hardware-accelerated vector tile rendering smoothly displays hundreds of interactive pothole markers and cluster layers at 60 FPS without browser UI freezing. **Cost and hosting:** The compiled frontend bundle consists of static HTML, CSS, and JavaScript assets that can be hosted entirely free of charge on platforms such as Vercel, Netlify, or GitHub Pages, eliminating recurring web server hosting fees. **Evaluated alternative:** The team evaluated Leaflet.js with vanilla JavaScript as an alternative; however, Leaflet was passed over because its DOM-based SVG marker rendering suffers severe frame rate drops when displaying dense spatial clusters, and vanilla JavaScript lacks TypeScript's static type safety for complex RFC 7946 GeoJSON schema validation.

## 6.4 Messaging or Hardware Platform: Workstation / Dashcam Hardware with In-Memory IPC & ONNX Runtime

StreetSmart utilizes standard vehicle-mounted dashcams with local workstation/server hardware, coordinating frame execution via in-memory IPC and Microsoft ONNX Runtime. **Team skill fit:** This selection directly leverages **Advait's** specialized expertise in training and optimizing deep learning computer vision models, allowing Advait to train YOLO detection networks in PyTorch, quantize model weights, and export production-ready ONNX artifacts that seamlessly integrate with **Raihan's** Go inference ingestion runtime. **Licensing:** Microsoft ONNX Runtime is open-source under the permissive MIT License, allowing unrestricted deployment and execution across development and production environments. **Community support:** ONNX Runtime is actively maintained by Microsoft, Intel, AMD, and NVIDIA, providing exhaustive multi-language documentation, pre-built cross-platform binaries, and broad hardware acceleration provider support. **Performance:** ONNX Runtime provides optimized graph execution and hardware acceleration (utilizing CUDA/TensorRT on NVIDIA GPUs or vectorized AVX-512 on multi-core CPUs), executing frame inference in ~15 ms per frame to satisfy the **AC-01.1** budget of processing a 60-minute video run in under 1,200 seconds (20 minutes). **Cost and hosting:** Utilizing standard vehicle dashcams with asynchronous post-drive workstation processing leverages existing municipal depot infrastructure and student development machines (NVIDIA RTX GPUs), completely eliminating costly per-vehicle edge compute hardware ($800–$1,500 per vehicle) and expensive cellular streaming data subscriptions. **Evaluated alternative:** The team evaluated direct embedded PyTorch inference running on vehicle-mounted edge modules (e.g., NVIDIA Jetson); however, embedded PyTorch was passed over due to its heavy runtime dependency footprint (>2.5 GB), high vehicle hardware costs, and vulnerability to in-cab thermal and vibration failures.

## 6.5 Hosting: Supabase Cloud and Containerized Docker Deployment

StreetSmart selects Supabase Cloud for managed database and object storage hosting, paired with containerized Docker deployment for application compute services. **Team skill fit:** This architecture combines **Sahil's** DevOps expertise in Docker containerization and CI/CD pipelines with **Raihan's** backend database administration skills, ensuring consistent local development and automated deployment workflows. **Licensing:** Docker engine components are open-source under Apache-2.0, and Supabase provides open-source backend tools under Apache-2.0 alongside its cloud service terms, ensuring freedom from proprietary platform lock-in. **Community support:** Docker and Supabase both maintain massive global user communities, extensive documentation, and active developer forums, providing proven deployment patterns and troubleshooting resources. **Performance:** Containerization guarantees consistent runtime dependencies and sub-second container startup times across environments, while Supabase provides co-located managed PostgreSQL and edge object storage with low-latency connection pooling (`pgbouncer`). **Cost and hosting:** Supabase provides a generous free tier including 500 MB PostgreSQL database storage and 1 GB object storage, which easily accommodates the prototype phase, while containerized Docker services can run on low-cost virtual servers ($5–$10/month VPS) or university-provided virtual machine infrastructure, keeping recurring operational expenses near zero. **Evaluated alternative:** The team evaluated AWS Enterprise Cloud (RDS PostgreSQL, S3, ECS Fargate, and Application Load Balancers) as an alternative; however, AWS was passed over because its complex configuration overhead, egress bandwidth charges, and steep monthly subscription fees would rapidly exceed the senior design student budget.
