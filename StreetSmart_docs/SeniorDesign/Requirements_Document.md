---
type: deliverable
date: 2026-10-29
version: "0.9"
aliases:
  - Requirements Document
  - Assignment 9
tags:
  - senior-design
  - requirements
---
# StreetSmart: Requirements Document

**Project:** StreetSmart: Automated Public Infrastructure Damage Detection and Geospatial Reporting System
**Team Members:** Advait Vagerwal, Sahil Thakare, Raihan Rafeek
**Course:** CS 5001 - Computer Science Senior Design
**Advisor:** Eric Jamison
**Assignment:** Assignment 9 - Requirements Document (companion: [Technical Specification](Technical_Specification.md))
**Document Version:** 0.9 (draft for advisor review, Oct 30, 2026)

---

# 1. Version and Change Log

| Version | Date | Change | Author |
| --- | --- | --- | --- |
| 0.9 | 2026-10-29 | First full draft. Consolidates the Week 4 user stories, D0, D1, D2, the Week 8 plan, and the Week 3 constraints essay. Assigns stable REQ, NFR, and CON IDs. | Raihan Rafeek |
| 0.9 | 2026-10-29 | Design changes since the Week 7 review (D2 peer review, Oct 13), with reasons: (a) the `POST /api/v1/detections` and `PATCH /api/v1/runs/{id}` endpoints and the `operator` API role are dropped, because a batch prototype needs only the I7 write path (PR-12, see W-05), (b) priorities are re-set so that Musts are about half of all requirements (D2 §4 marked 10 of 14 Must), (c) the D2 NFR IDs are replaced by `NFR-##` IDs (mapping in §6.1), (d) NFR-REL-01 is split into NFR-10 and NFR-11 so that the second can be Should, (e) US-05 export is raised from Should to Must, because D2 already treated AC-02.1 and AC-02.2 as Must, and they cannot pass without the export endpoint, (f) ownership of Authentication moved to Sahil (PR-10, Week 8 plan). | Raihan Rafeek |

IDs are stable and never reused. A dropped requirement is marked **withdrawn** and logged here, it is never renumbered.

# 2. Purpose and Scope

**Purpose.** This document states what StreetSmart must do, for whom, and how each statement will be checked. The [Technical Specification](Technical_Specification.md) states how it will be built and traces to this document (v0.9).

**In scope (this release).** A batch prototype. Recorded dashcam video (1080p MP4/H.264) and a matching NMEA GPS track go in. Potholes are detected with an ONNX model, given GPS coordinates, and stored with redacted evidence images in PostgreSQL/PostGIS. City staff view them on a web map. City GIS systems pull them through an authenticated RFC 7946 GeoJSON export. Architecture: [D0 Block Diagram](Design_Diagrams/D0_Block_Diagram.svg).

**Out of scope.** See the Won't list (§8). StreetSmart is a proof of concept, not a production work-order system (D2 §1.1).

# 3. Stakeholders and User Goals (Week 4)

| Stakeholder | Type | Goal | Stories |
| --- | --- | --- | --- |
| City of Cincinnati, Digital Transformation Office (DTO) Division Manager | Primary | Identify damage and integrate reports with existing city systems without friction | US-01 |
| City of Cincinnati, Office of Performance and Data Analytics (OPDA) Manager | Primary | Accurate, reliable damage data for maintenance decisions | US-02 |
| Cincinnati commuters and drivers | Secondary | Severe potholes on major routes repaired promptly | US-03 |
| Municipal data privacy and compliance officer | Hidden | No faces or license plates retained from roadway footage | US-04 |
| City GIS analyst and downstream city systems | Hidden | Verified pothole records in standard GeoJSON, ingestible without custom transformation | US-05 |

# 4. Glossary

Each term is defined once here, the Technical Specification uses these meanings.

| Term | Meaning |
| --- | --- |
| Pothole | One physical road defect, stored as one `POTHOLE` row with a location, aggregated confidence, observation count, and status. |
| Detection | One sighting of a pothole in one video frame (`DETECTION` row), with its model confidence and frame index. |
| Observation count | Number of accepted detections merged into one pothole. |
| Model confidence | The detector's score from 0 to 1 for one detection. |
| Aggregated confidence | The pothole's combined score: 0.70 × mean model confidence + 0.30 × n/(n+1), where n is the observation count (D1 §3.1). |
| Evidence image | A cropped frame with the detection box drawn on it, with faces and license plates blurred. |
| Redaction | Blurring faces and license plates in an evidence image before it is saved. |
| Video run | One processing of one recorded video (`VIDEO_RUN`), with a status (D2 Fig. 2.2). |
| GPS fix | One timed latitude/longitude reading with a fix-quality value, parsed from an NMEA file (NMEA is the text format GPS devices record). |
| `LOCATION_UNRESOLVED` | Flag on a detection with no qualifying GPS fix. Such a detection is never stored or exported. |
| `NEEDS_REVIEW` | Pothole status given to an ambiguous match. Other values: `UNRESOLVED` (default) and `REPAIRED` (set by hand in testing only). |
| Match radius | 5.0 m (inclusive) within which a detection may merge into an existing pothole. |
| Bounding box (bbox) | `min_lon,min_lat,max_lon,max_lat` in WGS84 (EPSG:4326) degrees. |
| Viewport | The map area currently visible to the user. |
| GeoJSON | RFC 7946 text format for map data, coordinates are longitude first. |
| ONNX / ONNX Runtime | Open model file format / the engine that runs it on CUDA, DirectML, or CPU. |
| mAP@0.5 | Detector quality score on a held-out image set (higher is better). |
| Release gate | A model is published only if held-out mAP@0.5 is greater than 0.75. |
| Held-out set | Labeled images never used for training and free of Cincinnati 311 imagery. |
| Target workstation | The machine and execution provider used for the throughput benchmark. Not yet named (A-01). |
| MoSCoW | Priority scheme: Must, Should, Could, Won't (for this release). |
| `viewer` | Signed-in map user who may read potholes and details. |
| `exporter` | A `viewer` who may also call the GeoJSON export (city GIS analyst or city system). |
| Operator | Team member who runs video runs and reads logs. Not an API role in this release. |
| City system | An external municipal system that calls the export with an API key. |

# 5. Functional Requirements

Verification methods: **Test** (automated or scripted), **Demonstration** (run live and observe), **Inspection** (read design or data), **Analysis** (calculate or measure from logs).

| ID | Requirement | Priority | Source | Verification |
| --- | --- | --- | --- | --- |
| REQ-01 | The system shall detect potholes in recorded 1080p MP4/H.264 video of up to 60 minutes and store each detection with its model confidence, keeping confidence of 0.70 or higher (exactly 0.70 is kept) and discarding lower values. | Must | US-01, US-02, AC-01.1 | Test: labeled clip, 0 stored detections below 0.70, Go detection count within 5% of the Python reference on the same 5-minute clip |
| REQ-02 | The system shall assign each kept detection a location by interpolating between the GPS fixes on both sides of its frame time when both are valid and each is within 2 s, otherwise by the nearest valid fix within 2 s. | Must | US-01, AC-01.1 | Test: recorded tracks with gaps and bad fixes, every detection gets a coordinate or the unresolved flag |
| REQ-03 | The system shall flag a detection with no qualifying fix `LOCATION_UNRESOLVED`, log it with status 422 within 3 s, and never write it to the database or return it from any API response. | Must | US-01, AC-01.2 | Test: video with null or corrupted GPS, log entry within 3 s, 0 such rows in the database |
| REQ-04 | The system shall blur every detected face and license plate in an evidence image before upload, if redaction fails or is uncertain after one retry, it shall save the detection with no image. | Must | US-04 | Test: labeled crops, 0 stored images with a visible face or plate |
| REQ-05 | The system shall merge a detection into an existing pothole when exactly one pothole is within 5.0 m, or when the nearest is within 2.0 m and at least 1.5 m closer than the next, with no pothole within 5.0 m it shall create one, in every other case it shall create or attach to a `NEEDS_REVIEW` pothole. Thresholds may change after T14. | Must | US-02 | Test: integration cases for 0, 1, and several candidates, at exactly 5.0 m |
| REQ-06 | The system shall compute each pothole's aggregated confidence as 0.70 × mean model confidence + 0.30 × n/(n+1), within [0, 1], counting each `(run, frame)` once. | Should | US-02 | Test: worked example (mean 0.90, n = 3 gives 0.855 ± 0.001), duplicate frame leaves n unchanged |
| REQ-07 | The system shall return, for `GET /api/v1/potholes` with a valid bbox, an RFC 7946 FeatureCollection of potholes in that box (id, `[lon, lat]`, aggregated confidence, observation count, status, dates), defaulting to `min_confidence` 0.70 and `limit` 100, with a maximum of 500. | Must | US-01 | Test: seeded database, counts and defaults match |
| REQ-08 | The system shall return, for `GET /api/v1/potholes/{id}`, the pothole with its detections' evidence images, `404` for an unknown ID, and `400` for a malformed UUID. | Should | US-02, US-03 | Test |
| REQ-09 | The system shall return, for `GET /api/v1/export/geojson` with a valid bbox and date range, an RFC 7946-valid FeatureCollection containing 100% of matching located records (maximum 500) with coordinates, detection timestamps, and confidence, an empty valid collection plus a notice when none match. | Must | US-05, US-01, AC-02.1 | Test: RFC 7946 validator, record count equals database count |
| REQ-10 | The system shall reject a map or export query with latitude outside [-90, 90], longitude outside [-180, 180], min greater than max, non-numeric values, or `limit` outside 1 to 500, with HTTP 400 and an RFC 7807 JSON body naming the invalid parameter, before any database access and with 0 bytes written to the export cache. | Must | US-05, AC-02.2 | Test: one case per rule |
| REQ-11 | The system shall display potholes for the current viewport on a web map, cluster pins when zoomed out, filter by minimum confidence and status, and open a record panel (confidence, observation count, dates, redacted evidence image), `NEEDS_REVIEW` shall carry a text label, not color alone. | Should | US-01, US-03 | Demonstration on seeded data, filters change the visible set |
| REQ-12 | The system shall track each video run through its lifecycle (D2 Fig. 2.2) and resume a failed or cancelled run from its last committed frame, producing 0 duplicate detections or images. | Should | US-01 | Test: stop a run mid-way and resume, record counts equal an uninterrupted run |
| REQ-13 | The system shall flag or reject, before storing any detection, a run whose video time range does not overlap its GPS track time range. | Should | US-01, AC-01.1 | Test: run with a deliberately shifted camera clock |
| REQ-14 | The system shall send exactly one operator alert (a log entry plus one chat or email channel) for each failed run, suppressing duplicates by event key, with at most 3 delivery retries. | Could | US-01 | Test: one failed run produces one alert |
| REQ-15 | The system shall list every `LOCATION_UNRESOLVED` detection (metadata only, 0 image bytes) in the run summary for manual review. | Could | US-01, AC-01.2 | Inspection of a run summary |
| REQ-16 | The system shall log each export with caller ID, timestamp, and record count. | Should | US-05 | Test: log entry per export |
| REQ-17 | The system shall serve evidence images only through signed URLs that expire (proposed default 15 minutes). | Should | US-04 | Test: expired URL returns an error |

# 6. Non-Functional Requirements

| ID | Requirement | Priority | Source | Verification |
| --- | --- | --- | --- | --- |
| NFR-01 | **Performance.** The system shall process 60 minutes of 1080p video end to end (decode, inference, GPS matching, redaction, upload, database write) in 1,200 s or less on the target workstation. | Must | US-01, AC-01.1 | Test: T10 benchmark, then 60-minute drive in T24 |
| NFR-02 | **Performance.** The system shall deliver a 500-record GeoJSON export within 5.0 s and return the 400 for an invalid parameter within 1.0 s. | Must | US-05, AC-02.1, AC-02.2 | Test: T19, 20 timed runs, all within limit |
| NFR-03 | **Performance.** The system shall answer a viewport query returning the default 100 features within 2.0 s at the 95th percentile of 100 requests. | Should | US-01 | Test: T19 |
| NFR-04 | **Accuracy.** The published detector shall score held-out mAP@0.5 greater than 0.75 (exactly 0.75 fails). | Must | US-02 | Test: T01 held-out evaluation, reproduced by a second member |
| NFR-05 | **Accuracy.** The median distance between an assigned location and the surveyed pothole shall be 5 m or less on the field-drive data. | Should | US-02, AC-01.1 | Analysis: T14 on T11 data |
| NFR-06 | **Security.** The system shall require a valid bearer JWT (map) or API key (city system) on every protected endpoint over HTTPS, returning 401 for a missing or invalid credential and 403 for the wrong role, API keys shall be stored only as hashes. | Must | US-01, CON-02 | Test: T16 negative tests, 100% pass on staging |
| NFR-07 | **Privacy.** The redaction step shall find at least 95% of labeled faces and plates on the test set, add no more than 30% to per-frame time, and 0 stored images shall have skipped redaction. | Must | US-04, CON-02 | Test: T06 test set, storage bucket audit |
| NFR-08 | **Usability.** At least 4 of 5 first-time city staff shall find a pothole by status filter and open its evidence image within 60 s with no help. | Should | US-01 | Demonstration: T20 walkthrough |
| NFR-09 | **Accessibility.** The map shall have 0 open critical or serious axe violations against WCAG 2.1 AA, be fully keyboard-operable, and never show status by color alone. | Should | US-01 | Test: axe plus keyboard and screen-reader pass in T20 |
| NFR-10 | **Reliability.** Resubmitting a `(run, frame)` shall store 1 detection, and 4 concurrent workers submitting 100 detections of the same spot shall create 0 duplicate potholes. | Must | US-02, CON-03 | Test: T08 integration and T19 load tests |
| NFR-11 | **Reliability.** With the database stopped mid-run, the system shall lose 0 records and, after replay, create 0 duplicates. | Should | US-01 | Test: T09 outage test |
| NFR-12 | **Maintainability.** API paths shall carry a version prefix (`/api/v1`), any breaking change shall move to `/api/v2`. | Could | US-01 | Inspection |

**6.1 Old-ID map.** D2 §4 used other IDs: NFR-SEC-01 is NFR-06, NFR-PRIV-01 is NFR-07, NFR-PERF-01 is NFR-03, NFR-REL-01 is NFR-10 and NFR-11, NFR-ACC-01 is NFR-09, NFR-MAINT-01 is NFR-12. AC-01.1 is REQ-01, REQ-02, NFR-01, and NFR-05, AC-01.2 is REQ-03, AC-02.1 is REQ-09 and NFR-02, AC-02.2 is REQ-10 and NFR-02.

# 7. MoSCoW Summary

**Must (14 of 29, 48%):** REQ-01, REQ-02, REQ-03, REQ-04, REQ-05, REQ-07, REQ-09, REQ-10, NFR-01, NFR-02, NFR-04, NFR-06, NFR-07, NFR-10. This is the MVP: video and GPS in, redacted and geotagged potholes stored and exported securely.

**Should (12):** REQ-06, REQ-08, REQ-11, REQ-12, REQ-13, REQ-16, REQ-17, NFR-03, NFR-05, NFR-08, NFR-09, NFR-11.

**Could (3):** REQ-14, REQ-15, NFR-12.

**Won't (this release):** written down so it cannot creep back.

| ID | Won't build | Why |
| --- | --- | --- |
| W-01 | Automated alerts to maintenance teams about severe potholes (US-03) | No severity field, staff find high-confidence potholes through REQ-11 filters (D2 §4.1) |
| W-02 | A severity rating or severity field in exports (US-05) | Not in the D1 schema, confidence is exported instead (D2 §1.4 #10) |
| W-03 | Damage classes other than `pothole` | The model and schema are single-class |
| W-04 | Live, on-vehicle, or streamed inference | Cost and hardware (D0 Decision 1) |
| W-05 | A remote-worker write API: `POST /api/v1/detections`, `PATCH /api/v1/runs/{id}`, `operator` role | Batch prototype writes only through I7 (PR-12) |
| W-06 | Changing pothole status in the API or map, or any work-order workflow | Out of the proof of concept (PR-06) |
| W-07 | Direct city database access, and export formats other than GeoJSON | Security and interoperability (D0 Decision 4) |
| W-08 | More than one detection per frame | Known limitation (E-52, PR-08) |
| W-09 | Live serial GPS input | Recorded NMEA files only (D2 §2.13, I5) |

# 8. Inherited Constraints (Week 3 essay and D0)

| ID | Constraint | Source |
| --- | --- | --- |
| CON-01 | **Economic.** Cloud compute and storage are the main recurring costs, the team has a camera and can borrow a vehicle. Unnecessary inference and storage must be avoided. | Week 3 essay |
| CON-02 | **Security.** Imagery, coordinates, credentials, and detections require JWT-based authentication and protected endpoints, unnecessary personally identifiable information is not retained. | Week 3 essay |
| CON-03 | **Ethical.** The model can give false positives and negatives, so a confidence score is stored and repeat sightings are tracked, letting users judge reliability. | Week 3 essay |
| CON-04 | **Professional.** Machine learning, backend, database, and deployment work must fit a two-semester timeline and the team's skills, so proven technologies are preferred. | Week 3 essay |
| CON-05 | **Trade-off.** Processing more frames improves coverage but raises cost, so the frame sampling rate is a deliberate, configurable setting. | Week 3 essay |
| CON-06 | **Hosting.** Batch processing on workstation or low-cost servers in Docker containers, with no vendor lock-in or per-vehicle hardware. | D0 §6 (derives from CON-01, CON-04) |

# 9. Assumptions and Open Questions

| ID | Assumption or question | Owner | Date |
| --- | --- | --- | --- |
| A-01 | The target workstation and ONNX execution provider are not named, REQ-01 and NFR-01 assume 60 minutes fits in 1,200 s (PR-04). | Advait | 2026-12-18 (T10) |
| A-02 | Identity provider and API-key issuing are undecided, NFR-06 assumes one is chosen (D2 §1.4 #9). | Sahil | 2026-10-30 (T03) |
| A-03 | The video start time equals the camera clock and can be checked against GPS (REQ-13, PR-03). | Sahil | 2026-11-23 (T07) |
| A-04 | The camera's view ahead of the vehicle may put locations more than 5 m from the pothole, so NFR-05 and the 5 m, 2.0 m, and 1.5 m rules (REQ-05) may need new values (PR-02, PR-07). | Advait | 2027-01-29 (T14) |
| A-05 | A face and plate detector exists with a license allowing project use and a miss rate of 5% or less (NFR-07). | Advait | 2026-11-20 (T06) |
| A-06 | Pothole status values and who may change them are unsettled, `REPAIRED` is set by hand in testing only (D2 §1.4 #2, PR-06). | Raihan | 2026-11-06 (T02) |
| A-07 | UC-02 says exported records are "marked synchronized", D1 has no such field. Decide whether to add it or drop that step. | Raihan | 2026-10-30 (advisor meeting) |
| A-08 | Signed-URL expiry (REQ-17), the 95th-percentile basis (NFR-03), and the 4-of-5 usability threshold (NFR-08) are proposed values for advisor confirmation. | Raihan | 2026-10-30 (advisor meeting) |
| A-09 | A municipal stakeholder can join the usability walkthrough, if not, the advisor and a peer team stand in (R11). | Sahil | 2027-02-19 |
| A-10 | Notifications has no D2 section yet, REQ-14 is Could until it is written (PR-01). | Raihan | 2027-01-29 (T15) |
| A-11 | T24 in the plan validates only seven items, it must be widened to the 14 Musts above. | Advait | 2026-11-06 |
