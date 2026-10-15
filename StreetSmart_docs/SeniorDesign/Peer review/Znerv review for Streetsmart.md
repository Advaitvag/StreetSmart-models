# Peer Review Critique: StreetSmart D2 (Draft 1.3)

**Reviewed document:** StreetSmart: Detailed System Design (D2), Draft 1.3, October 13, 2026
**Team reviewed:** Advait Vagerwal, Sahil Thakare, Raihan Rafeek
**Criteria:** Completeness, Feasibility, Clarity, Risk

## Overall Impression

This is a strong draft. The edge-case register is thorough and covers all four categories for every component. The privacy-first ordering (blur before upload, withhold the image rather than store it unredacted) is consistently reasoned. The interface review in §2.13 does exactly what the assignment asks: it names a concrete leak in each D0 interface and fixes it.

Most of our feedback falls into three groups:

- A missing glue component and a set of broken cross-references, which a grader will notice quickly.
- One privacy hole that contradicts the design's own central rule.
- Geolocation accuracy assumptions that may not hold with consumer dashcam and GPS hardware.

Suggested priorities are ours; the team should assign owners and due dates.

## Completeness

**C1. Notifications has no component section.** §1.3 promises "shared services (configuration, authentication, logging, notifications)." E-46 to E-49 name handlers such as `NotificationDispatcher`, and §4.2 lists "Operational notifications" as a component. However, there is no §2.x giving it a data model, behavior, or interface. The assignment explicitly requires glue components to get the same treatment. Several components already say "notify operator," so there must be a defined interface behind that.
*Suggested action:* Add a Notifications section with:
- Data model: "no persistent data," or a dedup cache.
- Behavior: dedup, severity routing, delivery retry.
- Interface: for example, `Notify(event NotificationEvent) error`, with its error table.

*Priority:* must-fix.

**C2. The peer review notes section (§6) is missing.** §1.3 says D2 includes "a template for the peer review notes (§6)," but the document ends at §5. Per the assignment, §6 is also 20% of the grade.
*Priority:* must-fix (the team likely planned this, but flag it).

**C3. `RunSummary` and `DetectionRecord` are never defined.** `ProcessVideo` returns a `RunSummary`, and I7 takes a `DetectionRecord`, but neither type's fields are listed. §2.6 lists the fields sent to the database, but it is not clear that this list is `DetectionRecord`. Without these definitions, I4 and I7 are not complete interface specifications.
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

**C6. Figure 2.1 omits several error paths the text defines.** The diagram is missing:
- the "keep only the top candidate per frame" step,
- `DETECTION_INVALID` rejection,
- the stationary-period filter,
- IPC send failure (E-50), and
- `BUFFER_FULL` leading to a FAILED run.

Because this is the figure that satisfies "at least one diagram shows error paths," it should include the riskiest failures.
*Priority:* worth considering.

## Clarity

**CL1. Cross-references point to sections that don't exist.** This is the fastest fix and the most visible problem:

| Where | Says | Should probably be |
|---|---|---|
| §1.2 conventions, §2.3 I2, NFR-MAINT-01 | §2.14 (interface revisions) | §2.13 |
| §2.9 endpoint table | §2.15 (D2 additions) | nonexistent |
| §1.4 #7 | §2.16 | nonexistent |
| §2.7 step 2 | §1.4 #10 (severity filter) | the table ends at #9 |

*Priority:* must-fix.

**CL2. The edge-case column in the table under Figure 2.1 is mostly wrong.**
- "Missing GPS location" cites E-15, but E-15 is redaction failure.
- "Database write failure" cites E-32 and E-33, which are authentication cases. The correct reference is E-24.
- "Authentication and key validation" cites E-50, which is the IPC socket failure. The correct references are E-30 to E-33.

The traceability rubric explicitly rewards rows that cite edge-case IDs and figures, so incorrect citations here hurt.
*Priority:* must-fix.

**CL3. §1.4 #6 contradicts the rest of the design.** The open-questions table says the team is "leaning towards top 10 confident predictions." Meanwhile:
- §2.5 step 8 keeps only the single highest-confidence candidate.
- §2.8 enforces a unique constraint on `(video_run_id, frame_index)`.

Moving to top-10 would break the constraint, the duplicate check, and E-19. Either state that the current design is one-per-frame and that top-k would require a new key (for example, adding a candidate index), or decide now.
The wording also needs cleanup:
- "This is up to debate" should read "This is open for debate."
- In #2, "We are discussion with stakeholders" should read "We are in discussion with stakeholders."

*Priority:* must-fix.

**CL4. Ownership of run status is ambiguous, and PENDING_REPLAY conflicts with continued processing.**
- §2.5 step 11 says inference sets the run to `PENDING_REPLAY`, but database outages are detected by ingestion.
- Figure 2.2 moves RUNNING to PENDING_REPLAY when the database becomes unreachable, but §2.6 step 8 says to "keep processing." A run that is still processing frames should not be in a non-running state.

*Suggested action:* Enter PENDING_REPLAY only after all frames are processed with records still buffered, and name one component as the owner of status transitions.
*Priority:* worth considering.

**CL5. Several thresholds have names but no values:** frame sampling rate, stationary-speed limit, signed-URL lifetime, grid-cell size for the area lock, and local buffer size. Proposed defaults would make the design testable next week, even if they are tagged "to validate."
*Priority:* worth considering.

**CL6. AC-01.2's "log within 3 s" has no defined start point.** In a batch system, 3 seconds from the frame's recording time is meaningless. The clock should probably start when ingestion receives the `DetectionEvent`. State this explicitly so the test is unambiguous.
*Priority:* worth considering.

## Feasibility

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

**F5. API key revocation requires a restart.** API key hashes live in the secret store, and configuration is loaded once at startup and frozen. Revoking a key, which E-32 handles, therefore requires a service restart. Clarify whether key hashes are re-read periodically.
*Priority:* worth considering.

## Risk

**R1. The unresolved list may store unredacted images on the worker's disk.** The pipeline resolves location before redaction (step 4 before step 5, by design per rationale #3). A detection that fails location lookup is added to the unresolved list "for reprocessing." If that entry includes `crop_image`, an unredacted image is now persisted on local disk. That contradicts NFR-PRIV-01 and D0 Decision 5 ("an unblurred image is never stored").
*Suggested action:* Either store only metadata in the unresolved list and regenerate the crop from the video on reprocessing, or redact before writing to the list.
*Priority:* must-fix. This is the most serious issue we found, because privacy is the design's central guarantee.

**R2. Clock skew between video and GPS is unaddressed.** Frame times are computed from `VIDEO_RUN.started_at`, which §1.4 #3 already questions. Dashcam clocks often drift or are set to local time rather than UTC. A constant offset will not trigger `LOCATION_UNRESOLVED`, because the fixes still fall within 2 s of the wrong time. It will silently misplace every detection in the run.
*Suggested action:* Add a sanity check, such as comparing GPS-derived speed with visual motion, or require an offset calibration step per run.
*Priority:* must-fix.

**R3. NEEDS_REVIEW records can multiply without bound.** Every ambiguous case creates a new `NEEDS_REVIEW` pothole. If that new pothole is also a match candidate, the next pass through the same cluster has even more candidates, stays ambiguous, and creates another one. Repeated drives down one street could produce a growing pile of duplicates, which undermines US-02 and the observation counts.
*Suggested action:* Define whether `NEEDS_REVIEW` potholes are match candidates, and consider attaching ambiguous detections to an existing `NEEDS_REVIEW` record instead of creating a new one each time.
*Priority:* must-fix.

**R4. The REPAIRED status is unreachable.** Status editing is out of scope (US-03 gap), and no endpoint changes pothole status. `REPAIRED` therefore exists in the schema with no way to set it. Either remove it from the prototype's allowed values or note that it will only be set manually in the database during testing.
*Priority:* worth considering.

**R5. Result limits can silently truncate data.**
- The map defaults to 100 results. A zoomed-out city view would quietly show 100 of possibly thousands of potholes, and client-side clustering would make the coverage look complete.
- The export caps at 500 with no stated behavior when more exist.

*Suggested action:* Return a total count or a `truncated: true` flag in the response and export metadata, and show "showing 100 of N" on the map.
*Priority:* worth considering.

## Traceability

**T1. The POST detections endpoint may be scope creep.** The reverse check in §4.2 says every component traces to a requirement. However, `POST /api/v1/detections` and `PATCH /api/v1/runs/{id}` serve "remote workers and testing," and §1.4 #7 already questions whether they stay. Trace them to a requirement or mark them as candidates to cut.
*Priority:* worth considering.

**T2. The mAP release gate and model versioning have no requirement row.** The gate (mAP@0.5 > 0.75) and the versioning lifecycle are significant design elements, but they trace only loosely to US-01 and AC-01.1. If a D0 requirement covers detection accuracy, cite it. If not, that gap should be stated.
*Priority:* worth considering.

## Rationale

**RA1. Mark review-driven changes.** No rationale entries are marked as changed by the peer review yet, which is expected for a pre-review draft. Remember to add the marks after applying these items, since the rubric checks for them.

**RA2. Consider adding entries for the open decisions.** Two more rationale entries would strengthen the section: one-detection-per-frame versus top-k, and blocking unlocated detections versus storing them with a flag. Both have real alternatives and trade-offs. The section would still be within the 6 to 10 limit.

## Summary for the Team

The criterion that drew the most feedback was **Risk/Feasibility**, specifically geolocation accuracy (F1, F2, R2) and privacy handling of unresolved detections (R1).

The top two issues we raised:

1. **R1:** Unredacted crops may be persisted in the unresolved-location list, contradicting the design's own privacy rule.
2. **F1 and R2:** The geotag records the vehicle's position at a possibly misaligned timestamp, not the pothole's location. This could defeat 5 m matching across passes.

The quickest wins are C1, CL1, CL2, and CL3. These are mostly editing, and they remove the issues a grader is most likely to spot first.

The uploaded PDF seems to be missing page 4, the top of Figure 2.1. Check C6 and CL2 against your full copy before sending.