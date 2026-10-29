---
type: deliverable
date: 2026-10-29
version: "0.9"
aliases:
  - Technical Specification
  - Assignment 9
tags:
  - senior-design
  - design
---
# StreetSmart: Technical Specification

**Project:** StreetSmart: Automated Public Infrastructure Damage Detection and Geospatial Reporting System
**Team Members:** Advait Vagerwal, Sahil Thakare, Raihan Rafeek
**Course:** CS 5001 - Computer Science Senior Design
**Advisor:** Eric Jamison
**Assignment:** Assignment 9 - Technical Specification Document
**Document Version:** 0.9 (draft for advisor review, Oct 30, 2026)
**Traces to:** [Requirements Document](Requirements_Document.md) **v0.9**

---

# 1. Version and Change Log

| Version | Date | Change | Author |
| --- | --- | --- | --- |
| 0.9 | 2026-10-29 | First full draft. Consolidates D0, D1, D2 (Draft 1.3 plus peer-review actions), and the Week 8 plan. Traces to Requirements Document v0.9. | Raihan Rafeek |
| 0.9 | 2026-10-29 | Design changes since the Week 7 review, with reasons: (a) the write endpoints `POST /api/v1/detections` and `PATCH /api/v1/runs/{id}` are removed from §3.2 and I7 is the only write path (PR-12; still listed in D1 §5.1 and D2 §2.9, which must be updated); (b) the Backend API and Go inference worker supersede D0's FastAPI and `asyncpg` wording (D1 §6.2 chose Go and Gin); (c) static hosting follows D1 §6.3 (Vercel or GitHub Pages), not D0's NGINX; (d) Authentication is owned by Sahil (PR-10). | Raihan Rafeek |

# 2. Architecture Summary

StreetSmart has seven components, shown in the [D0 Block Diagram](Design_Diagrams/D0_Block_Diagram.svg) and the [D0 Data Flow Diagram](Design_Diagrams/D0_Data_Flow_Diagram.svg); the data model is in the [D1 ERD](Design_Diagrams/D1_Data_Model_ERD.svg). **Model Training** (Advait) fine-tunes a YOLO detector and exports it, with a manifest and checksum, to **Trained Model Storage**. **Model Inference** (Raihan, Go with ONNX Runtime) loads that model, decodes a recorded video one frame at a time, and sends detections of 0.70 confidence or higher to the **Ingestion Pipeline** (Sahil). The pipeline matches each detection to a GPS fix from the recorded NMEA track, blurs faces and plates in the evidence crop, uploads the crop to Supabase Storage, and writes the record to the **PostgreSQL/PostGIS Database** (Raihan), which matches it to an existing pothole within 5.0 m or creates one. The **Backend API** (Raihan, Go with Gin) reads from the database and serves GeoJSON to the **Current Infrastructure Map** (Sahil, React) and, through an API key, to **City Systems**.

**Deployment model.** Processing is batch, not real time (D0 Decision 1). The inference worker and ingestion pipeline run in one Docker container on a workstation or low-cost server and talk over a local Unix socket (I6). The Backend API runs in its own Docker container. The database and image bucket are hosted by Supabase. The React app is built to static files and hosted on a free static host. GitHub Actions builds and tests images on each pull request. **Data flow:** video and GPS → detections → located, redacted records → database → API → map or city export. A detection with no GPS location stops at the pipeline and is never stored (REQ-03).

# 3. Interfaces and Data Formats

## 3.1 Component boundaries

Interface IDs are from D0; contents are as revised in D2 §2.13. All errors from the API use RFC 7807 (§3.3).

| ID  | Boundary                                | Inputs                                                 | Outputs                                          | Format and protocol                          | Error behavior                                                                                                                          |
| --- | --------------------------------------- | ------------------------------------------------------ | ------------------------------------------------ | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| I1  | Labeled data → Model Training           | `image_files[]`, `annotations[]`, `classes[]`          | `dataset_manifest`, `validated_pairs`            | JPEG, YOLO text; local file I/O              | Skip invalid samples and log; stop if more than 5% are invalid (E-02).                                                                  |
| I2  | Model Training → Trained Model Storage  | `ModelPackage { onnx_model, export_manifest }`         | stored version                                   | ONNX binary, JSON manifest; atomic file move | Gate failure (`METRIC_GATE_FAILED`) or export failure keeps the previous stable model (E-05, E-51).                                     |
| I3  | Trained Model Storage → Model Inference | `ResolveModel(version)`                                | `ModelHandle { version, checksum, tensor_spec }` | ONNX; in-process call                        | Missing file or checksum mismatch: refuse to start, alert (`MODEL_NOT_FOUND`, `MODEL_CHECKSUM_MISMATCH`); 3 read retries for an outage. |
| I4  | Caller → Model Inference                | `InferenceJob { run_id, video_ref }`                   | `RunSummary`                                     | MP4/H.264 file; in-process call              | Corrupt frame: skip and continue. Unreadable video: run `FAILED` (`VIDEO_UNREADABLE`).                                                  |
| I5  | GPS file → Ingestion Pipeline           | NMEA file                                              | `GpsFix { time, lat, lon, fix_quality }[]`       | NMEA 0183 text                               | Bad sentence or fix loss: detection flagged `LOCATION_UNRESOLVED`, logged within 3 s.                                                   |
| I6  | Model Inference → Ingestion Pipeline    | `DetectionEvent` (§3.4)                                | acknowledgement                                  | JSON; Unix domain socket                     | 3 retries, then drop the frame, log its index, count a warning (`IPC_SEND_FAILED`).                                                     |
| I7  | Ingestion Pipeline → Database           | `RecordDetection(DetectionRecord)`                     | `RecordResult` (§3.4)                            | SQL over PostgreSQL wire protocol            | 3 retries with backoff, then local buffer and alert; replay is safe (unique key). Duplicate returns the existing ID.                    |
| I8  | Database → Backend API                  | `FindPotholes(bbox, filters, limit)`, `GetPothole(id)` | `PotholeSummary[]`, `PotholeDetail`              | Parameterized SQL; connection pool           | Timeout or outage: API returns 503 and resets the pool (E-29).                                                                          |
| I9  | Backend API → Map                       | HTTPS GET with bearer JWT                              | RFC 7946 GeoJSON or detail JSON                  | HTTPS (port 443)                             | 400, 401, 403, 404, 429, 503 shown as messages; map keeps last good data and offers Retry (E-37).                                       |
| I10 | Backend API ↔ City Systems              | HTTPS GET with API key                                 | GeoJSON plus export metadata                     | HTTPS, TLS 1.3                               | 400 for bad bbox within 1.0 s; 401 for a missing or revoked key; 403 for the wrong role.                                                |
| B11 | Ingestion Pipeline → Supabase Storage   | redacted JPEG named `run_id/frame_index`               | `image_path`                                     | HTTPS multipart upload                       | 3 retries, then save the detection without an image (`IMAGE_UPLOAD_FAILED`, E-20).                                                      |
| B12 | Backend API → Identity provider         | JWT signing-key request                                | verified claims                                  | HTTPS, JWKS                                  | Provider down: use cached keys while valid, else 503 and block by default (E-33).                                                       |

## 3.2 Endpoint table (Backend API, `/api/v1`)

| Method and path | Purpose | Inputs | Success | Errors | Role | Req |
| --- | --- | --- | --- | --- | --- | --- |
| `GET /potholes` | Potholes in a bbox | `bbox` (required); `min_confidence` (default 0.70); `status` (default `ALL`); `limit` 1 to 500 (default 100) | 200 GeoJSON | 400, 401, 403, 429, 503 | `viewer` | REQ-07, REQ-10 |
| `GET /potholes/{id}` | One pothole with evidence images | `id` (UUID) | 200 detail JSON | 400, 401, 403, 404, 503 | `viewer` | REQ-08, REQ-17 |
| `GET /export/geojson` | City GIS export | `bbox` (required); date range; `limit` up to 500; `format=geojson` | 200 GeoJSON plus `export_meta` | 400, 401, 403, 429, 503 | `exporter` | REQ-09, REQ-10, REQ-16 |

`POST /api/v1/runs`, `POST /api/v1/detections`, and `PATCH /api/v1/runs/{id}` (D1 §5.1, D2 §2.9) are withdrawn from this release (W-05).

## 3.3 Error body (RFC 7807)

```json
{ "type": ".../errors/invalid-spatial-parameter", "title": "Invalid Coordinate Bounding Box",
  "status": 400, "detail": "latitude '94.2000' exceeds [-90.0, 90.0]",
  "instance": "/api/v1/export/geojson?bbox=-84.5,94.2,-84.4,39.1",
  "request_id": "<correlation-id>", "invalid_params": [{ "name": "bbox[1]", "reason": "..." }] }
```

## 3.4 Message payloads and database schema

`DetectionEvent` (I6): `run_id` UUID, `frame_index` int ≥ 0, `frame_timestamp` RFC 3339, `damage_type` "pothole", `model_confidence` float [0, 1], `bbox` float[4], `crop_image` JPEG. `DetectionRecord` (I7): `run_id`, `frame_index`, `detected_at`, `model_confidence`, `damage_type`, `latitude` [-90, 90], `longitude` [-180, 180], optional `image_path`. `RecordResult`: `detection_id`, `pothole_id`, `match_action` (`MERGED`, `CREATED`, `AMBIGUOUS`), `aggregated_confidence`, `observation_count`. Full example: D1 §5.2.

| Table | Columns | Rules and indexes |
| --- | --- | --- |
| `VIDEO_RUN` | `id` PK, `source_video_name`, `started_at`, `processing_status`, `last_frame_index` (PR-11) | status values per D2 Fig. 2.2 |
| `POTHOLE` | `id` PK, `location` geometry(Point, 4326), `aggregated_confidence`, `observation_count`, `status`, `first_detected_at`, `last_detected_at` | GiST on `location`; B-tree on confidence and status; confidence in [0, 1] |
| `DETECTION` | `id` PK, `video_run_id` FK, `pothole_id` FK, `model_confidence`, `detected_at`, `frame_index`, `observed_location` | unique `(video_run_id, frame_index)`; B-tree on both FKs |
| `EVIDENCE_IMAGE` | `id` PK, `detection_id` FK, `storage_path`, `created_at` | row added only after a successful redacted upload |

# 4. Technology Stack

| Layer                           | Choice                                                                                              | Justification                                                                                 |
| ------------------------------- | --------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Detector training               | PyTorch, Ultralytics YOLO                                                                           | Existing trained weights; meets NFR-04 with team skill (CON-04).                              |
| Model interchange and runtime   | ONNX, ONNX Runtime (CUDA, DirectML, or CPU)                                                         | No PyTorch in production; runs on whatever hardware exists (CON-01, CON-06, NFR-01).          |
| Video decoding                  | GoCV / OpenCV 4                                                                                     | Frame-by-frame decode keeps memory low (REQ-01, NFR-01).                                      |
| Backend language and API        | Go, Gin                                                                                             | Small binary, low memory, lets one codebase serve inference and API (CON-04, CON-06, NFR-02). |
| Database                        | PostgreSQL 16 with PostGIS 3.4                                                                      | Foreign keys, transactions, and GiST radius search (REQ-05, NFR-10, NFR-02).                  |
| Hosting for database and images | Supabase (free tier), signed URLs                                                                   | Cheap managed hosting, no server to run (CON-01, REQ-17).                                     |
| Geometry and GeoJSON            | `paulmach/orb`                                                                                      | RFC 7946 output without custom code (REQ-07, REQ-09).                                         |
| Privacy filter                  | Haar cascade or lightweight YOLO face and plate detector (T06 picks; license check)                 | Blurs before storage (REQ-04, NFR-07, CON-02).                                                |
| Authentication                  | Bearer JWT for the map, hashed API keys for city systems; **provider to be chosen in T03 (Oct 30)** | Needed for NFR-06 and CON-02; middleware interface lets it plug in late.                      |
| Front end                       | React, TypeScript, MapLibre GL                                                                      | Type-safe API models; viewport rendering (REQ-11, NFR-03, NFR-09, CON-04).                    |
| Packaging and CI                | Docker, GitHub Actions                                                                              | Repeatable deploy without cloud lock-in (CON-06, NFR-12).                                     |
| Configuration and logs          | Environment variables; structured logs with correlation ID                                          | No secrets in Git (NFR-06); failures traceable (NFR-11).                                      |

# 5. Known Constraints

| ID | Constraint | What it rules out | What it forces |
| --- | --- | --- | --- |
| CON-01 | Economic: cloud compute and storage cost | Always-on GPU servers; per-vehicle edge hardware; storing every frame | Batch processing; stationary-frame filtering; free-tier hosting; one saved evidence image per detection |
| CON-02 | Security: JWT and protected endpoints; minimal personal data | Anonymous endpoints; direct city database access; storing or logging unredacted images | Auth middleware on every route; hashed API keys; redaction before upload; log sanitizer |
| CON-03 | Ethical: false positives and negatives | Presenting a detection as certain; keeping only the maximum score | Stored model confidence; observation counts; `NEEDS_REVIEW` for ambiguous matches |
| CON-04 | Professional: two semesters, team skills | Custom inference engine; own identity system; many damage classes | Proven libraries (Gin, React, Supabase); single-class model; one shared Go codebase |
| CON-05 | Trade-off: coverage against cost | Processing every frame at full rate | A configurable sampling rate (2 to 5 frames per second proposed; T10 sets the default) |
| CON-06 | Hosting: containerized batch deployment | Real-time streaming; vendor-locked cloud services | Docker images; the same migrations on Supabase or local PostGIS |

# 6. Traceability Matrix

Status: **Designed** = specified in D0, D1, or D2; **In progress** = implementation or training has started; **Planned** = design detail still to be written. Test IDs are provisional until the Week 10 test plan confirms them. No row is ORPHANED.

| Req ID | Description | Design Component (D0/D1/D2) | Status | Test Case |
| ------ | ----------- | --------------------------- | ------ | --------- |
| REQ-01 | Detect potholes, keep confidence ≥ 0.70 | Model Inference, `DetectionFilter` (D0 I4, I6; D2 §2.5, E-10) | In progress | TC-01 |
| REQ-02 | Interpolate GPS location within 2 s | Ingestion Pipeline, `GpsSynchronizer` (D0 I5; D2 §1.4 #3, §2.6) | Designed | TC-02 |
| REQ-03 | Flag `LOCATION_UNRESOLVED`, log in 3 s, never store | Ingestion Pipeline (D0 I5; D1 §3.2; D2 §2.6, E-17) | Designed | TC-03 |
| REQ-04 | Blur faces and plates before upload | Ingestion privacy step (D0 Decision 5; D2 §2.6, E-15, E-20; D1 `EVIDENCE_IMAGE`) | Designed | TC-04 |
| REQ-05 | Merge within 5.0 m; `NEEDS_REVIEW` when ambiguous | Database `RecordDetection` (D1 §3.2; D2 §2.8, E-21) | Designed | TC-05 |
| REQ-06 | Aggregated confidence formula | `internal/scoring` (D1 §3.1; D2 §2.8) | Designed | TC-06 |
| REQ-07 | Map query endpoint | Backend API (D0 I8, I9; D1 §5.1; D2 §2.9) | Designed | TC-07 |
| REQ-08 | Pothole detail endpoint | Backend API (D1 §5.1; D2 §2.9) | Designed | TC-08 |
| REQ-09 | GeoJSON export | Backend API (D0 I10, Decision 4; D2 §2.9) | Designed | TC-09 |
| REQ-10 | Reject invalid query with 400 | `SpatialQueryValidator`, `ProblemDetails` (D2 §2.9, E-25, E-26) | Designed | TC-10 |
| REQ-11 | Map display, clusters, filters, record panel | Current Infrastructure Map (D0 I9; D2 §2.7) | Designed | TC-11 |
| REQ-12 | Run lifecycle and resume | `RunController` (D2 Fig. 2.2, §2.6, E-12; PR-11) | Designed | TC-12 |
| REQ-13 | Reject runs whose clocks do not overlap | Ingestion Pipeline clock check (D2 §1.4 #3; PR-03; extends `GpsSynchronizer`) | Planned | TC-13 |
| REQ-14 | One alert per failed run | Notifications (D2 §1.4 #11, E-46 to E-49; section pending, T15) | Planned | TC-14 |
| REQ-15 | Unresolved list in run summary | Ingestion unresolved list (D2 §2.6; PR-09) | Planned | TC-15 |
| REQ-16 | Log each export | Backend API, logging (D2 §2.9, §2.12) | Designed | TC-16 |
| REQ-17 | Signed, expiring image URLs | Backend API, Supabase Storage (D1 §5.3; D2 §2.9) | Designed | TC-17 |
| NFR-01 | 60 min of video in 1,200 s | Model Inference and Ingestion (D0 §5; D2 §2.5; budget in T10) | Designed | TC-18 |
| NFR-02 | Export 500 in 5.0 s; reject in 1.0 s | Backend API, GiST index (D1 §2.4; D2 §2.9) | Designed | TC-19 |
| NFR-03 | Viewport query in 2.0 s | API, request-sequence control (D0 §5; D2 §2.7, E-35) | Designed | TC-20 |
| NFR-04 | Held-out mAP@0.5 > 0.75 | Model Training and Storage (D2 §2.3, §2.4, E-51) | In progress | TC-21 |
| NFR-05 | Median location error ≤ 5 m | `GpsSynchronizer`, forward projection (D2 PR-02; T14) | Planned | TC-22 |
| NFR-06 | Authenticated, role-checked endpoints | `AuthenticateAndAuthorize` (D2 §2.10, E-30 to E-33) | Designed | TC-23 |
| NFR-07 | Redaction ≥ 95% find rate; none skipped | Privacy step, log sanitizer (D2 §2.6, §2.12, E-44) | Designed | TC-24 |
| NFR-08 | 4 of 5 users complete task in 60 s | Current Infrastructure Map (D2 §2.7) | Planned | TC-25 |
| NFR-09 | WCAG 2.1 AA, keyboard, not color alone | Current Infrastructure Map (D0 §6; D2 §2.7 steps 7, 8) | Designed | TC-26 |
| NFR-10 | No duplicate detections or potholes | Unique key, area lock, transaction (D1 §3.1; D2 §2.8, E-18, E-19, E-22) | Designed | TC-27 |
| NFR-11 | No record lost in a database outage | Local buffer and replay (D0 I7; D2 §2.6 step 8, E-24) | Designed | TC-28 |
| NFR-12 | Versioned API paths | `/api/v1` prefix (D1 §5.4; D2 §2.13) | Designed | TC-29 |
| CON-01 | Economic | Batch design (D0 Decision 1); sampling setting (D2 §2.11) | Designed | TC-30 |
| CON-02 | Security | Auth and privacy design (D0 Decision 5; D2 §2.10, §2.6) | Designed | TC-31 |
| CON-03 | Ethical | Confidence and matching (D1 §3.1, §3.2) | Designed | TC-32 |
| CON-04 | Professional | Build-versus-reuse table (D1 §4) | Designed | TC-33 |
| CON-05 | Coverage/cost trade-off | Sampling rate setting (D2 §2.5, §2.11; T10) | Planned | TC-34 |
| CON-06 | Hosting | Docker and Supabase (D1 §6.5; D0 §6) | Designed | TC-35 |

CON rows are verified by inspection of the named design element; their TC entries are checklist items in the Week 10 plan.

# 7. Advisor Review

| Item | Record |
| --- | --- |
| Reviewer | Eric Jamison |
| Date | Friday, October 30, 2026 (scheduled; draft sent beforehand) |
| Discussed | Pending. To be filled in after the meeting with what was actually discussed. |
| Changes produced | Pending. Each change will be listed with the section edited and the new version number. |

Items to bring: the matrix (§6), the NFR thresholds, and the MoSCoW lists from the Requirements Document, plus open items A-02, A-07, and A-08 there.
