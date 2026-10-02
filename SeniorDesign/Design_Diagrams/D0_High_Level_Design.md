# StreetSmart — High-Level System Design (Design D0)

**Team Members:** Advait Vagerwal, Sahil Thakare, Raihan Rafeek  
**Course:** CS 5001 - Computer Science Senior Design  
**Advisor:** Eric Jamison  
**Assignment:** Assignment 5 — High-Level System Design (Design D0)  
**Date:** 2 October 2026  
**Document Version:** 1.0  

---

# 1. Title, Goal Statement, and Conventions

## Project Title
**StreetSmart: Automated Public Infrastructure Damage Detection and Geospatial Reporting System**

## Goal Statement
StreetSmart is an automated public infrastructure inspection system that analyzes vehicle-mounted camera footage and synchronized GPS data to detect, geotag, and classify roadway damage such as potholes. The system provides municipal personnel and downstream city systems with a centralized geospatial database, interactive visualization dashboard, and standardized API integration to accelerate road maintenance and improve public transit safety.

### Basic Input
The basic input to the system is vehicle-mounted camera video footage (in standard container formats such as MP4/H.264) capturing road surfaces, accompanied by synchronized NMEA GPS track data (latitude, longitude, and timestamps) recorded during vehicle transit.

### Basic Output
The basic output of the system is a centralized database of validated, geotagged infrastructure damage records, displayed on an interactive geospatial web map for municipal personnel and exported via authenticated REST APIs as standardized RFC 7946 GeoJSON datasets for municipal GIS and work-order management.

## Diagram Conventions
The table below specifies the graphical syntax and visual semantics utilized across all architecture and data-flow diagrams in this document and accompanying source files:

| Notation / Shape | Visual Style | Semantic Meaning |
| :--- | :--- | :--- |
| **Solid Rectangle** | Blue border, light blue fill (`#e7f5ff`, `#1971c2`) | Internal software component built and maintained by the StreetSmart team. |
| **Rounded Rectangle** | Orange dashed border, peach fill (`#fff4e6`, `#d9480f`) | External system, hardware dependency, or third-party platform outside team control. |
| **Cylinder** | Green border, light green fill (`#ebfbee`, `#2b8a3e`) | Persistent database storage or versioned model artifact storage. |
| **Parallelogram** | Purple border, light purple fill (`#f3f0ff`, `#6741d9`) | Input or output data artifact crossing a system boundary. |
| **Solid Arrow** | Solid line with arrowhead (`——>`) | Core unidirectional data flow or synchronous interface between components. |
| **Dashed Arrow** | Dashed line with arrowhead (`- - ->`) | External network integration, batch file synchronization, or asynchronous export. |
| **Interface IDs** | `I1`, `I2`, `I3`, ..., `I10` | Unique interface identifier mapping directly to the Interface Specification Table. |

---

# 2. Block Diagram (the D0 Diagram)

The D0 Block Diagram provides the highest-level structural view of the StreetSmart platform. It illustrates all seven internal major components, three external systems/dependencies, and the ten formal interfaces connecting them.

```mermaid
flowchart TD
    %% ==========================================
    %% TITLE & GOAL BLOCK (Embedded on Diagram)
    %% ==========================================
    subgraph TitleBlock ["StreetSmart — High-Level System Block Diagram (Design D0)"]
        direction TB
        TITLE["Project: StreetSmart | Goal: Detect, geotag, and persist road infrastructure damage from vehicle cameras for municipal review and GIS integration."]
    end

    %% ==========================================
    %% LEGEND & CONVENTIONS (Embedded on Diagram)
    %% ==========================================
    subgraph LegendBlock ["Legend & Conventions"]
        direction TB
        L_COMP["Internal Component (Built by Team)"]:::compStyle
        L_EXT(["External System / Hardware Dependency"]):::extStyle
        L_DB[("Persistent Database / Model Storage")]:::dbStyle
        L_DATA[/Input / Output Data Artifact/]:::dataStyle
    end

    %% ==========================================
    %% EXTERNAL SYSTEMS & HARDWARE
    %% ==========================================
    EXT_DATA[/Labeled Training Data
(RDD2022 / Roboflow)/]:::extStyle
    EXT_CAM(["Vehicle Camera Hardware
(1080p MP4/H.264)"]):::extStyle
    EXT_GPS(["Vehicle GPS Receiver
(NMEA 0183 Track)"]):::extStyle
    EXT_CITY(["City Systems & Municipal GIS
(Cincinnati DTO / OPDA / CAGIS)"]):::extStyle

    %% ==========================================
    %% INTERNAL STREETSMART COMPONENTS
    %% ==========================================
    subgraph ModelSubsystem ["Machine Learning Subsystem"]
        direction LR
        COMP_TRAIN["Model Training
(Advait Vagerwal)"]:::compStyle
        COMP_MSTORE[("Trained Model Storage
(Advait Vagerwal)")]:::dbStyle
        COMP_INFER["Model Inference
(Raihan Rafeek)"]:::compStyle
    end

    subgraph CoreBackend ["Ingestion & Persistence Tier"]
        direction TB
        COMP_INGEST["Ingestion Pipeline
(Sahil Thakare)"]:::compStyle
        COMP_DB[("PostgreSQL Database
(Raihan Rafeek)")]:::dbStyle
        COMP_API["Backend API
(Raihan Rafeek)"]:::compStyle
    end

    subgraph PresentationTier ["Presentation Dashboard"]
        direction TB
        COMP_MAP["Current Infrastructure Map
(Sahil Thakare)"]:::compStyle
    end

    %% ==========================================
    %% SUBSYSTEM & COMPONENT INTERFACES
    %% ==========================================
    EXT_DATA -->|I1: Training Dataset| COMP_TRAIN
    COMP_TRAIN -->|I2: Exported Model Weights| COMP_MSTORE
    COMP_MSTORE -->|I3: Loaded ONNX Session| COMP_INFER

    EXT_CAM -->|I4: Video Frames Stream| COMP_INFER
    EXT_GPS -->|I5: Spatial Coordinates Track| COMP_INGEST

    COMP_INFER -->|I6: Damage Detections| COMP_INGEST
    COMP_INGEST -->|I7: Geotagged Damage Records| COMP_DB
    COMP_DB -->|I8: Infrastructure Records Query| COMP_API

    COMP_API -->|I9: Geospatial Damage Data| COMP_MAP
    COMP_API -.->|I10: Standardized GeoJSON Integration| EXT_CITY

    %% ==========================================
    %% MERMAID STYLING CLASSES
    %% ==========================================
    classDef compStyle fill:#e7f5ff,stroke:#1971c2,stroke-width:2px,color:#1864ab;
    classDef extStyle fill:#fff4e6,stroke:#d9480f,stroke-width:2px,stroke-dasharray: 5 5,color:#d9480f;
    classDef dbStyle fill:#ebfbee,stroke:#2b8a3e,stroke-width:2px,color:#2b8a3e;
    classDef dataStyle fill:#f3f0ff,stroke:#6741d9,stroke-width:2px,color:#5f3dc4;
```

### Component Overview

| Component | Architecture Boundary & Purpose |
| :--- | :--- |
| **Model Training** | Fine-tunes deep learning object detection networks (YOLO family) on annotated roadway datasets, validating bounding-box precision and mAP metrics before exporting production-ready ONNX weights. |
| **Trained Model Storage** | Manages versioned model artifacts, checkpoints, and execution metadata, providing immutable model files to inference engines. |
| **Model Inference** | Ingests video streams, extracts keyframes, and executes hardware-accelerated computer vision inference via ONNX Runtime to identify pavement damage with bounding boxes and confidence scores. |
| **Ingestion Pipeline** | Ingests raw GPS track data and vision inference events, correlates timestamps to resolve geographic coordinates, applies automated PII redaction (license plates/faces), and validates records. |
| **PostgreSQL Database** | Relational and spatial database engine with PostGIS extension, providing persistent storage, spatial indexing (`GIST`), and ACID guarantees for infrastructure damage records. |
| **Backend API** | Central application server exposing authenticated RESTful endpoints for spatial queries, administrative actions, and RFC 7946-compliant GeoJSON data exports. |
| **Current Infrastructure Map** | Single-page interactive web application displaying detected roadway defects on an interactive vector map with severity filtering, cluster analysis, and record inspection. |

---

# 3. Component Responsibility Table

In accordance with system design constraints, each component possesses a single, cohesive responsibility expressed without compound clauses. Every component traces directly to user stories and is assigned exactly one primary team member owner who will lead its implementation tasks.

| Component | Responsibility | Interfaces In | Interfaces Out | Primary Owner |
| :--- | :--- | :--- | :--- | :--- |
| **Model Training** | Trains deep learning computer vision models on labeled roadway damage datasets to produce deployable detection artifacts. | `I1` | `I2` | Advait Vagerwal |
| **Trained Model Storage** | Persists exported ONNX model artifacts for version-controlled deployment to inference environments. | `I2` | `I3` | Advait Vagerwal |
| **Model Inference** | Processes roadway video frames through the deployed model to detect public infrastructure damage with confidence scores. | `I3`, `I4` | `I6` | Raihan Rafeek |
| **Ingestion Pipeline** | Synchronizes detected damage events with spatial GPS coordinates into validated infrastructure records. | `I5`, `I6` | `I7` | Sahil Thakare |
| **PostgreSQL Database** | Persists validated infrastructure damage records with geospatial coordinates for structured querying. | `I7` | `I8` | Raihan Rafeek |
| **Backend API** | Exposes secure RESTful endpoints for client querying of infrastructure damage data. | `I8` | `I9`, `I10` | Raihan Rafeek |
| **Current Infrastructure Map** | Renders an interactive geospatial dashboard displaying detected roadway defects for municipal review. | `I9` | — | Sahil Thakare |

---

# 4. Interface Specification Table

The table below formally defines every connection illustrated on the D0 Block Diagram. Each interface specifies named and typed inputs, named and typed outputs, data formats, communication protocols, and explicit error-handling behaviors identifying the responsible component.

| ID | Interface Connection | Inputs (Named & Typed) | Outputs (Named & Typed) | Data Format | Protocol | Error Handling & Handling Component |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **I1** | Labeled Dataset → Model Training | `image_files: Binary/JPEG[]`<br>`annotations: YOLO_TXT[]`<br>`classes: String[]` | `dataset_manifest: JSON`<br>`validated_pairs: Integer` | JPEG / YOLO Text Annotations | Local POSIX File I/O | Unreadable images or corrupt annotation coordinates are rejected with a warning log; **Model Training** halts if invalid samples exceed 5% of dataset. |
| **I2** | Model Training → Trained Model Storage | `trained_weights: Tensor`<br>`training_metrics: JSON`<br>`model_version: String` | `onnx_model: Binary/ONNX`<br>`export_manifest: JSON` | ONNX Binary / JSON Metadata | Local File Storage / Atomic Move | Export or quantization failure is logged; **Model Training** prevents overwriting the production model pointer and retains the previous stable checkpoint. |
| **I3** | Trained Model Storage → Model Inference | `model_path: String`<br>`execution_provider: String` | `session: InferenceSession`<br>`input_specs: TensorShape` | ONNX Model Format | In-Memory Model Loader | Model checksum failure or missing provider triggers an initialization exception; **Model Inference** halts startup, logs critical error, and alerts the operator. |
| **I4** | Vehicle Camera → Model Inference | `video_container: Binary/H.264`<br>`frame_rate: Float`<br>`video_id: UUID` | `decoded_frame: Tensor[3, 640, 640]`<br>`frame_idx: Integer`<br>`relative_ts: Float` | MP4 / H.264 Video Stream | V4L2 Video Capture / File Stream | Corrupted video frames or unreadable container headers are dropped; **Model Inference** logs a warning and advances to the next valid keyframe (I-frame). |
| **I5** | GPS Receiver → Ingestion Pipeline | `nmea_sentence: String`<br>`baud_rate: Integer` | `latitude: Float`<br>`longitude: Float`<br>`altitude: Float`<br>`gps_timestamp: String(ISO8601)`<br>`fix_quality: Integer` | NMEA 0183 / JSON Track | Serial Stream / HTTP Upload | Corrupted sentences or GPS fix loss cause **Ingestion Pipeline** to reject coordinates and flag affected detections as `LOCATION_UNRESOLVED` (AC-01.2). |
| **I6** | Model Inference → Ingestion Pipeline | `decoded_frame: Tensor`<br>`frame_idx: Integer`<br>`relative_ts: Float` | `damage_type: String`<br>`confidence: Float`<br>`bbox: Float[4]`<br>`crop_image: Binary/JPEG`<br>`frame_timestamp: String(ISO8601)` | Structured JSON / IPC Record | Local IPC / Unix Domain Socket | Detections below 0.70 confidence are dropped; IPC socket errors are caught by **Model Inference**, which retries transmission up to 3 times before dropping frame. |
| **I7** | Ingestion Pipeline → PostgreSQL Database | `record_id: UUID`<br>`damage_type: String`<br>`confidence: Float`<br>`geom: Geometry(Point, 4326)`<br>`detected_at: Timestamp`<br>`image_url: String`<br>`status: String` | `db_status: Integer`<br>`rows_affected: Integer`<br>`inserted_id: UUID` | SQL Statements / PostGIS Binary Tuples | PostgreSQL Wire Protocol (TCP 5432) | Connection failure or constraint violation triggers retry with exponential backoff (3 attempts); **Ingestion Pipeline** buffers records locally and alerts admin. |
| **I8** | PostgreSQL Database → Backend API | `sql_query: String`<br>`params: QueryParameters`<br>(bbox, date_range, min_conf) | `record_set: Record[]`<br>(uuid, type, conf, geom, time, img, status) | PostGIS Result Tuples | PostgreSQL Connection Pool (`asyncpg`) | Query timeout or database unreachable returns HTTP 503; **Backend API** catches the database exception, resets the connection pool, and logs error trace. |
| **I9** | Backend API → Current Infrastructure Map | `http_request: HTTP_GET`<br>`auth_token: Bearer JWT`<br>`query_params: ViewportBBox` | `geojson_data: GeoJSON`<br>`feature_count: Integer`<br>`http_status: Integer` | RFC 7946 GeoJSON / REST JSON | HTTPS / REST (Port 443) | Expired JWT returns HTTP 401; **Current Infrastructure Map** catches response, redirects user to login, and displays user-friendly error toast. |
| **I10** | Backend API ↔ City Systems | `http_request: HTTP_GET`<br>`api_key: String`<br>`export_bbox: Float[4]`<br>`format: String` | `geojson_features: GeoJSON`<br>`export_meta: JSON`<br>`http_status: Integer` | RFC 7946 GeoJSON / REST JSON | HTTPS / REST (TLS 1.3) | Out-of-range coordinates trigger HTTP 400 within 1.0s (AC-02.2); **Backend API** validates inputs, returns RFC 7807 error JSON, and logs access violation. |

---

## Example Payloads

### Example 1: Damage Detection & Ingestion Payload (`I6` / `I7`)
This payload represents a validated pothole detection generated by Model Inference and processed by the Ingestion Pipeline after synchronizing with GPS coordinates and applying PII redaction:

```json
{
  "detection_id": "4a7f9218-c2b3-4f9e-a81d-6120531e21b0",
  "damage_type": "pothole",
  "confidence": 0.942,
  "bounding_box": {
    "x_min": 214.5,
    "y_min": 380.0,
    "x_max": 425.2,
    "y_max": 512.8
  },
  "geospatial": {
    "latitude": 39.132145,
    "longitude": -84.516028,
    "altitude_meters": 224.5,
    "coordinate_system": "EPSG:4326"
  },
  "metadata": {
    "detected_at": "2026-10-02T14:32:10.420Z",
    "source_video_id": "vid_20261002_route04_cincy",
    "video_frame_index": 14280,
    "vehicle_speed_kph": 38.6,
    "pii_redacted": true
  },
  "reference_image": {
    "image_uri": "https://storage.streetsmart.internal/damage/4a7f9218-c2b3.jpg",
    "checksum_sha256": "9f83c1264c9e4210d7a9b08f8a65f9a3e2154c125674389a0f4523c14a2b918d"
  }
}
```

### Example 2: Standardized Municipal GIS Export Payload (`I9` / `I10`)
Conforming to RFC 7946 GeoJSON FeatureCollection specifications for direct consumption by city GIS systems (e.g., CAGIS / ArcGIS) and the interactive web map:

```json
{
  "type": "FeatureCollection",
  "metadata": {
    "generated_at": "2026-10-02T15:00:00Z",
    "query_bounding_box": [-84.5500, 39.1000, -84.4500, 39.1600],
    "total_records": 1,
    "crs": "urn:ogc:def:crs:OGC:1.3:CRS84"
  },
  "features": [
    {
      "type": "Feature",
      "id": "4a7f9218-c2b3-4f9e-a81d-6120531e21b0",
      "geometry": {
        "type": "Point",
        "coordinates": [-84.516028, 39.132145]
      },
      "properties": {
        "damage_type": "pothole",
        "confidence_score": 0.94,
        "detection_timestamp": "2026-10-02T14:32:10Z",
        "severity_level": "HIGH",
        "review_status": "UNRESOLVED",
        "verification_count": 3,
        "image_url": "https://streetsmart.cincinnati-oh.gov/api/v1/evidence/4a7f9218-c2b3.jpg"
      }
    }
  ]
}
```

### Example 3: Standardized API Error Response Payload (RFC 7807)
Standardized error structure returned by the Backend API when request validation fails (satisfying AC-02.2):

```json
{
  "type": "https://streetsmart.cincinnati-oh.gov/errors/invalid-spatial-parameter",
  "title": "Invalid Coordinate Bounding Box",
  "status": 400,
  "detail": "Requested latitude coordinate '94.2000' exceeds valid WGS84 range [-90.0, 90.0].",
  "instance": "/api/v1/export/geojson?bbox=-84.5,94.2,-84.4,39.1",
  "timestamp": "2026-10-02T15:00:01.045Z",
  "invalid_params": [
    {
      "name": "bbox[1]",
      "reason": "Value must be between -90.0 and 90.0 degrees latitude."
    }
  ]
}
```

---

# 5. Data-Flow Diagram

The data-flow architecture illustrates how information transitions through successive transformations, noting the exact form of data crossing each boundary and the timing budgets enforced by system acceptance criteria. StreetSmart incorporates two distinct flows: an offline Model Training and Deployment Flow, and a runtime Ingestion, Detection, Storage, and Geospatial Visualization Flow.

## Flow 1: Model Training and Model Deployment Flow (Offline)

```mermaid
flowchart LR
    subgraph Flow1Title ["Flow 1: Model Training & Model Deployment Flow (Offline)"]
        direction TB
        F1_T["Project: StreetSmart | Goal: Transform raw labeled road damage imagery into an optimized, deployable ONNX model artifact."]
    end

    subgraph Flow1Legend ["Conventions & Forms"]
        direction TB
        F1_L1[/Data State: Name [Form]/]:::dataStyle
        F1_L2["Processing Component"]:::compStyle
        F1_L3[("Model Artifact Storage")]:::dbStyle
    end

    F1_A[/Labeled Training Imagery
[raw dataset: JPEG + YOLO txt]/]:::dataStyle
    F1_B["Model Training
(Advait Vagerwal)
PyTorch Training & Val"]:::compStyle
    F1_C[("Trained Model Storage
(Advait Vagerwal)
[production artifact: ONNX]")]:::dbStyle

    F1_A -->|"Training images & bounding boxes
[raw dataset]"| F1_B
    F1_B -->|"Trained weights & execution graph
[production artifact: ONNX]"| F1_C

    classDef compStyle fill:#e7f5ff,stroke:#1971c2,stroke-width:2px,color:#1864ab;
    classDef extStyle fill:#fff4e6,stroke:#d9480f,stroke-width:2px,stroke-dasharray: 5 5,color:#d9480f;
    classDef dbStyle fill:#ebfbee,stroke:#2b8a3e,stroke-width:2px,color:#2b8a3e;
    classDef dataStyle fill:#f3f0ff,stroke:#6741d9,stroke-width:2px,color:#5f3dc4;
```

## Flow 2: Runtime Ingestion, Detection, Storage, and Geospatial Visualization Flow

```mermaid
flowchart TD
    subgraph Flow2Title ["Flow 2: Runtime Ingestion, Detection, Storage, & Geospatial Visualization Flow"]
        direction TB
        F2_T["Project: StreetSmart | Goal: Continuous transformation of raw video and GPS readings into validated database records, map pins, and GIS exports."]
    end

    subgraph Flow2Legend ["Data Forms & Timing Budgets"]
        direction TB
        F2_L1[/Sensor Input: [raw reading]/]:::extStyle
        F2_L2["Processing Stage"]:::compStyle
        F2_L3[("Database: [stored row]")]:::dbStyle
        F2_L4["Timing Budget Annotation"]:::budgetStyle
    end

    %% SENSOR INPUTS
    S_CAM[/Vehicle Camera Footage
[raw reading: H.264 stream]/]:::extStyle
    S_GPS[/Vehicle GPS Receiver
[raw reading: NMEA sentences]/]:::extStyle

    %% STAGES
    STAGE_INFER["Model Inference
(Raihan Rafeek)
Frame Extraction & Detection
<b>Timing Budget: < 1,200s for 60 min video (AC-01.1)</b>"]:::compStyle
    STAGE_INGEST["Ingestion Pipeline
(Sahil Thakare)
GPS Sync, Validation, & PII Redaction
<b>Location Error Budget: < 3.0s (AC-01.2)</b>"]:::compStyle
    STAGE_DB[("PostgreSQL Database
(Raihan Rafeek)
Spatial Data Store
[stored row]")]:::dbStyle
    STAGE_API["Backend API
(Raihan Rafeek)
Spatial Query & Export Serialization
<b>Export Budget: < 5.0s (AC-02.1)</b>
<b>Validation Rejection: < 1.0s (AC-02.2)</b>"]:::compStyle
    STAGE_MAP["Current Infrastructure Map
(Sahil Thakare)
Interactive Geospatial Dashboard
<b>Viewport Query: < 2.0s</b>"]:::compStyle
    STAGE_CITY(["City Systems / Municipal GIS
(CAGIS / DTO / OPDA)
[export file: RFC 7946 GeoJSON]"]):::extStyle

    %% FLOW ARROWS WITH DATA AND FORM
    S_CAM -->|"Decoded video frames
[raw reading]"| STAGE_INFER
    S_GPS -->|"Timestamped geographic track
[raw reading]"| STAGE_INGEST
    STAGE_INFER -->|"Damage classes, confidence & bounding boxes
[in-memory detection]"| STAGE_INGEST
    STAGE_INGEST -->|"Geotagged & PII-redacted damage records
[validated record]"| STAGE_DB
    STAGE_DB -->|"Queried spatial damage rows
[stored row]"| STAGE_API
    STAGE_API -->|"Damage locations, severity, & image URLs
[map pin / JSON]"| STAGE_MAP
    STAGE_API -.->|"RFC 7946 Standardized FeatureCollection
[export file / GeoJSON]"| STAGE_CITY

    classDef compStyle fill:#e7f5ff,stroke:#1971c2,stroke-width:2px,color:#1864ab;
    classDef extStyle fill:#fff4e6,stroke:#d9480f,stroke-width:2px,stroke-dasharray: 5 5,color:#d9480f;
    classDef dbStyle fill:#ebfbee,stroke:#2b8a3e,stroke-width:2px,color:#2b8a3e;
    classDef dataStyle fill:#f3f0ff,stroke:#6741d9,stroke-width:2px,color:#5f3dc4;
    classDef budgetStyle fill:#fff3e0,stroke:#e65100,stroke-width:1px,color:#bf360c;
```

### Detailed Stage-by-Stage Walkthrough

#### Flow 1: Model Training and Model Deployment (Offline)
1. **Dataset Preparation (`[raw dataset]`):** Labeled public datasets (RDD2022, Roboflow Pothole datasets) and locally annotated roadway imagery are structured into normalized image directories and YOLO text coordinate files.
2. **Model Training & Evaluation:** The Model Training component fine-tunes a YOLO architecture across multiple epochs, calculating validation loss, precision, recall, and mean Average Precision (mAP@0.5).
3. **Artifact Export (`[production artifact]`):** Upon reaching evaluation criteria (mAP > 0.75), the model graph is exported into an optimized ONNX binary file and persisted to Trained Model Storage with metadata specifying input tensor dimensions ($3 	imes 640 	imes 640$) and class labels.

#### Flow 2: Runtime Ingestion, Detection, Storage, and Geospatial Visualization (Runtime)
1. **Raw Sensor Ingestion (`[raw reading]`):** Vehicle-mounted cameras record roadway video in 1080p MP4/H.264 format, while vehicle GPS modules capture continuous NMEA 0183 coordinate streams with UTC timestamps.
2. **Vision Inference (`[in-memory detection]`):** Model Inference consumes video frames, resizes tensors, and executes ONNX inference. Detections exceeding the 0.70 confidence threshold generate in-memory detection objects containing damage classification, bounding-box coordinates, frame index, and cropped evidence images.  
   * **Timing Budget:** Inference on a 60-minute video run must complete within 1,200 seconds (20 minutes) on standard processing hardware (AC-01.1).
3. **Synchronization, Validation, & Privacy Redaction (`[validated record]`):** The Ingestion Pipeline matches detection timestamps with GPS coordinates using linear interpolation. Before database persistence, an automated privacy filter blurs any detected license plates and pedestrian faces in the cropped reference image (US-04). If GPS fix was lost or coordinates are invalid, the record is flagged with status `LOCATION_UNRESOLVED` and prevented from external transfer (AC-01.2).  
   * **Timing Budget:** Any GPS exception must be isolated, flagged as `LOCATION_UNRESOLVED`, and logged within 3.0 seconds (AC-01.2).
4. **Database Persistence (`[stored row]`):** Validated damage records are committed to PostgreSQL using PostGIS `ST_SetSRID(ST_MakePoint(lon, lat), 4326)` geometry points, indexed via spatial R-trees (`GIST` indexes).
5. **API Query Execution & Transformation (`[map pin / JSON]` & `[export file / GeoJSON]`):** Municipal users interact with the map dashboard, or city systems submit export requests. The Backend API executes bounding-box spatial queries against PostGIS and serializes results into RFC 7946 GeoJSON FeatureCollections.  
   * **Timing Budgets:**
     * Export requests for up to 500 pothole records must be delivered within 5.0 seconds (AC-02.1).
     * Out-of-bounds parameter validation rejections with HTTP 400 must return within 1.0 second (AC-02.2).
     * Interactive web map bounding-box viewport queries must return within 2.0 seconds.

---

# 6. Architecture Pattern and Justification

## Selected Architecture Patterns

StreetSmart employs a hybrid architecture combining three classical patterns from the Week 5 syllabus:

1. **Pipeline Architecture Pattern:** Governs the end-to-end data ingestion and computer vision processing flow. Data transitions unidirectionally through sequential, decoupled stages: Video Frame Decoding $ightarrow$ ONNX Computer Vision Inference $ightarrow$ GPS Spatial Correlation $ightarrow$ PII Privacy Redaction $ightarrow$ Database Persistence. Each stage operates with strict interface boundaries, ensuring processing errors in one stage (such as a dropped video frame) do not crash downstream stages.
2. **Client-Server Architecture Pattern:** Governs user interaction and external system interoperability. The Current Infrastructure Map acts as a lightweight client running in municipal staff web browsers, while the Backend API operates as the central server exposing HTTPS endpoints. Client applications never connect directly to the database, enforcing security boundaries and query validation.
3. **Layered / Microservice Architecture Pattern:** Governs internal system structuring by strictly separating the Presentation Layer (React Web Dashboard), Application/API Service Layer (FastAPI REST Service), Persistence Layer (PostgreSQL with PostGIS), and Compute Worker Layer (Inference Engine). Separating the computationally heavy inference engine from the web API prevents deep learning processing from monopolizing web server threads.

---

## Pattern Justification Against Five Class Criteria

### 1. Fit to the Problem
The pipeline pattern directly matches the physical and temporal reality of municipal road inspections: vehicles traverse streets capturing continuous sensor streams that must be systematically transformed from unstructured binary pixels into structured geospatial records. The client-server model allows diverse municipal stakeholders (DTO division managers, OPDA data analysts, maintenance crews) to access a unified, real-time map of road conditions without installing local analytical software. Crucially, the pipeline architecture allows a dedicated **Privacy Filter stage** to execute automated redaction of pedestrian faces and vehicle license plates before records are stored, directly fulfilling municipal data privacy mandates (**US-04**).

### 2. Team Skills
The architectural separation maps directly to the team's defined roles and technical competencies:
* **Advait Vagerwal** focuses on machine learning architectures, training pipelines, and ONNX model optimization.
* **Raihan Rafeek** manages the backend API services, PostgreSQL/PostGIS database design, and inference runtime orchestration.
* **Sahil Thakare** develops the user-facing web map dashboard, UI/UX design, and the GPS ingestion/redaction validation pipeline.  
Because the components interact via well-defined REST and IPC contracts, team members can build, test, and mock their respective subsystems in parallel without blocking one another.

### 3. Performance and Timing
Separating computationally intensive computer vision inference from the web API ensures that heavy GPU/CPU workloads do not degrade web dashboard responsiveness. Video processing is executed asynchronously in batch mode, satisfying the requirement to process 60 minutes of drive footage within 1,200 seconds (**AC-01.1**). Concurrently, the Backend API leverages PostGIS spatial indexing (`GIST`) to execute geographic bounding-box queries in milliseconds, easily satisfying the requirement to generate 500-record GeoJSON exports in under 5.0 seconds (**AC-02.1**) and reject invalid coordinates within 1.0 second (**AC-02.2**).

### 4. Scalability
The modular pipeline and client-server design provide clear independent scaling axes:
* If roadway video volume increases across multiple municipal fleets, additional Model Inference workers can be provisioned horizontally across available compute nodes without modifying the database schema or web interface.
* If municipal staff usage spikes during heavy pothole seasons (e.g., late winter thaw), the Backend API can scale horizontally behind a reverse proxy (e.g., NGINX).
* PostgreSQL with PostGIS supports hundreds of thousands of spatial records, allowing multi-year roadway condition tracking across the Greater Cincinnati area.

### 5. Hardware Constraints
The architecture explicitly addresses hardware realities. Real-time, on-vehicle inference requires expensive, power-hungry edge GPUs (e.g., NVIDIA Jetson AGX) mounted inside municipal vehicles, exposing sensitive electronics to vehicular vibrations, extreme temperatures, and battery drain. By decoupling data capture (standard vehicle dashcams and GPS units) from inference processing (workstation or server compute), StreetSmart eliminates the need for specialized vehicle hardware. Furthermore, packaging the model in ONNX format allows the inference engine to utilize available hardware execution providers (NVIDIA CUDA, DirectML, or multicore CPU) without modifying application code.

---

## Integration of Week 3 Project Constraints

The chosen architecture directly satisfies the constraints established in Week 3:

* **Economic / Budget Constraints:** Cloud computing and GPU-accelerated virtual machines represent the project's greatest recurring expense. Decoupling the pipeline allows the team to run batch inference on local workstations or low-cost spot instances during off-peak hours, while maintaining the web dashboard and database on an economical, low-resource VPS. Additionally, frame-filtering in the ingestion pipeline discards redundant stationary frames, avoiding unnecessary cloud storage costs.
* **Hosting & Deployment Constraints:** The system is structured into containerized Docker services (Inference Worker, FastAPI Server, PostgreSQL/PostGIS Database, and NGINX Static Web Host). This containerized topology enables deployment on university-provided virtual servers or self-hosted Linux infrastructure without incurring commercial enterprise cloud lock-in.
* **Privacy & Surveillance Compliance Constraints (US-04):** Municipal data compliance policies strictly regulate the capture of public street imagery. Incorporating an automated PII redaction filter directly within the Ingestion Pipeline ensures that vehicle license plates and citizen faces are blurred before evidence frames are written to persistent storage or exposed via API endpoints.
* **Accessibility & Professional Constraints:** The web dashboard client is developed following WCAG 2.1 AA accessibility guidelines, providing high-contrast color palettes for damage severity pins, keyboard navigation for tabular inspection views, and screen-reader accessible metadata. This ensures compliance with municipal public software procurement standards within the two-semester Senior Design timeline.

---

## Rejected Alternative Architecture

### Pattern Considered: Monolithic Architecture
A monolithic architecture would package the computer vision inference engine, video decoding, GPS parsing, database access, REST API endpoints, and web frontend serving into a single unified application codebase and process.

### Why It Was Considered
A monolith is initially simpler to scaffold: it eliminates network hops between internal services, avoids inter-process serialization overhead, requires only a single Git repository and build pipeline, and simplifies local single-machine development during early project stages.

### Why It Was Rejected
1. **Resource Contention and Instability:** Deep learning computer vision libraries (PyTorch, OpenCV, CUDA runtime) require substantial RAM and GPU compute. Under a monolithic architecture, executing a heavy video inference batch would starve the web server and database connection pool of CPU cycles and memory, resulting in HTTP timeouts and frozen web maps for municipal staff.
2. **Deployment and Dependency Bloat:** A monolith bundles heavy machine learning binaries (~3–5 GB container footprint) with the web API. Updating a simple frontend UI bug or API query would require rebuilding, testing, and redeploying the entire machine learning environment.
3. **Impediment to Municipal Interoperability:** A monolith typically encourages tightly coupled internal database calls rather than clean, standardized RESTful API boundaries. This would directly hinder seamless integration with external City of Cincinnati GIS and work-order platforms (**US-01**, **US-05**).
4. **Violates Separation of Concerns:** Combining data ingestion, deep learning, geospatial analysis, and user interface logic into one application obscures component boundaries and violates the single responsibility principle, making parallel development across three team members inefficient and error-prone.

---

# 7. Decision Log

The decision log records pivotal architectural and engineering decisions made during the design of StreetSmart. These entries capture the engineering trade-offs, evaluated alternatives, and rationale grounded in user stories and system constraints.

---

### Decision 1: Asynchronous Batch Ingestion Pipeline vs. Real-Time On-Vehicle Edge Inference

* **Context & Problem:** StreetSmart must process vehicle-mounted camera footage to detect roadway damage. The team had to determine whether inference should execute in real time on hardware mounted inside the vehicle or asynchronously in batch mode on dedicated server/workstation compute after vehicle patrols return.
* **Alternatives Considered:**
  1. *Real-Time Edge Inference:* Deploy embedded computing modules (e.g., NVIDIA Jetson Orin Nano, Raspberry Pi with Coral TPU) inside municipal patrol vehicles to perform real-time frame inference as the vehicle drives.
  2. *Live Cellular Video Streaming:* Stream live 1080p video from vehicles over 4G/5G LTE networks to a cloud server for immediate cloud inference.
  3. *Asynchronous Post-Drive Batch Ingestion (Chosen):* Log video and GPS tracks to local onboard storage (SD card/SSD) and ingest footage via an automated batch pipeline when vehicles return to the depot or connect to Wi-Fi.
* **Evaluation & Rationale (Why Chosen Option Won):** Real-time edge hardware significantly increases per-vehicle deployment costs ($800–$1,500 per vehicle), introduces thermal and power management challenges in municipal vehicles, and risks hardware failure from road vibration. Cellular streaming of 1080p video is economically infeasible due to recurring cellular data bandwidth expenses ($$$/GB). In contrast, municipal road repairs operate on 24- to 72-hour work order cycles; potholes do not disappear over a few hours. Asynchronous batch processing fully satisfies municipal operational needs, easily achieves the timing budget of processing 60 minutes of video in under 20 minutes (**AC-01.1**), and allows the team to utilize existing workstation/server GPU compute without vehicle hardware modifications.
* **Traceability:** Aligns with Economic Constraints, Hardware Constraints, and **US-01**.

---

### Decision 2: ONNX Runtime Model Interchange Format vs. Native PyTorch Production Coupling

* **Context & Problem:** The computer vision model is trained using deep learning frameworks (PyTorch / Ultralytics). The team needed to decide how the trained model would be packaged, deployed, and executed in the runtime inference pipeline.
* **Alternatives Considered:**
  1. *Direct PyTorch Deployment:* Run inference directly in Python using the native PyTorch/Ultralytics library in production.
  2. *Proprietary Hardware Compilers (TensorRT / OpenVINO only):* Compile models exclusively to vendor-specific formats (NVIDIA TensorRT or Intel OpenVINO).
  3. *ONNX Export with ONNX Runtime (Chosen):* Export trained PyTorch models to the open-standard Open Neural Network Exchange (ONNX) format and execute inference using Microsoft ONNX Runtime.
* **Evaluation & Rationale (Why Chosen Option Won):** Deploying native PyTorch in production requires installing heavy development dependencies (~2.5 GB library footprint), incurs slower cold-start times, and tightly couples the inference service to specific Python framework versions. Proprietary compilers like TensorRT create rigid hardware lock-in to specific GPU architectures, conflicting with our hardware constraint flexibility. ONNX provides a standardized, interoperable model representation with cross-platform execution providers (CUDA for NVIDIA GPUs, DirectML for AMD/Intel, and optimized CPU execution). This enables lightweight inference containers, faster inference throughput, and seamless portability across team workstations and deployment servers.
* **Traceability:** Aligns with Professional Constraints, Performance and Timing, and **US-02**.

---

### Decision 3: PostgreSQL with PostGIS Spatial Extension vs. NoSQL / Document Store

* **Context & Problem:** StreetSmart must store thousands of roadway defect records, each containing geographic coordinates, confidence metrics, timestamps, severity classifications, and image references, while supporting fast geographic bounding-box queries for map rendering and GIS export.
* **Alternatives Considered:**
  1. *Document Database (MongoDB with 2dsphere indexing):* Store detections as JSON BSON documents with geospatial coordinates.
  2. *Full-Text / Search Engine (Elasticsearch):* Ingest detections as spatial documents optimized for spatial filtering.
  3. *Relational Spatial Database (PostgreSQL with PostGIS) (Chosen):* Store detections in a relational database with native OGC-compliant spatial geometry types (`GEOMETRY(Point, 4326)`) and `GIST` indexing.
* **Evaluation & Rationale (Why Chosen Option Won):** While MongoDB handles unstructured JSON easily, it lacks native compliance with Open Geospatial Consortium (OGC) standards and provides limited spatial query operators compared to PostGIS. PostGIS is the industry-standard spatial database utilized by municipal engineering and GIS departments worldwide (including Cincinnati CAGIS). It provides native functions for spatial bounding boxes (`ST_MakeEnvelope`), coordinate reprojection (`ST_Transform`), spatial clustering (`ST_ClusterDBSCAN`), and direct GeoJSON serialization (`ST_AsGeoJSON`). Furthermore, PostgreSQL enforces ACID compliance and strict foreign key relationships between user accounts, video ingestion runs, and detection audit records.
* **Traceability:** Aligns with **US-01**, **US-05**, **AC-02.1**, and System Security Constraints.

---

### Decision 4: Standardized RFC 7946 GeoJSON & REST API vs. Proprietary File Exports

* **Context & Problem:** The system must export roadway damage data for ingestion into external municipal systems, such as the City of Cincinnati Digital Transformation Office (DTO), Office of Performance and Data Analytics (OPDA), and Cincinnati Area Geographic Information System (CAGIS).
* **Alternatives Considered:**
  1. *Direct Database-to-Database Replication:* Grant external city systems direct read-only SQL connection access to the StreetSmart PostgreSQL database.
  2. *Custom CSV / ESRI Shapefile Batch Dumps:* Generate scheduled file exports in proprietary CSV or zipped Shapefile formats for manual download.
  3. *Authenticated REST API with RFC 7946 GeoJSON (Chosen):* Expose secure, authenticated HTTPS REST endpoints delivering standard RFC 7946 GeoJSON FeatureCollections with bounding-box and date-range filtering.
* **Evaluation & Rationale (Why Chosen Option Won):** Direct database access introduces severe security vulnerabilities, bypasses application-level authentication, and breaches municipal firewall protocols. Scheduled file dumps are static, error-prone, and require manual data handling by city personnel. REST endpoints delivering standardized RFC 7946 GeoJSON provide instantaneous, friction-free interoperability. Modern GIS platforms (ArcGIS Enterprise, QGIS) and web dashboards consume GeoJSON streams natively without custom schema transformation, directly fulfilling **US-05** and enabling the Digital Transformation Office to integrate StreetSmart with minimal friction (**US-01**).
* **Traceability:** Aligns with **US-01**, **US-05**, **AC-02.1**, **AC-02.2**, and Security Constraints.

---

### Decision 5: Dedicated Pre-Persistence Privacy Filter (PII Redaction) vs. Post-Hoc / On-Demand Blurring

* **Context & Problem:** Municipal surveillance and data privacy regulations strictly mandate that vehicle dashcam imagery of public roadways must not retain personally identifiable information (PII), specifically readable vehicle license plates and visible pedestrian faces (**US-04**).
* **Alternatives Considered:**
  1. *Full Video Pre-Anonymization:* Blur all faces and license plates across every raw video frame before feeding the footage into the pothole detection model.
  2. *On-Demand Dynamic Blurring:* Store unredacted reference crops in the database and apply blurring algorithms dynamically when a user requests an image through the web UI or API.
  3. *Pre-Persistence Ingestion Pipeline Privacy Filter (Chosen):* Execute computer vision detection on the raw frame crops first, apply an automated PII blurring filter to the reference image crop during the Ingestion Pipeline stage, and persist only the redacted image artifact.
* **Evaluation & Rationale (Why Chosen Option Won):** Full video pre-anonymization degrades computer vision inference performance because blurring algorithms can inadvertently blur road surface textures or potholes located near vehicle bumpers, lowering detection recall. On-demand dynamic blurring creates significant legal and compliance exposure: storing unredacted citizen imagery on persistent disks violates municipal data governance policies, and an API breach would expose raw citizen PII. The chosen approach processes detections with full visual fidelity, then immediately strips and blurs all sensitive PII from the evidence crop in the Ingestion Pipeline before any byte is written to persistent storage. This guarantees that unredacted PII is never stored or exposed, fully complying with municipal compliance standards (**US-04**).
* **Traceability:** Aligns with **US-04**, Ethical Constraints, and Security Constraints.
