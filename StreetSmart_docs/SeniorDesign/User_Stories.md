---
type: deliverable
aliases:
  - User Stories
  - Assignment 4
tags:
  - senior-design
  - requirements
---

# Assignment 4 - User Stories and Use Cases

## Team Members

1. Advait Vagerwal
2. Sahil Thakare
3. Raihan Rafeek

## Stakeholder Map

| Category  | Stakeholder                                              | Need                                                                                                                                                           |
| --------- | -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Primary   | City of Cincinnati (Digital Transformation Office & OPDA)| Identify, locate, and prioritize potholes and other public infrastructure damage while integrating StreetSmart's data with existing city systems and workflows |
| Secondary | Cincinnati Residents and Drivers                         | Benefit from safer, better-maintained roads and fewer vehicle hazards through prompt, prioritized road repairs                                                  |
| Hidden    | Municipal Data Privacy and Compliance Officers           | Ensure roadway footage captured by vehicle cameras complies with municipal surveillance and privacy regulations by redacting personally identifiable information |
| Hidden    | Downstream Systems & City GIS Teams                      | Integrate standardized geographic pothole datasets directly into existing municipal mapping, work-order, and asset-management databases                         |

## User Stories

### US-01

**Category:** Primary

As a Division Manager for the Digital Transformation Office (DTO), I want StreetSmart to identify public infrastructure damage and integrate its reports with existing city systems, so that community responders can use the technology within their current workflows without introducing unnecessary friction.

### US-02

**Category:** Primary

As a manager in the Office of Performance and Data Analytics, I want StreetSmart to provide accurate data about public infrastructure damage, so that city staff can make maintenance decisions based on reliable information.

### US-03

**Category:** Secondary

As a Cincinnati commuter and driver, I want municipal road maintenance teams to receive automated alerts about severe potholes along major transit routes, so that dangerous road hazards are repaired promptly before they cause vehicle damage or accidents.

### US-04

**Category:** Hidden

As a municipal data privacy and compliance officer, I want StreetSmart to automatically redact personally identifiable information such as vehicle license plates and pedestrian faces from collected roadway footage before storage, so that the city upholds public privacy standards and complies with municipal data governance policies.

### US-05

**Category:** Hidden

As a city GIS analyst, I want StreetSmart to export verified pothole location and severity records in a standardized geospatial format such as GeoJSON, so that downstream municipal systems and infrastructure asset management platforms can ingest the data without custom transformation.

## INVEST Self-Check

| Story | Independent | Negotiable | Valuable | Estimable | Small | Testable | Notes |
| ----- | ----------- | ---------- | -------- | --------- | ----- | -------- | ----- |
| US-01 | ✓           | ✓          | ✓        | ✓         | ✓     | ✓        | Focuses on automated detection and smooth integration with existing city workflows without specifying UI elements |
| US-02 | ✓           | ✓          | ✓        | ✓         | ✓     | ✓        | Focuses on providing reliable infrastructure-damage data with confidence scoring to guide maintenance decisions |
| US-03 | ✓           | ✓          | ✓        | ✓         | ✓     | ✓        | Focuses on public safety and prompt hazard repair outcomes for road users without prescribing system interfaces |
| US-04 | ✓           | ✓          | ✓        | ✓         | ✓     | ✓        | Focuses on privacy compliance and automated redaction prior to long-term data retention |
| US-05 | ✓           | ✓          | ✓        | ✓         | ✓     | ✓        | Focuses on standardized data interoperability and export compatibility with existing municipal GIS platforms |

## Use Cases

### UC-01 - Process Infrastructure Footage

**Story:** US-01 - As a Division Manager for the Digital Transformation Office (DTO), I want StreetSmart to identify public infrastructure damage and integrate its reports with existing city systems, so that community responders can use the technology within their current workflows without introducing unnecessary friction.

**Primary Actor:** Division Manager, Digital Transformation Office (DTO)

**Secondary Actors:** StreetSmart System, Existing City Systems

**Preconditions:**

1. Vehicle camera footage is available for processing in a supported video container format.
2. The footage contains synchronized location data that can be used to determine the vehicle's geographic coordinates.
3. StreetSmart is connected to the city's existing system via an active, authenticated API connection.
4. The primary actor has verified administrative credentials to initiate processing and access the resulting infrastructure records.

**Main Success Flow:**

1. **Actor:** Submits vehicle camera footage and associated geographic track data to StreetSmart for processing.
2. **System:** Ingests the footage, runs machine learning inference to identify public infrastructure damage, and associates each detected instance with geographic coordinates.
3. **Actor:** Requests the processed infrastructure damage records for the submitted batch.
4. **System:** Generates structured records containing damage classification, model confidence score, geographic coordinates, and reference imagery, and presents the processed results.
5. **Actor:** Reviews the detection batch and initiates transfer of the records to the existing city infrastructure system.
6. **System:** Validates record integrity, transmits the structured infrastructure records to the external city system, and issues a confirmation of successful delivery.

**Alternate Flow:**

1. **System:** Processes the footage but does not identify any public infrastructure damage exceeding the confidence threshold.
2. **System:** Generates a processing summary indicating zero qualifying detections and logs the footage run as clear of hazards without generating new damage records.
3. **System:** Reports to the actor that processing finished with no actionable roadway defects detected.

**Exception Flow:**

1. **System:** Identifies infrastructure damage in the footage but cannot determine valid geographic coordinates due to missing or corrupted GPS data.
2. **System:** Creates the infrastructure record, flags it with status `LOCATION_UNRESOLVED`, and prevents automatic transfer to the existing city system.
3. **System:** Alerts the actor that the record requires location review before synchronization can proceed.

**Postcondition:**
Each detected infrastructure-damage event has a corresponding structured record containing its location, confidence score, and imagery, and is successfully synchronized with the existing city system.

### UC-02 - Export Roadway Damage Data to Municipal GIS

**Story:** US-05 - As a city GIS analyst, I want StreetSmart to export verified pothole location and severity records in a standardized geospatial format such as GeoJSON, so that downstream municipal systems and infrastructure asset management platforms can ingest the data without custom transformation.

**Primary Actor:** City GIS Analyst

**Secondary Actors:** StreetSmart System, Municipal GIS Database

**Preconditions:**

1. The primary actor is authenticated with permissions to query and export roadway infrastructure records.
2. Processed pothole detections with verified geographic coordinates exist in the StreetSmart database.
3. The downstream municipal GIS platform supports standard RFC 7946 GeoJSON format.

**Main Success Flow:**

1. **Actor:** Submits a data export request specifying a date range and geographic bounding box coordinates.
2. **System:** Queries the database for all verified pothole detections meeting the specified date and spatial criteria.
3. **Actor:** Selects the export format as standardized GeoJSON and confirms export generation.
4. **System:** Compiles the matching detections into a validated GeoJSON FeatureCollection containing coordinates, detection timestamps, confidence scores, and damage attributes.
5. **Actor:** Downloads the generated GeoJSON file for ingestion into the municipal GIS database.
6. **System:** Logs the export event with user ID, timestamp, and record count, and marks the exported records as synchronized.

**Alternate Flow:**

1. **System:** Identifies zero pothole detections matching the requested date range and bounding box coordinates.
2. **System:** Returns an empty GeoJSON FeatureCollection with valid schema headers and notifies the actor that no records matched the query criteria.

**Exception Flow:**

1. **System:** Detects invalid or out-of-range bounding box coordinates (e.g., latitude outside [-90, 90] or longitude outside [-180, 180]) in the request.
2. **System:** Rejects the export request with an error response detailing the coordinate boundary violation.
3. **System:** Halts file compilation to prevent incomplete or corrupt data from being transmitted to downstream GIS systems.

**Postcondition:**
A standardized, validated GeoJSON file containing all matching pothole detection records has been generated and delivered to the actor, with the export transaction logged in StreetSmart.

## Acceptance Criteria

### AC-01.1 (UC-01 Main Success Flow)

**Given** a 1080p vehicle camera video file of up to 60 minutes with synchronized NMEA GPS track data containing at least one roadway pothole,
**When** the Division Manager submits the footage to the StreetSmart processing pipeline,
**Then** StreetSmart completes ML inference within 1,200 seconds (20 minutes), records every detected pothole with a confidence score of 0.70 or higher, associates each detection with GPS coordinates accurate to within 5 meters, and makes the structured records available for city system transfer.

### AC-01.2 (UC-01 Exception Flow)

**Given** an uploaded video file containing pothole detections but lacking valid geographic metadata (null or corrupted GPS coordinates),
**When** StreetSmart completes inference processing on the video,
**Then** the system marks the record with status `LOCATION_UNRESOLVED`, prevents automated transmission to external city systems, and logs a location error event with HTTP status code 422 within 3 seconds.

### AC-02.1 (UC-02 Main Success Flow)

**Given** an authenticated GIS analyst requesting an export for a valid geographic bounding box containing 500 or fewer recorded pothole detections,
**When** the analyst submits the export request for standard GeoJSON format,
**Then** StreetSmart generates and delivers an RFC 7946-compliant GeoJSON FeatureCollection file containing 100% of the matching records within 5.0 seconds.

### AC-02.2 (UC-02 Exception Flow)

**Given** an authenticated GIS analyst submitting an export query containing coordinates outside valid geographic ranges (latitude beyond -90 to +90 or longitude beyond -180 to +180),
**When** the request is submitted to the export endpoint,
**Then** StreetSmart rejects the request with HTTP status code 400, returns a JSON error payload detailing the invalid bounding parameter within 1.0 second, and writes zero bytes to the export storage cache.
