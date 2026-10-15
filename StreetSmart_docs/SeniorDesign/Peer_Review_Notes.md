# StreetSmart: Peer Review Notes (D2)

**Project:** StreetSmart: Automated Public Infrastructure Damage Detection and Geospatial Reporting System  
**Team Members:** Advait Vagerwal, Sahil Thakare, Raihan Rafeek  
**Reviewed document:** D2 Detailed System Design, Draft 1.3 (October 13, 2026)  
**Reviewing teams:** Team Znerv, Team Pulse

These are the comments we received from each reviewing team. Comments on wording and formatting, and comments already fixed in Draft 1.4, have been removed. The action items, owners, and due dates are in D2 §6.

---

## Team Znerv

### Overall impression

This is a strong draft. The edge-case register is thorough and covers all four categories for every component. The privacy-first ordering (blur before upload, withhold the image rather than store it unredacted) is consistently reasoned. The interface review in §2.13 does exactly what the assignment asks: it names a concrete leak in each D0 interface and fixes it.

### Completeness

**C1. Notifications has no component section.** §1.3 promises "shared services (configuration, authentication, logging, notifications)." E-46 to E-49 name handlers such as `NotificationDispatcher`, and §4.2 lists "Operational notifications" as a component. However, there is no §2.x giving it a data model, behavior, or interface. The assignment explicitly requires glue components to get the same treatment. Several components already say "notify operator," so there must be a defined interface behind that.

*Suggested action:* Add a Notifications section with:
- Data model: "no persistent data," or a dedup cache.
- Behavior: dedup, severity routing, delivery retry.
- Interface: for example, `Notify(event NotificationEvent) error`, with its error table.

*Priority:* must-fix.

**C4. The unresolved-location list has no lifecycle.** Detections flagged `LOCATION_UNRESOLVED` are "kept in a cache for reprocessing." The design does not say:
- what triggers reprocessing,
- how long items are kept,
- what the size limit is, or
- what happens when the list is full.

The local record buffer has `BUFFER_FULL`; the unresolved list has no equivalent.

*Suggested action:* Add an edge case and either a reprocessing path or an explicit "reprocessing is out of scope; the list is exported in the run summary for manual review."

*Priority:* worth considering.

**C5. Several edge cases are missing from the register:**
- A new detection within 5 m of a `REPAIRED` pothole. Does it merge into the repaired record, reopen it, or create a new pothole?
- Clock offset between the dashcam's recording time and NMEA UTC time. This is a different problem from a GPS gap; see R2.
- Two distinct potholes visible in the same frame. Under the one-detection-per-frame rule, one is silently lost.

*Priority:* must-fix for the first; worth considering for the others.

### Feasibility

**F1. The geotag is the vehicle's position, not the pothole's.** A forward-facing dashcam typically sees a pothole several to 15+ meters ahead of the vehicle. Interpolating GPS to the frame timestamp places the pothole where the car was, not where the damage is. That systematic offset can exceed the 5 m match radius. Passes driven in opposite directions would then place the same pothole at points 10+ m apart and never merge them.

*Suggested action:* Either estimate forward distance from the bounding box position and camera geometry and project along the heading, or document the offset as a known limitation with a test plan.

*Priority:* must-fix (at minimum, document it).

**F2. The disambiguation thresholds are tighter than consumer GPS accuracy.** D1's rule requires the nearest candidate to be within 2.0 m and at least 1.5 m closer than the next. Typical consumer GPS error is roughly 3 to 5 m. Timing error adds to this: at 30 mph, a 0.5 s offset is about 6.7 m. In practice, almost every multi-candidate case will be classified as ambiguous.

*Suggested action:* Collect a small real drive dataset to measure positional spread before locking these numbers.

*Priority:* worth considering.

**F3. The 20-minute processing budget has many serial costs.** Each detection goes through redaction (with one retry), a Supabase upload (with three retries), and a database transaction with area locks, all after inference. The design doesn't say whether these steps are pipelined or concurrent. "The agreed hardware" is also never named. A rough per-stage time budget would help show the target is plausible.

*Priority:* worth considering.

**F4. Resuming after CANCELLED or FAILED repeats work.** Resume behavior relies on the duplicate check, but there is no frame checkpoint. A resumed run would re-decode, re-redact, and re-upload every earlier detection before the database rejects it as a duplicate. This costs time and creates orphan images in storage unless image paths are deterministic.

*Suggested action:* Store the last committed `frame_index` on `VIDEO_RUN`, or name uploads by `run_id/frame_index` so re-uploads overwrite instead of duplicating.

*Priority:* worth considering.

### Risk

**R2. Clock skew between video and GPS is unaddressed.** Frame times are computed from `VIDEO_RUN.started_at`, which §1.4 #3 already questions. Dashcam clocks often drift or are set to local time rather than UTC. A constant offset will not trigger `LOCATION_UNRESOLVED`, because the fixes still fall within 2 s of the wrong time. It will silently misplace every detection in the run.

*Suggested action:* Add a sanity check, such as comparing GPS-derived speed with visual motion, or require an offset calibration step per run.

*Priority:* must-fix.

**R3. NEEDS_REVIEW records can multiply without bound.** Every ambiguous case creates a new `NEEDS_REVIEW` pothole. If that new pothole is also a match candidate, the next pass through the same cluster has even more candidates, stays ambiguous, and creates another one. Repeated drives down one street could produce a growing pile of duplicates, which undermines US-02 and the observation counts.

*Suggested action:* Define whether `NEEDS_REVIEW` potholes are match candidates, and consider attaching ambiguous detections to an existing `NEEDS_REVIEW` record instead of creating a new one each time.

*Priority:* must-fix.

**R4. The REPAIRED status is unreachable.** Status editing is out of scope (US-03 gap), and no endpoint changes pothole status. `REPAIRED` therefore exists in the schema with no way to set it. Either remove it from the prototype's allowed values or note that it will only be set manually in the database during testing.

*Priority:* worth considering.

### Traceability

**T1. The POST detections endpoint may be scope creep.** The reverse check in §4.2 says every component traces to a requirement. However, `POST /api/v1/detections` and `PATCH /api/v1/runs/{id}` serve "remote workers and testing," and §1.4 #7 already questions whether they stay. Trace them to a requirement or mark them as candidates to cut.

*Priority:* worth considering.

---

## Team Pulse

### Completeness

**C1. The number of detections kept per frame contradicts itself.** §1.4 #6 says the team is "leaning towards top 10 confident predictions." But §2.5 step 8 keeps only the highest-confidence box, and §2.8 puts a unique constraint on `(video_run_id, frame_index)`, which makes more than one detection per frame impossible. With the current design, a frame showing two potholes silently loses one. #6 is also the only row in §1.4 with no draft decision.

*Suggested action:* Choose one option. Either keep one detection per frame and record the loss as a known limitation, or allow N per frame. The second option means adding a `detection_index` to the unique key and updating §2.5, §2.8, E-19 and NFR-REL-01 to match.

*Priority:* must-fix.

**C2. Notifications is used throughout but never designed.** "What D2 adds" lists notifications as a shared service. E-46 to E-49 depend on it, §4.2 traces it to requirements, and the error tables keep saying "alert admin" or "notify operator." Yet §2.10–2.12 cover only auth, config and logging. Notifications has no data model, behavior, interface, errors or owner.

*Suggested action:* Add a §2.x Notifications section in the same format as the others: event schema, channel (email or chat), deduplication key, interface signature and error table. Otherwise, state plainly that alerts are only log entries plus run status in the prototype, and remove E-46 to E-49.

*Priority:* must-fix.

### Feasibility

**F1. Nothing in the design shows the 60-min-in-20-min target (AC-01.1) is reachable.** For every detection, the pipeline does ONNX inference, then GPS matching, then a redaction model with a retry, then an upload with up to 3 retries, then a database transaction with a geographic lock. The frame sampling rate is listed in §2.11 but has no value, and the "agreed hardware" is never named. The feasibility of the main acceptance criterion depends on two unknowns.

*Suggested action:* Set a default sampling rate (for example 2–5 fps) and the target hardware (GPU or CPU, which execution provider). Run a short benchmark on a 5-minute clip and add a time budget per stage to §2.5. Also decide whether redaction and upload run asynchronously so they do not block inference.

*Priority:* must-fix.

**F2. The remote-worker write path adds scope a batch prototype does not need.** `POST /api/v1/detections`, `PATCH /api/v1/runs/{id}`, the operator role, per-worker API keys and the 409 retry handling all exist so remote workers can write data. The Ingestion Pipeline already writes directly through I7, and §1.4 #7 says it is undecided whether these endpoints stay.

*Suggested action:* Drop the POST and PATCH endpoints from the prototype and keep I7 as the only write path. Leave a single line in §5 noting that remote workers could be added later.

*Priority:* out of scope for now.

### Risk

**R2. Too much of the work sits with one person.** Raihan owns Inference, Ingestion, the Database, the Backend API, Auth integration, and 6 of the 9 open questions. Sahil owns only the Map, and Advait owns Training and Storage. If Raihan gets stuck, most of the critical path stops. Also, nobody has been named to own the identity provider decision (§1.4 #9), and the whole auth design depends on it.

*Suggested action:* Rebalance ownership. For example, move Auth and the identity provider decision to Sahil, and the Database/PostGIS layer or redaction integration to Advait. Update the owner fields and §1.4.

*Priority:* worth considering.
