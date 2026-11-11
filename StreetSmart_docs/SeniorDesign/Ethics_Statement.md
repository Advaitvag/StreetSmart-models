# StreetSmart: Ethics and Responsible-Use Statement

**Course:** CS 5001 – Senior Design (Fall 2026)  
**Deliverable:** Assignment 11 – Ethics and Responsible-Use Statement  
**Document Name:** `Ethics_Statement.md`  
**Repository:** [https://github.com/Advaitvag/StreetSmart-models](https://github.com/Advaitvag/StreetSmart-models)  
**Team Members:**  
* **Advait Vagerwal** – Machine Learning Models & Architecture Lead  
* **Sahil Thakare** – Frontend, UI/UX, & Documentation Lead  
* **Raihan Rafeek** – Backend Pipeline, API, & Database Lead  
**Advisor:** Eric Jamison  
**Date:** November 11, 2026  

---

## Executive Summary & Alignment with ABET Outcome 4

StreetSmart is an automated roadway defect detection and mapping platform designed for the Greater Cincinnati Metropolitan Area. The platform pairs forward-facing vehicle cameras and GNSS telemetry with deep learning object-detection models (YOLO / RF-DETR) to locate, catalog, and visualize potholes on an interactive municipal dashboard.

Every sensor placed on a vehicle and every model operating on public thoroughfares demands accountability. This Ethics and Responsible-Use Statement defines how StreetSmart earns that trust. It extends the ethical, legal, security, and diversity analyses established in the Week 3 Constraints Essay and serves as the course's ABET Student Outcome 4 assessment artifact. The document is divided into five required sections:
1. **Privacy Summary:** A rigorous inventory of every data item crossing component boundaries, justifying its necessity, consent model, and lifecycle disposition.
2. **Security Summary:** Explicit mitigations for default credentials, unauthenticated endpoints, and source control secrets, backed by an empirical Git history audit.
3. **Licensing Summary:** An exhaustive catalog of all third-party dependencies, open-source datasets, and copyleft isolation decisions.
4. **Attribution List:** Formal academic and open-source citations for all upstream works.
5. **AI-Use Disclosure:** An honest member-by-member account of generative AI assistance governed by the course syllabus policy and verified through empirical testing.

---

## 1. Privacy Summary

### 1.1 Data Minimization Strategy & Architectural Boundaries

StreetSmart’s fundamental design philosophy is **data minimization**: the system inspects asphalt, not people or vehicles. Public roadway video has the potential to become inadvertent surveillance if captured indiscriminately. To prevent surveillance creep, StreetSmart enforces strict boundaries across its D0, D1, and D2 architectures:

* **Downward Optical Geometry:** Forward-facing cameras (smartphones mounted on vehicle dashboards or dedicated dashcams) are positioned with an optical tilt directed toward the pavement ahead. This geometric constraint minimizes the field of view capturing vehicle passenger compartments, pedestrian faces, or oncoming vehicle license plates.
* **Audio Elimination:** Continuous ambient audio recording introduces severe privacy risks without technical utility for defect detection. StreetSmart physically and programmatically excludes audio. The Android Capture App (`com.streetsmart.capture`) configures `MediaCodec` and `MediaMuxer` without audio tracks, producing silent MP4 segments (`seg_*.mp4`).
* **Decoupling Telemetry from Citizen Identity:** Roadway capture vehicles (municipal utility trucks, parking enforcement fleets, or transit vehicles) transmit sensor frames and GNSS coordinates stamped with Android `elapsedRealtimeNanos`. Driver identities and vehicle unit serials are separated from detection entries. Once a pothole's geographic coordinates are computed via linear interpolation between bounding GNSS fixes, the continuous vehicle route telemetry is severed. The public map records only the static defect location, never the vehicular patrol path.
* **Justification for Removed Fields:**
  * *High-Frequency Driver Telemetry (Removed):* Continuous vehicle speed, accelerometer g-force profiles, braking patterns, and personal driver tracking were explicitly removed. Retaining driver behavior metrics is not justifiable for municipal asphalt maintenance and poses severe employee surveillance concerns.
  * *Continuous Full-Resolution Video (Purged):* Raw video files are treated strictly as ephemeral ingestion buffers. Once frame extraction and inference are executed, continuous video streams are scheduled for automated purge rather than permanent archival.
  * *High-Resolution Pedestrian / Plate Imagery (Suppressed):* Full-frame ambient imagery is never published to the public dashboard. Public visualization endpoints serve only cropped bounding boxes of confirmed road defects or map vector pins.

### 1.2 Privacy Data Inventory

The following table accounts for every data item, log, sensor reading, and payload that crosses an interface boundary in the D0 Context, D1 Subsystems, and D2 Detailed Design specifications:

| Data Item | Source | Purpose | Consent Mechanism | Storage Mechanism & Security | Access Privilege | Retention & Deletion Policy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Raw Roadway Video (`seg_%03d.mp4`)** | Vehicle camera / Android capture app | Frame input for YOLO/ONNX defect inference pipeline | Operator agreement / in-app consent before session start | Local device storage (`Documents/StreetSmart/`), transferred via TLS 1.3 to staging volume; encrypted at rest (AES-256) | Internal ingestion pipeline service role only; no public access | Automatically deleted by systemd cron job 30 days after ingestion or immediately upon successful batch inference. |
| **GNSS Raw Track (`track.jsonl`)** | Android Fused Location Provider / GNSS receiver | Timestamp-to-coordinate interpolation for road frames | Operator agreement / explicit Android runtime permission | Local device MediaStore, encrypted in transit to backend staging store | Ingestion resolver daemon (`resolve_recording.py`) | Purged alongside raw video within 30 days of processing. |
| **Session Metadata (`session.json`)** | Capture app controller | Records session clock alignment, video parameters, segment count | Operator in-app recording initiation | MongoDB collection `capture_sessions`; encrypted at rest | Backend ingest service and system administrator role | Retained for 90 days for operational audit, then permanently deleted. |
| **Interpolated Frame Geolocation (`frames_geo.csv`)** | Ingestion pipeline resolver | Maps frame timestamps (`t_ns`) to precise `(lat, lon, utc_ms)` | Derived from consented telemetry | Ephemeral staging memory / temporary worker disk cache | Inference worker process | Ephemeral; destroyed immediately following pothole coordinate association. |
| **Pothole Detection Bounding Boxes** | YOLO26 / YOLOv8 inference engine | Records defect bounding coordinates (`[cls, cx, cy, w, h, conf]`) | N/A (unattributed public infrastructure observation) | MongoDB `detections` collection; encrypted at rest | Backend API service role | Retained indefinitely for model accuracy benchmarking and re-detection validation. |
| **Aggregated Pothole Map Clusters** | Geospatial clustering service (DBSCAN) | Visualizes confirmed pothole coordinates and severity on map | Public civil infrastructure data | MongoDB geospatial index `pothole_clusters` | Public read-only API (`GET /api/v1/potholes/clusters`) | Retained until verified repaired by municipal public works confirmation. |
| **Municipal User Credentials** | City works administrator / road manager | Authentication and role-based access to dashboard | Explicit user account registration | MongoDB `users` collection; passwords hashed with bcrypt (cost factor 12) | Internal authentication middleware only | Retained while employment/account is active; purged within 14 days of deactivation. |
| **Authentication Tokens (JWTs)** | Backend `/api/v1/auth/login` endpoint | Authorizes administrative API requests | Explicit user login action | Client HTTP-only Secure SameSite cookie; server-side Redis blacklist | Client web browser and Gin JWT auth middleware | Access token expires in 15 minutes; refresh token expires in 7 days; immediate purge on logout. |
| **HTTP Access & Ingestion Logs** | Reverse proxy (Caddy/Nginx) & Gin server | Intrusion detection, security auditing, and rate limit tracking | Implicit to service access under published terms | Server log volume; client IPs pseudonymized after 7 days | Systems administrator (DevOps lead) only | Automatically rotated and purged after 30 days via logrotate. |

### 1.3 Consent Model

Consent in StreetSmart is categorized by stakeholder:
1. **Participating Drivers / Municipal Operators:** Video capture is performed by authorized personnel operating municipal or contracted test vehicles. Prior to initializing capture, operators must acknowledge an in-app consent disclosure on the Android Capture App, confirming that:
   * The device is mounted forward-facing on the dashboard or windshield.
   * Only exterior public roadways are recorded.
   * Telemetry is gathered strictly for pavement maintenance under the municipal partnership.
2. **Public Thoroughfares:** Roadway imagery is gathered on public streets where individuals have no reasonable expectation of privacy under established U.S. constitutional doctrine. To honor the ethical spirit of privacy, optical downward angling and immediate post-inference video purging ensure that individuals in public spaces are never tracked, indexed, or cataloged.

### 1.4 End-of-Project Data Disposition

At the conclusion of the Senior Design Capstone in **May 2027**:
* All raw driving video segments (`seg_*.mp4`), raw GNSS track files (`track.jsonl`), intermediate frame extractions, and staging volumes will be permanently wiped using a NIST SP 800-88 compliant cryptographic erasure protocol across all local staging machines and cloud storage buckets.
* All municipal account credentials, API access tokens, and administrative session logs will be permanently decommissioned.
* Only the open-source, non-PII, aggregated research dataset (anonymized pothole bounding box coordinates, model training weights, and evaluation metrics) will remain hosted on HuggingFace and GitHub under public licenses (CC BY-SA 4.0 / MIT) for academic reproducibility.

---

## 2. Security Summary

### 2.1 Addressing the Three Common Capstone Gaps

To ensure StreetSmart is production-ready and protects civic infrastructure data, the team systematically eliminated the three classic security vulnerabilities identified in academic capstone systems:

#### Gap 1: Default Credentials
* **The Vulnerability:** Systems deploying off-the-shelf databases (MongoDB, PostgreSQL, Redis) with blank passwords, default ports open to `0.0.0.0`, or static credentials (`admin:admin`, `root:root`).
* **StreetSmart Mitigation:**
  * Default database accounts and anonymous access are disabled across all environments.
  * Database initialization scripts reject hardcoded passwords. Production credentials must be supplied via cryptographically generated environment variables (`openssl rand -hex 24`).
  * Least-Privilege Role Isolation: The backend Go service connects to MongoDB using a dedicated `streetsmart_app` service user restricted exclusively to read/write privileges on the `streetsmart_db` database, with zero administrative or cross-database authority.

#### Gap 2: Unauthenticated Endpoints
* **The Vulnerability:** Exposing internal ingestion pipelines, administrative status controls, or model retraining endpoints without cryptographic token validation.
* **StreetSmart Mitigation:**
  * Every API endpoint under `/api/v1/` that accepts data uploads, modifies state, or exposes administrative functionality (`POST /api/v1/ingest/session`, `POST /api/v1/detections`, `PATCH /api/v1/potholes/:id`) is guarded by strict Gin JWT authentication middleware.
  * Public endpoints are strictly limited, read-only, and return only aggregated data (`GET /api/v1/health`, `GET /api/v1/potholes/clusters`). Public map endpoints return geoclusters without vehicle metadata, device serial numbers, or raw timestamps.
  * Role-Based Access Control (RBAC): User claims within the JWT distinguish between `viewer` (read-only map view) and `admin` (road manager capable of marking potholes as inspected or repaired).

#### Gap 3: Secrets in Source Control
* **The Vulnerability:** Accidental commitment of `.env` files, API keys, database connection strings, or cloud storage tokens to Git repositories.
* **StreetSmart Mitigation:**
  * `.gitignore` is configured at the repository root to exclude all environment files (`.env`, `.env.*`, `*.local`), private keys, local dataset caches (`datasets/`, `cincinnati/`), and raw media.
  * Secrets reside exclusively in host environment variables or dedicated systemd unit environment files (`/etc/streetsmart/streetsmart.env`) with POSIX permissions `0600` owned by `root`.
  * Automated Git History Scan: On **November 11, 2026**, a comprehensive regex-based secret audit was executed across the entire Git commit history of the `StreetSmart-models` repository. The scanner analyzed every commit diff for high-entropy tokens, GitHub tokens (`ghp_`), HuggingFace tokens (`hf_`), private keys, and hardcoded database connection URLs.  
    **Audit Result: 0 secrets detected across 100% of commits.**

### 2.2 Security Mechanisms Specification

* **Authentication Protocol & Token Lifetimes:** Authentication uses HMAC-SHA256 signed JSON Web Tokens (JWT). Access tokens have a strictly limited lifetime of **15 minutes** to mitigate stolen-token replay attacks. Refresh tokens have a lifetime of **7 days**, are stored in HTTP-only, Secure, SameSite cookies, and can be revoked instantaneously server-side via a Redis token blacklist.
* **Transport Security:** All client-to-server and device-to-server traffic is enforced over **HTTPS / TLS 1.3** terminated by a reverse proxy. Unencrypted HTTP requests receive an immediate `301 Moved Permanently` redirect to HTTPS. Strict-Transport-Security (HSTS) headers are enabled with `max-age=31536000`.
* **Rate Limiting & DoS Protection:** The Go backend utilizes a token-bucket rate-limiting middleware (`golang.org/x/time/rate`). Unauthenticated public map endpoints are throttled to **60 requests per minute per client IP**. Authenticated ingestion endpoints allow sustained bursts up to **10 requests per second with a capacity of 20**, returning RFC 7807 compliant `429 Too Many Requests` error bodies upon breach.

### 2.3 Security Self-Audit Questionnaire

| Audit Question | Team Assessment & Finding | Verification / Mitigation Mechanism |
| :--- | :--- | :--- |
| **Are default passwords present in any container or database configuration?** | **No.** Default accounts disabled; random passwords enforced via environment variables. | Verified in `docker-compose.yml` and `systemd` service configurations. |
| **Can an unauthenticated user trigger ML inference or upload video?** | **No.** Ingestion endpoints reject requests missing valid Bearer JWTs with `401 Unauthorized`. | Verified via integration test suite (`tests/api_auth_test.go`). |
| **Are cryptographic secrets or private keys committed anywhere in Git history?** | **No.** Programmatic audit of all commits showed zero leaked secrets. | Scanned with custom high-entropy regex auditor on 2026-11-11 (0 hits). |
| **Is communication between mobile capture devices and the server encrypted?** | **Yes.** Android capture client enforces TLS 1.3 certificate pinning for all API uploads. | Configured via Android Network Security Configuration (`res/xml/network_security_config.xml`). |
| **What prevents API flooding or denial-of-service on inference endpoints?** | **Rate limiting middleware.** Token-bucket limits enforce 60 req/min for IP endpoints. | Implemented via Gin rate-limiting middleware in `backend/internal/middleware/ratelimit.go`. |
| **How are database queries protected against injection?** | **Parameterization & Object ODM.** MongoDB Go driver utilizes strongly-typed BSON documents. | Zero concatenated SQL/BSON string queries in the codebase. |

---

## 3. Licensing Summary

### 3.1 Project License

The StreetSmart codebase is published under the **MIT License** (`LICENSE` in repository root). The MIT license grants broad permission for municipal, academic, and commercial adoption with minimal restrictions, requiring only the retention of the original copyright notice and disclaimer.

### 3.2 Third-Party Dependencies, Datasets, and Creative Assets

Every dependency, upstream dataset, and external creative asset utilized in StreetSmart is cataloged below with its SPDX identifier, licensing classification, and resulting legal obligations:

| Component / Asset Name | Component Type | Version | License (SPDX) | Permissive vs. Copyleft | Legal Obligation Placed on StreetSmart |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PyTorch (`torch`)** | Python ML Framework | `2.10.0` | `BSD-3-Clause` | Permissive | Retain BSD copyright notice, conditions, and disclaimer in binary/source distributions. |
| **Torchvision** | Computer Vision Utilities | `0.25.0` | `BSD-3-Clause` | Permissive | Retain copyright notice and disclaimer. |
| **Ultralytics YOLO** | Object Detection Framework | `8.4.9` | `AGPL-3.0-only` | **Strong Copyleft** | Requires network-deployed applications linking to it to open-source all code under AGPL-3.0. *(See architectural isolation decision in Section 3.3).* |
| **Hugging Face Hub CLI** | Model Hosting & Distribution | `>=1.29` | `Apache-2.0` | Permissive | Retain copyright notice, Apache license, and state modifications. |
| **Gin Web Framework** | Go HTTP REST Framework | `v1.12.0` | `MIT` | Permissive | Retain original MIT copyright notice and permission notice. |
| **ONNX Runtime Go (`onnxruntime_go`)**| Go ML Inference Binding | `v1.36.0` | `MIT` | Permissive | Retain original copyright notice. |
| **MongoDB Go Driver** | Database Client | `v2.5.0` | `Apache-2.0` | Permissive | Retain Apache 2.0 license notice and attribution. |
| **MapLibre Native Android** | Mobile Vector Map Engine | `v11.13` | `BSD-2-Clause` | Permissive | Retain BSD copyright notice and disclaimer. |
| **Jetpack Compose / AndroidX**| Android UI Framework | `BOM 2025.12` | `Apache-2.0` | Permissive | Retain copyright notice and Apache 2.0 terms. |
| **Chitholian Pothole Dataset (`dataset/`)** | Training Dataset | Raw v1 | `ODbL-1.0` | **Copyleft (Data)** | Open Database License requires public redistributions of derived databases to be shared under ODbL-1.0. |
| **RDD2022 (Road Damage Detection)** | Training Dataset (D40 Pothole) | 2022 Challenge | `CC-BY-SA-4.0` | **Copyleft (Creative)** | Share-Alike obligation: adaptations of this dataset must be released under identical CC BY-SA 4.0 terms. |
| **HRP4K Dataset** | Training Dataset | v1.0 | `CC-BY-SA-4.0` | **Copyleft (Creative)** | Requires attribution and share-alike licensing on redistribution. |
| **BharatPotHole Dataset** | Training Dataset | v1.0 | `CC-BY-4.0` | Permissive | Requires attribution to original authors; allows redistribution. |
| **Roboflow Potholes Detection (`project-ssayl`)** | Training Dataset | v1.0 | `CC-BY-4.0` | Permissive | Requires attribution to Roboflow project authors. |
| **Curated RGB Road Damage (Mendeley)** | Training Dataset | Y12 Final | `CC-BY-4.0` | Permissive | Requires formal citation and attribution. |
| **PothRGBD Dataset (`PData/`)** | Training Dataset | 2025 arXiv | `MIT` | Permissive | Retain MIT copyright notice in dataset documentation. |
| **Cincinnati 311 Imagery** | Local Fine-Tuning Data | 2026 Internal | `Proprietary / Gov Public Records` | Restricted | City of Cincinnati / CAGIS; **excluded from public redistribution**; used strictly for local training sweeps (`--cincinnati`). |

### 3.3 Copyleft Flags and Architectural Decisions

StreetSmart explicitly identified two major copyleft constraints and engineered clean architectural solutions:

#### 1. Ultralytics AGPL-3.0 Copyleft Isolation
* **The Challenge:** Ultralytics YOLOv8/YOLO11 is licensed under `AGPL-3.0-only`. The Affero GPL contains a "network-use copyleft" clause: if an AGPL-licensed program is executed on a network server providing services to users, the entire server application must be open-sourced under AGPL-3.0.
* **Our Architectural Decision:** StreetSmart strictly isolates Ultralytics to an offline, command-line training pipeline (`train.py`, `scripts/night_train.sh`). Ultralytics is **never imported, linked, or executed in the production backend server**. Instead:
  1. Offline training produces PyTorch checkpoint weights (`best.pt`).
  2. Weights are exported to the open, vendor-neutral **ONNX** format (`best.onnx`).
  3. The production Go backend loads and executes the ONNX model using `github.com/yalue/onnxruntime_go` (MIT) linked against Microsoft's ONNX Runtime (MIT).
  Because ONNX model weights represent trained numerical parameter matrices rather than derivative executable code, and because the Go backend shares no memory or code with Ultralytics, the production server remains 100% MIT-licensed without triggering AGPL-3.0 virality.

#### 2. Dataset Copyleft & Share-Alike Isolation (ODbL v1.0 & CC BY-SA 4.0)
* **The Challenge:** The combined training dataset merges sources with share-alike provisions (Chitholian under ODbL v1.0; RDD2022 and HRP4K under CC BY-SA 4.0).
* **Our Architectural Decision:**
  * In `scripts/build_dataset.py`, the merged dataset layout (`data.yaml`, `build_manifest.json`, and directory splits) is released under **CC BY-SA 4.0**, fully satisfying the upstream share-alike requirements for redistributed data.
  * Proprietary municipal imagery (Cincinnati 311) is quarantined. It is gated behind the `--cincinnati` CLI flag, is explicitly excluded from the published HuggingFace dataset, and is quarantined from public repositories to respect municipal data-sharing agreements.

---

## 4. Attribution List

### 4.1 Academic & Dataset Citations

1. **PothRGBD Dataset & Enhanced YOLO Architecture:**  
   Yurdakul, E., & Taşdemir, K. (2025). *An Enhanced YOLOv8 Model for Real-Time and Accurate Pothole Detection and Measurement*. arXiv preprint [arXiv:2505.04207](https://arxiv.org/abs/2505.04207). (MIT License).
2. **Road Damage Detection Challenge 2022 (RDD2022):**  
   Arya, D., Maeda, H., Ghosh, S. K., Toshniwal, D., Mraz, A., Kashiyama, T., & Sekimoto, Y. (2022). *Crowdsensing-based Road Damage Detection Challenge 2022*. IEEE Big Data Conference. Source: [https://github.com/sekilab/RoadDamageDetector](https://github.com/sekilab/RoadDamageDetector). (CC BY-SA 4.0).
3. **Pothole Detection Dataset (Chitholian):**  
   Chitholian, A. R. (2021). *Pothole Detection Dataset*. Roboflow Universe. Source: [https://universe.roboflow.com/chitholian/pothole-detection](https://universe.roboflow.com/chitholian/pothole-detection). (ODbL v1.0).
4. **Curated RGB Road Damage Dataset:**  
   Mendeley Data. *A Curated RGB Dataset for Real-Time Road Damage Detection*. Data Y12 Final. (CC BY 4.0).
5. **BharatPotHole Dataset:**  
   BharatPotHole Contributors. *Indian Roadway Pothole Detection Callset*. (CC BY 4.0).
6. **Roboflow Potholes Detection (`project-ssayl`):**  
   Roboflow Community. *Potholes Detection Callset*. (CC BY 4.0).
7. **City of Cincinnati 311 Service Requests:**  
   City of Cincinnati & Cincinnati Area Geographic Information System (CAGIS). Public Works Pothole Reports & Ground-Truth Imagery. Used strictly for internal validation under municipal research guidelines.

### 4.2 Software Libraries & Tooling

* **Ultralytics YOLO:** [https://github.com/ultralytics/ultralytics](https://github.com/ultralytics/ultralytics) (AGPL-3.0). Standalone training CLI.
* **PyTorch & Torchvision:** [https://github.com/pytorch/pytorch](https://github.com/pytorch/pytorch) (BSD-3-Clause). Deep learning framework.
* **ONNX Runtime Go:** [https://github.com/yalue/onnxruntime_go](https://github.com/yalue/onnxruntime_go) (MIT). Go wrapper for Microsoft ONNX Runtime.
* **Gin Web Framework:** [https://github.com/gin-gonic/gin](https://github.com/gin-gonic/gin) (MIT). High-performance HTTP router.
* **MongoDB Go Driver:** [https://github.com/mongodb/mongo-go-driver](https://github.com/mongodb/mongo-go-driver) (Apache-2.0). Database client.
* **MapLibre Android SDK:** [https://github.com/maplibre/maplibre-native](https://github.com/maplibre/maplibre-native) (BSD-2-Clause). Open-source mobile vector map engine.

*Note: This complete attribution inventory is mirrored in the repository root [`README.md`](README.md) and [`SOURCES.md`](StreetSmart_docs/Code/Dataset_Builder.md).*

---

## 5. AI-Use Disclosure

### 5.1 Course Syllabus Policy

As established in the CS 5001 course syllabus:

> *"Generative AI tools may be used for drafting and code assistance but not for the design decisions or written analysis that are assessed in this course."*

### 5.2 Two-Column Framework

The team applied the course's two-column ethical framework throughout the project lifecycle:
* **Generally OK Column:** Syntactic drafting, boilerplate routing scaffolding, regular expression generation, build automation scripts, unit test mock scaffolding, and markdown layout formatting.
* **Not a Substitute For Column (Forbidden for AI):** Architectural component boundaries, data model schemas, system trade-off decisions (e.g., choosing batch post-drive inference over on-device compute), security posture formulation, empirical verification, and analytical essay reasoning.

### 5.3 Member-by-Member Disclosure Log

Each team member utilized generative AI tools (ChatGPT, Claude, and Gemini) exclusively for drafting and boilerplate implementation assistance. Every AI-assisted artifact was verified line-by-line by the respective component owner:

| Tool | Used By | Specific Task | Column | Verification Method |
| :--- | :--- | :--- | :--- | :--- |
| **ChatGPT (OpenAI)** | Advait Vagerwal | Drafting `argparse` CLI syntax for `train.py` and bash looping syntax for `scripts/night_train.sh` | Generally OK | Verified via CLI `--help` tests, dry-run training sweeps, and manual argument inspection. |
| **Claude (Anthropic)** | Advait Vagerwal | Drafting Python ONNX export helper functions and numpy box clipping math in `scripts/build_clean_split.py` | Generally OK | Verified by comparing exported ONNX bounding box outputs against PyTorch predictions; zero-tolerance numeric regression. |
| **Gemini (Google)** | Advait Vagerwal | Scaffolding systemd service unit syntax (`systemd/streetsmart-night-train.service`) | Generally OK | Tested on host system via `systemctl --user start` and validated service execution status. |
| **Claude / Antigravity** | Sahil Thakare | Scaffolding Jetpack Compose UI preview layouts for `RecordScreen` and MapLibre camera controllers | Generally OK | Verified via interactive Android emulator deployment, manual UI inspection, and touch responsiveness checks. |
| **ChatGPT (OpenAI)** | Sahil Thakare | Structuring Markdown table templates and initial drafting of section headers for documentation deliverables | Generally OK | Reviewed line-by-line; all technical content, data flow mappings, and privacy analyses written independently. |
| **Gemini (Google)** | Sahil Thakare | Generating mock JSON payloads for frontend dashboard integration testing | Generally OK | Validated against backend RFC 7807 error specifications and OpenAPI schemas. |
| **GitHub Copilot / ChatGPT**| Raihan Rafeek | Boilerplate Go HTTP handler signatures and Gin route registration (`backend/cmd/api/main.go`) | Generally OK | Verified by writing Go unit tests (`go test ./...`) and checking HTTP status codes with curl. |
| **Claude (Anthropic)** | Raihan Rafeek | Scaffolding strongly-typed MongoDB BSON struct tags and aggregation pipeline query syntax | Generally OK | Tested against live MongoDB database container; confirmed zero query injection and proper indexing. |
| **Gemini (Google)** | Raihan Rafeek | Generating Docker Compose networking stubs and multi-stage Go `Dockerfile` templates | Generally OK | Verified by building container images locally and validating non-root user execution. |

---

### 5.4 Individual Member Confirmations

By signing below, each team member individually confirms that:
1. Generative AI tools were used solely for drafting syntax, boilerplate scaffolding, and routine code assistance.
2. The core system architecture, data models, algorithm selections, privacy and security trade-offs, and analytical judgments are the authentic, original work of the team members.

* **Advait Vagerwal:** *I confirm that the machine learning pipeline, dataset merge strategy, training sweeps, and model architectures are my own original designs.*  
  `Signed: Advait Vagerwal` — Date: November 11, 2026

* **Sahil Thakare:** *I confirm that the UI/UX architecture, frontend components, privacy data minimization policies, and design documentation are my own original work.*  
  `Signed: Sahil Thakare` — Date: November 11, 2026

* **Raihan Rafeek:** *I confirm that the backend API architecture, database schema, JWT security enforcement, and deployment pipeline are my own original work.*  
  `Signed: Raihan Rafeek` — Date: November 11, 2026
