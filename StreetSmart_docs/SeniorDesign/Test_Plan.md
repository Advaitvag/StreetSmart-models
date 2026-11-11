---
type: deliverable
date: 2026-11-10
version: "1.0"
aliases:
  - Test Plan
  - Assignment 10
tags:
  - senior-design
  - testing
---
# StreetSmart: Test Plan

**Team Members:** Advait Vagerwal, Sahil Thakare, Raihan Rafeek | **Course:** CS 5001 | **Advisor:** Eric Jamison | **Prepared by:** Raihan Rafeek
**Version:** 1.0 (Nov 10, 2026) | **Traces to:** [Requirements Document](Requirements_Document.md) v0.9 and [Technical Specification](Technical_Specification.md) v0.9
**Change log:** 0.9 (2026-11-10) First draft. Test IDs change from TC-01 style to TC-01.1 style so each Must has three cases. 1.0 (2026-11-10) Environment pinned. Compound cases split (TC-05.4, TC-23.3 to 23.5, TC-30.1 to 35.1). Fail conditions and review rules added. Technical Specification matrix and version log updated to match.

# 1. Scope

All 14 Musts and the Shoulds in the Technical Specification matrix are tested this cycle. Each owner writes the cases for their component.

| Component | Owner | Requirements tested |
| --- | --- | --- |
| Model Training and Model Storage | Advait | NFR-04 |
| Model Inference | Raihan | REQ-01, NFR-01 |
| Ingestion Pipeline (GPS, privacy, run control) | Sahil, Advait | REQ-02, REQ-03, REQ-04, REQ-12, REQ-13, NFR-05, NFR-07, NFR-11 |
| PostgreSQL/PostGIS Database | Raihan | REQ-05, REQ-06, NFR-10 |
| Backend API and Authentication | Raihan, Sahil | REQ-07, REQ-08, REQ-09, REQ-10, REQ-16, REQ-17, NFR-02, NFR-03, NFR-06 |
| Current Infrastructure Map | Sahil | REQ-11, NFR-08, NFR-09 |

**Not tested this cycle, with reasons:**

- W-01 to W-09 are Won't items (Requirements §7). A second pothole per frame is a known limitation (E-52). ONNX Runtime, OpenCV, PostGIS, Supabase, MapLibre and the identity provider are vendor tested.
- REQ-14, REQ-15 and NFR-12 are Could items. Notifications has no D2 section (A-10) and the unresolved list has no lifecycle yet (T21). IDs TC-14.1, TC-15.1 and TC-29.1 are reserved.
- The 5.0 m, 2.0 m, 1.5 m and 5 m location values may change after T14 (A-04). Changes from the Oct 30 advisor review are pending in the Technical Specification (§7). Both may change this scope.

# 2. Verification and Validation Strategy

**Verification** checks the product against the spec. The team does this for every requirement using the method in the Requirements Document (Test, Demonstration, Analysis or Inspection). **Validation** checks the product against stakeholder needs. Eric Jamison acts as the real user for the City of Cincinnati. He validates US-01 and US-02 at the M3, M7 and M9 demos, runs the NFR-08 walkthrough and gives the M11 sign-off. No municipal stakeholder is available yet (A-09).

| Layer | Approx. count | Coverage focus |
| --- | --- | --- |
| Unit | 8 | Single rules with stubbed input: confidence cutoff, GPS interpolation, scoring formula, query validation, model gate |
| Integration | 31 | Matching and duplicates, API endpoints, authentication, privacy failures, outage and resume |
| System | 15 | Detector score, throughput, API timing, redaction rate, location error on real video |
| Acceptance | 3 | Map demonstration, usability walkthrough, accessibility audit |
| Inspection | 6 | CON-01 to CON-06 |

| Part | Variable | Metric | Tolerance | Trials |
| --- | --- | --- | --- | --- |
| Detector | Model on held-out set D-1 | mAP@0.5 | Above 0.75 | One run and one reproduction by a second member. Go port count against `infer.py` on one 5-minute clip, within 5% |
| GPS | Assigned location against surveyed pothole (D-6) | Median distance | 5 m or less | Two routes, both directions (T11) |
| Redaction | Labeled crops D-4 | Find rate, added time | 95% or more, 30% or less | Whole labeled set |
| Throughput | Sampling rate from T10 | Seconds per 60 minutes | 1,200 s or less | One 5-minute benchmark and one 60-minute run |

# 3. Success Criteria

| ID | Metric | Target | How measured | Req. |
| --- | --- | --- | --- | --- |
| M-01 | Stored detections under 0.70. Detection at exactly 0.70 | 0 stored. 0.70 kept | SQL count after TC-01.2 | REQ-01 |
| M-02 | Detection count against Python | Within 5% | D-2 rows against `infer.py` | REQ-01 |
| M-03 | Detections with a coordinate or the unresolved flag | 100% | Run summary against detections found | REQ-02 |
| M-04 | Unresolved detections | Logged within 3 s with 422. 0 stored. 0 returned | Logs, SQL, API responses | REQ-03 |
| M-05 | Stored images with a visible face or plate. Redaction find rate. Added time | 0. 95% or more. 30% or less | Review of every bucket image and D-4 | REQ-04, NFR-07 |
| M-06 | Correct match action per candidate case, including 5.0 m | 100% | `match_action` in `RecordResult` | REQ-05 |
| M-07 | Aggregated confidence for mean 0.90, n = 3 | 0.855 ± 0.001 | Call scoring function | REQ-06 |
| M-08 | Map query defaults and export validity | 0.70, limit 100, maximum 500. RFC 7946 valid. Count equals database | Seed D-5, validator, SQL | REQ-07, REQ-09 |
| M-09 | Invalid query handling | One 400 with RFC 7807 body per rule. 0 queries. 0 cache bytes | Responses, query log, cache size | REQ-10 |
| M-10 | Time for 60 minutes of 1080p video | 1,200 s or less | Wall clock on target workstation | NFR-01 |
| M-11 | 500-record export. Invalid-parameter response. Viewport query | 5.0 s or less. 1.0 s or less. 95th percentile 2.0 s or less | 20 timed runs, 100 requests | NFR-02, NFR-03 |
| M-12 | Held-out mAP@0.5 | Above 0.75 (0.75 fails) | D-1, reproduced by second member | NFR-04 |
| M-13 | Median location error | 5 m or less | Analysis of D-6 | NFR-05 |
| M-14 | Negative authentication tests. Plain text API keys | 100% pass on staging. 0 | Test results, store inspection | NFR-06 |
| M-15 | First-time users who find a pothole and open its image. Axe violations | 4 of 5 within 60 s. 0 critical or serious | Walkthrough, axe, keyboard | NFR-08, NFR-09 |
| M-16 | Duplicate detections and potholes. Records lost in an outage | 1 per `(run, frame)`, 0 duplicate potholes from 4 workers. 0 lost, 0 duplicated | SQL counts | NFR-10, NFR-11, REQ-12 |

# 4. Test Cases

Every status starts as Not Run. Data sets D-1 to D-8 are in section 5. A stub is a fixed test input in place of a real component. Any result other than the Expected Result is a Fail. A face is visible when its eyes and mouth can be told apart at full image size and a plate is visible when any character can be read. Two members review each image and either one finding a visible face or plate is a Fail. T numbers are tasks in the Task List and Project Plan, A numbers are in Requirements §9 and E numbers are in D2 §3.

| ID | Description | Steps | Expected Result | Status |
| --- | --- | --- | --- | --- |
| TC-01.1 | Detect and store (REQ-01) | 1) Run D-2 with the stable model. 2) Count `DETECTION` rows. 3) Count `infer.py` detections on D-2 | Go count within 5% of Python count. Fail: difference above 5% | Not Run |
| TC-01.2 | Cutoff edge case (REQ-01) | 1) Stub scores 0.69, 0.70, 0.71 in three frames. 2) Query `DETECTION` | Rows for 0.70 and 0.71 only. Fail: a row for 0.69 or no row for 0.70 | Not Run |
| TC-01.3 | Unreadable video (REQ-01) | 1) Submit a path to a file that does not exist. 2) Submit D-2 cut to its first 1 KB. 3) Read run status after each | Both FAILED with `VIDEO_UNREADABLE`, 0 rows. Fail: COMPLETED | Not Run |
| TC-02.1 | Interpolation (REQ-02) | 1) Valid fixes at 10 s and 11 s. 2) Detection at 10.5 s | Midpoint of the two fixes. Fail: any other coordinate | Not Run |
| TC-02.2 | Nearest fix (REQ-02) | 1) Mark the later fix invalid. 2) Detection 1 s after the earlier fix | Location equals the earlier fix | Not Run |
| TC-02.3 | No fix in range, edge (REQ-02) | 1) Nearest valid fix is 2.5 s away. 2) Submit detection | `LOCATION_UNRESOLVED` and no coordinate. Fail: a coordinate is assigned | Not Run |
| TC-03.1 | Null GPS (REQ-03) | 1) Run the D-3 null-GPS video with 3 detections. 2) Read the log and `DETECTION` | 3 entries with 422, each within 3 s, and 0 rows. Fail: late entry or any row | Not Run |
| TC-03.2 | Corrupted NMEA, edge (REQ-03) | 1) Replace every NMEA sentence from 30 s to 40 s of a D-3 track with random text. 2) Run detections at 20 s, 35 s, 50 s | 35 s is `LOCATION_UNRESOLVED`. 20 s and 50 s each have a coordinate | Not Run |
| TC-03.3 | Never returned (REQ-03) | 1) After TC-03.1 call `GET /api/v1/potholes` and `GET /api/v1/export/geojson` for the route. 2) List the bucket | None appears in either response or the bucket. Fail: any appears | Not Run |
| TC-04.1 | Blur applied (REQ-04) | 1) Pass the D-4 crops through the privacy step and upload. 2) Two members review every stored image | 0 visible faces or plates by the rule above. Fail: one or more | Not Run |
| TC-04.2 | Redaction fails (REQ-04) | 1) Stub redaction to return invalid output twice. 2) Submit one detection | Stored, no image, no `EVIDENCE_IMAGE` row. Fail: image or row exists | Not Run |
| TC-04.3 | Upload fails, edge (REQ-04) | 1) Point storage at an unreachable address. 2) Submit one detection | Detection stored without image after 3 retries and `IMAGE_UPLOAD_FAILED` logged | Not Run |
| TC-05.1 | New pothole (REQ-05) | 1) On empty D-5 submit one detection | `CREATED` and observation count 1 | Not Run |
| TC-05.2 | Exactly 5.0 m, edge (REQ-05) | 1) Seed one pothole. 2) Submit a detection exactly 5.0 m away | `MERGED` and count 2. Fail: `CREATED` | Not Run |
| TC-05.3 | Clear nearest (REQ-05) | 1) Seed potholes 1.8 m and 3.5 m from the detection. 2) Submit it | `MERGED` into the 1.8 m pothole | Not Run |
| TC-05.4 | Ambiguous, edge (REQ-05) | 1) Seed potholes 1.8 m and 2.5 m from the detection. 2) Submit it | `AMBIGUOUS` and a new pothole with status `NEEDS_REVIEW`. Fail: `MERGED` | Not Run |
| TC-07.1 | Defaults (REQ-07) | 1) Seed over 100 potholes at 0.70 or higher in one box. 2) `GET /api/v1/potholes?bbox=...` only | 100 features, each with id, `[lon, lat]`, confidence, count, status, dates | Not Run |
| TC-07.2 | Maximum (REQ-07) | 1) Seed over 500 potholes in one box. 2) Call with `limit=500` | Exactly 500 features | Not Run |
| TC-07.3 | Empty box, edge (REQ-07) | 1) Query a box with no potholes | Status 200 and an empty FeatureCollection | Not Run |
| TC-09.1 | Export (REQ-09) | 1) Call `GET /api/v1/export/geojson` as `exporter` with box and dates. 2) Run an RFC 7946 validator. 3) Count matching rows | Valid and count equals rows. Fail: validator error or mismatch | Not Run |
| TC-09.2 | No match, edge (REQ-09) | 1) Export a box with no records | Valid empty collection and a notice | Not Run |
| TC-09.3 | At maximum (REQ-09) | 1) Seed exactly 500 matches. 2) Export | All 500 returned | Not Run |
| TC-10.1 | Latitude range (REQ-10) | 1) Call the export with `bbox=-84.5,94.2,-84.4,39.1` | 400 and an RFC 7807 body naming `bbox[1]` | Not Run |
| TC-10.2 | Each rule (REQ-10) | 1) Send longitude 181, min above max, a non-numeric value, `limit=0` and `limit=501` to both `GET /api/v1/potholes` and `GET /api/v1/export/geojson` | All 10 return 400 naming the parameter. Fail: any other status | Not Run |
| TC-10.3 | No side effects, edge (REQ-10) | 1) Note export cache size and enable database query logging. 2) Send the 10 requests of TC-10.2 | 0 queries and 0 bytes added to the cache | Not Run |
| TC-18.1 | Stage benchmark (NFR-01) | 1) Run a 5-minute clip at the T10 sampling rate. 2) Record each stage time | Projected time for 60 minutes is at most 1,200 s | Not Run |
| TC-18.2 | Full run (NFR-01) | 1) Run D-7 on the target workstation. 2) Time start to COMPLETED | At most 1,200 s. Fail: above 1,200 s | Not Run |
| TC-18.3 | Top rate, edge (NFR-01) | 1) Repeat TC-18.2 at 5 frames per second | At most 1,200 s | Not Run |
| TC-19.1 | Export time (NFR-02) | 1) Seed 500 matches. 2) Time 20 exports | All 20 within 5.0 s. Fail: any above | Not Run |
| TC-19.2 | Reject time (NFR-02) | 1) Time 20 requests with invalid latitude | All 20 return 400 within 1.0 s | Not Run |
| TC-19.3 | During ingestion, edge (NFR-02) | 1) Start a run that is writing detections. 2) Time 20 exports of 500 records | All 20 within 5.0 s | Not Run |
| TC-21.1 | Release gate (NFR-04) | 1) Evaluate the published model on D-1 | mAP@0.5 above 0.75. Fail: 0.75 or lower | Not Run |
| TC-21.2 | Reproduction (NFR-04) | 1) A second member repeats TC-21.1 from the repository | Score within 0.01 of TC-21.1 and above 0.75 | Not Run |
| TC-21.3 | Exactly 0.75, edge (NFR-04) | 1) Submit a candidate model scored 0.75 | `METRIC_GATE_FAILED` and the stable pointer unchanged. Fail: the model is promoted | Not Run |
| TC-23.1 | No credential (NFR-06) | 1) Call `GET /api/v1/potholes`, `GET /api/v1/potholes/{id}` and `GET /api/v1/export/geojson` with no credential. 2) Call the first over HTTP | 401 from all 3 and HTTP refused. Fail: any 200 | Not Run |
| TC-23.2 | Wrong role (NFR-06) | 1) Call `GET /api/v1/export/geojson` with a `viewer` token | 403 | Not Run |
| TC-23.3 | Expired token, edge (NFR-06) | 1) Call `GET /api/v1/potholes` with an expired token | 401 | Not Run |
| TC-23.4 | Revoked key, edge (NFR-06) | 1) Revoke an API key. 2) Call `GET /api/v1/export/geojson` with it | 401 and the key ID is logged without the key | Not Run |
| TC-23.5 | Keys stored hashed (NFR-06) | 1) Issue an API key. 2) Search the secret store and logs for the key text | 0 matches. Only a hash is stored. Fail: any match | Not Run |
| TC-24.1 | Find rate (NFR-07) | 1) Run the D-4 crops through the privacy step. 2) Count labeled faces and plates found | At least 95% found. Fail: below 95% | Not Run |
| TC-24.2 | Added time (NFR-07) | 1) Time 100 frames with redaction off, then on | Rise of at most 30% | Not Run |
| TC-24.3 | Bucket audit, edge (NFR-07) | 1) Submit D-4 crops as detections, redaction stubbed to fail on every third. 2) List the bucket. 3) Review each image | Images equal crops minus failed, 0 visible. Fail: extra image or visible face or plate | Not Run |
| TC-27.1 | Resubmitted frame (NFR-10) | 1) Submit one `(run, frame)` twice | 1 row and the second call returns the existing ID. Fail: 2 rows | Not Run |
| TC-27.2 | Concurrent workers (NFR-10) | 1) Start 4 workers. 2) Each submits 100 detections of one spot with unique frames | 1 pothole and its count equals accepted detections. Fail: 2 or more potholes | Not Run |
| TC-27.3 | Replay, edge (NFR-10) | 1) After TC-27.2 resubmit every detection | All counts unchanged | Not Run |
| TC-06.1 | Confidence formula (REQ-06) | 1) Mean 0.90, n = 3. 2) Add the same `(run, frame)` again | 0.855 ± 0.001 and n stays 3 | Not Run |
| TC-08.1 | Detail (REQ-08) | 1) Call `GET /api/v1/potholes/{id}` with a known ID, an unknown UUID and `abc` | 200 with images, then 404, then 400 | Not Run |
| TC-11.1 | Map (REQ-11) | 1) Load D-5 in the map. 2) Zoom out. 3) Set a confidence filter. 4) Open a `NEEDS_REVIEW` record | Pins cluster, the filter changes the visible set and a text label shows | Not Run |
| TC-12.1 | Resume (REQ-12) | 1) Stop a D-2 run halfway and resume it. 2) Compare counts with an uninterrupted run | Equal counts and 0 duplicates | Not Run |
| TC-13.1 | Clock mismatch (REQ-13) | 1) Run D-8. 2) Count `DETECTION` rows for the run and read the log | 0 rows and a log entry that the time ranges do not overlap. Fail: any row | Not Run |
| TC-16.1 | Export log (REQ-16) | 1) Run one export. 2) Read the log | One entry with caller ID, time and record count | Not Run |
| TC-17.1 | URL expiry (REQ-17) | 1) Open an image URL. 2) Open it again after expiry | Opens the first time and returns an error the second | Not Run |
| TC-20.1 | Viewport time (NFR-03) | 1) Time 100 viewport queries that return 100 features | 95th percentile at most 2.0 s | Not Run |
| TC-22.1 | Location error (NFR-05) | 1) Process D-6. 2) Measure the distance to each surveyed pothole | Median at most 5 m | Not Run |
| TC-25.1 | Usability (NFR-08) | 1) Five first-time users find a pothole by status filter and open its image, timed, with no help | At least 4 of 5 within 60 s | Not Run |
| TC-26.1 | Accessibility (NFR-09) | 1) Run axe. 2) Repeat the TC-25.1 task by keyboard only. 3) Check status cues | 0 critical or serious violations, task completed and no status by color alone | Not Run |
| TC-28.1 | Database outage (NFR-11) | 1) Stop the database mid-run. 2) Restart it after the run ends. 3) Compare counts | 0 lost, 0 duplicates | Not Run |
| TC-30.1 | CON-01 Economic | Inspect the batch design and the sampling setting | Both exist as described in the Technical Specification | Not Run |
| TC-31.1 | CON-02 Security | Inspect auth middleware on every route and redaction before upload | Both exist | Not Run |
| TC-32.1 | CON-03 Ethical | Inspect that confidence is stored and `NEEDS_REVIEW` exists | Both exist | Not Run |
| TC-33.1 | CON-04 Professional | Inspect the build-versus-reuse table in D1 §4 | Table exists and matches the code | Not Run |
| TC-34.1 | CON-05 Trade-off | Inspect that the sampling rate is a configuration value | Value is read from configuration | Not Run |
| TC-35.1 | CON-06 Hosting | Inspect the Docker images and the migrations on Supabase | Both exist | Not Run |

# 5. Test Environment

Versions below come from the Technical Specification §4 first, then the repo (`backend/go.mod`). Items marked **TBC** have an owner and a date and are recorded in the test report header when each run starts.

**Software versions.**

| Item | Version | Source |
| --- | --- | --- |
| Containers and database | Docker images for the worker and the API. PostgreSQL 16 with PostGIS 3.4, same migrations on local Docker and Supabase | Tech Spec §2 and §4 |
| Hosting and identity | Supabase free tier for Database, Storage and Auth, region US East. Supabase Auth is the identity provider (closes A-02) | Tech Spec §4, team decision |
| Backend | Go 1.25, Gin 1.12, `onnxruntime_go` 1.36 | `backend/go.mod` |
| Model runtime | ONNX opset 17, input 1×3×640×640, ONNX Runtime with the CUDA execution provider (closes A-01) | Tech Spec §4, team decision |
| Video, web and transport | GoCV with OpenCV 4, React with TypeScript and MapLibre GL, HTTPS with TLS 1.3 for city export | Tech Spec §4 and I10 |
| Test tools | An RFC 7946 validator and axe | Test Plan §3 |
| Exact ONNX Runtime, CUDA, NVIDIA driver, OpenCV, Node, axe and validator versions | **TBC**, Advait (runtime, CUDA, driver) and Sahil (Node, axe, validator), by M4 (Dec 18) | Read from the built image and lockfiles |

**Hardware.**

| Role | Machine | Used for |
| --- | --- | --- |
| Target workstation (A-01) | One team PC with an RTX 3060, a 16-core CPU and 32 GB RAM, running the Docker worker with the CUDA provider. Which PC and its OS and driver version are **TBC**, Advait, by M4 (Dec 18) | TC-18.1 to 18.3, TC-19.3, TC-24.2. Always the same machine, so timings are comparable |
| Team development machines | Each member's own computer running Docker | Unit and integration cases only. No timing case runs here |
| Capture device | A OnePlus phone (model and Android version **TBC**, Sahil, by M3 Dec 4) recording video with GPS | D-6 field drive and the pilot |
| Browsers | Chromium based only for now, Chrome and Edge, current stable. Firefox and Safari are not tested this cycle | TC-11.1, TC-25.1, TC-26.1 |

**Network conditions.** Staging runs against Supabase in US East from a normal broadband connection. Flaky network is tested on purpose. Tests that need it are TC-04.3 (unreachable storage), TC-28.1 (database stopped mid-run) and TC-12.1 (interrupted run). Throttling and packet loss are applied with a network shaper on the worker host. Default profiles are 5% packet loss and 300 ms added latency, plus a full drop for 30 s (profile values **TBC**, Sahil, by M5 Jan 8). The pilot drive uses the phone's mobile data only for upload after the drive, because processing is batch.

**Data sets.** D-1 is the held-out labeled image set, free of Cincinnati 311 imagery (NFR-04). D-2 is a 5-minute labeled clip with its NMEA track and the Python reference count (REQ-01, REQ-12). D-3 is a set of NMEA tracks with gaps, bad fixes, null and corrupted data (REQ-02, REQ-03). D-4 is a set of labeled crops with faces and license plates (REQ-04, NFR-07). D-5 is a seeded database with known coordinates, including a pair at 5.0 m and a pothole with neighbors at 2.5 m and 3.5 m (REQ-05, REQ-07, REQ-09, REQ-11). D-6 is the field-drive recording with hand-surveyed pothole coordinates (NFR-05, NFR-07). D-7 is a 60-minute 1080p MP4 with an NMEA track (NFR-01). D-8 is a video with the camera clock shifted from GPS time (REQ-13).

# 6. Pass and Fail Criteria

**Per test.** Pass when every result matches the expected result and meets section 3. Fail when any result differs or a threshold is missed. Boundaries follow the requirement text, so exactly 0.70 is kept, exactly 5.0 m merges and exactly 0.75 mAP fails. Blocked means a component or data set is not ready and the reason is logged. Every Fail becomes a GitHub Issue with an owner (T19) and is rerun after the fix.

**Whole plan.** The plan succeeds when all 45 Must cases Pass and every metric for a Must requirement is met. Those are M-01 to M-06, M-08 to M-10, M-12, M-14, the NFR-02 part of M-11 and the NFR-10 part of M-16. Metrics for Should requirements are M-07, M-13, M-15, the NFR-03 part of M-11 and the NFR-11 and REQ-12 part of M-16. Each of these, and every Should case, must Pass or have an accepted gap with a reason, as T24 requires. The plan fails if any Must case is Fail or Blocked at M10 or any defect against a Must remains open.

# 7. Schedule

Core flows and data integrity are tested first, so matching and duplicates are checked at M5 before the API and map are built on them. Until CI exists (T17, Feb 19) tests run locally.

| Milestone | Test activity | Owner | Evidence |
| --- | --- | --- | --- |
| M1, Nov 6 (date has passed, outcome not yet recorded here) | Held-out score (TC-21.x) and database migrations | Advait, Raihan | Score log, checksum, migration log |
| M2, Nov 20 | GPS unit tests (TC-02.x, TC-03.x), Go against Python (TC-01.1) | Sahil, Raihan | Test output, checked by Advait |
| M3, Dec 4 | Privacy and clock check (TC-04.x, TC-24.x, TC-13.1) | Advait, Sahil | Bucket listing, live demo to advisor |
| M4, Dec 18 | Throughput benchmark (TC-18.1) | Advait | Results, checked by Raihan |
| M5, Jan 8 | Matching, duplicates, outage, resume (TC-05.x, TC-06.1, TC-27.x, TC-28.1, TC-12.1) | Raihan, Sahil | Integration run, checked by Advait |
| M6, Jan 22 | API cases (TC-07.x, TC-08.1, TC-09.x, TC-10.x) | Raihan | Validator output, checked by Sahil |
| M7, Feb 5 | Location accuracy (TC-22.1), map demo (TC-11.1) | Advait, Sahil | Error report, live demo |
| M8, Feb 19 | Security, logs, URLs, retrain gate (TC-23.x, TC-16.1, TC-17.1, TC-21.x) | Sahil, Advait | Negative test results, green CI |
| M9, Mar 12 | Performance, usability, accessibility (TC-19.x, TC-20.1, TC-25.1, TC-26.1) | Raihan, Sahil | Test report, advisor review |
| M10, Apr 2 | End-to-end run of all 14 Musts (TC-18.2, TC-24.3) and regression of 45 Must cases | Advait | T24 report reviewed by all |
| M11, Apr 16 | Constraint inspections (TC-30.1 to 35.1), clean install from runbook | All | Advisor sign-off |

# 8. Definition of Done

**Feature done:** all its cases including the edge case Pass. Another member reviewed the pull request and CI is green. Its matrix row and D2 edge cases are updated. Documentation is updated. No open Issue remains. The owner and reviewer sign off.

**Project done:** all 45 Must cases Pass and each Should case Passes or has an accepted gap. Metrics in section 3 are met or their gaps recorded. The T24 report is reviewed by the other two members and the advisor. No open defects against a Must. The user guide and runbook were followed by a member who did not write them (T23). Assumptions A-01 to A-11 are closed or documented. The matrix has no blank Test Case cell. The advisor signs off at M11.
