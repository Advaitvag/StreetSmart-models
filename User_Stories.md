# Assignment 4 - User Stories and Use Cases

## Team Members

1. Advait Vagerwal
2. Sahil Thakare
3. Raihan Rafeek

## Stakeholder Map

| Category  | Stakeholder                                       | Need                                                                                                                                                           |
| --------- | ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Primary   | City of Cincinnati                                | Identify, locate, and prioritize potholes and other public infrastructure damage while integrating StreetSmart's data with existing city systems and workflows |
| Secondary | Cincinnati Residents and Drivers                  | Benefit from safer, better-maintained roads and public infrastructure                                                                                          |
| Hidden    | Other Municipalities / Municipal Technology Teams | Evaluate and adapt StreetSmart's infrastructure-monitoring approach for use within their own cities and data systems                                           |

## User Stories

### US-01

**Category:** Primary

As a Division Manager for the Digital Transformation Office (DTO), I want StreetSmart to identify public infrastructure damage and integrate its reports with existing city systems, so that community responders can use the technology within their current workflows without introducing unnecessary friction.

### US-02

**Category:** Primary

As a manager in the Office of Performance and Data Analytics, I want StreetSmart to provide accurate data about public infrastructure damage, so that city staff can make maintenance decisions based on reliable information.

## INVEST Self-Check

| Story | Independent | Negotiable | Valuable | Estimable | Small | Testable | Notes                                                                              |
| ----- | ----------- | ---------- | -------- | --------- | ----- | -------- | ---------------------------------------------------------------------------------- |
| US-01 | ✓           | ✓          | ✓        | ✓         | ✓     | ✓        | Focuses on automated detection and smooth integration with existing city workflows |
| US-02 | ✓           | ✓          | ✓        | ✓         | ✓     | ✓        | Focuses on providing reliable infrastructure-damage data                           |

## Use Cases

### UC-01 - Process Infrastructure Footage

**Story:** US-01 - As a Division Manager for the Digital Transformation Office (DTO), I want StreetSmart to identify public infrastructure damage and integrate its reports with existing city systems, so that community responders can use the technology within their current workflows without introducing unnecessary friction.

**Primary Actor:** Division Manager, Digital Transformation Office (DTO)

**Secondary Actors:** StreetSmart, Existing City Systems

**Preconditions:**

1. Vehicle camera footage is available for processing.
2. The footage contains location data that can be used to determine the vehicle's coordinates.
3. StreetSmart is connected to the city's existing system for receiving infrastructure data.
4. The primary actor has permission to access the resulting infrastructure records.

**Main Success Flow:**

1. **Actor:** Provides vehicle camera footage to StreetSmart.
2. **System:** Processes the footage and identifies public infrastructure damage.
3. **System:** Determines the geographic coordinates associated with the detected damage.
4. **System:** Creates a structured infrastructure record containing the damage type, location, and supporting footage or image.
5. **Actor:** Requests the processed infrastructure records.
6. **System:** Displays the detected infrastructure damage and its corresponding geographic location.
7. **Actor:** Initiates integration with the existing city system.
8. **System:** Transfers the infrastructure record to the existing city system and confirms successful integration.

**Alternate Flow:**

1. **System:** Processes the footage but does not identify any public infrastructure damage.
2. **System:** Completes processing without creating an infrastructure-damage record.
3. **System:** Indicates that no qualifying infrastructure damage was detected.

**Exception Flow:**

1. **System:** Identifies infrastructure damage but cannot determine a valid geographic location for the detection.
2. **System:** Creates the infrastructure record without a location and flags it as requiring location review.
3. **System:** Prevents the incomplete record from being transferred to the existing city system until the required location information is available.

**Postcondition:**
Each detected infrastructure-damage event has a corresponding structured record containing its location and damage information and is available for integration with the existing city system.


## Acceptance Criteria
