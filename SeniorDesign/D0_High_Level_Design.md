# StreetSmart - High-Level System Design (D0)

**Team Members:** Raihan Rafeek, Advait Vagerwal, Sahil Thakare

**Course:** CS 5001
**Assignment:** Design D0 - High-Level System Design
**Date:** 29 September 2026

---

# 1. Title, Goal Statement, and Conventions

## Goal Statement

StreetSmart is a system that uses vehicle-mounted camera footage to identify public infrastructure damage, geotag detected issues, and provide city personnel with a centralized map and database of infrastructure conditions.

### Basic Input

* Vehicle camera footage containing road and infrastructure imagery
* GPS/location information associated with the footage

### Basic Output

* Identified infrastructure issues with geographic coordinates and relevant metadata
* Map/database records that city personnel can review and act upon
* Authenticated UI and API based access to data

## Diagram Conventions
| Shape                 | Meaning                           |
| --------------------- | --------------------------------- |
| **Rectangle**         | StreetSmart component we build    |
| **Rounded rectangle** | External system/service           |
| **Cylinder**          | Persistent data storage/database  |
| **Parallelogram**     | Input/output data                 |
| **Arrow**             | Data/interface between components |
| **Dashed arrow**      | External integration              |
| `I1`, `I2`, etc.      | Interface ID                      |

---

# 2. Block Diagram

## D0 System Architecture

```mermaid
flowchart TD

    %% =========================
    %% TRAINING INPUTS
    %% =========================

    TRAINING_DATA[/Labeled Training Data/]

    %% =========================
    %% RUNTIME INPUTS
    %% =========================

    VIDEO[/Vehicle Camera Footage/]
    GPS[/GPS Data/]

    %% =========================
    %% STREETSMART COMPONENTS
    %% =========================

    TRAINING["Model Training"]

    MODEL[("Trained Model")]

    INFERENCE["Model Inference"]

    INGESTION["Ingestion Pipeline"]

    DATABASE[("PG Database")]

    API["Backend API"]

    MAP["Current Infrastructure Map"]

    %% =========================
    %% EXTERNAL SYSTEM
    %% =========================

    CITY("City Systems")

    %% =========================
    %% TRAINING FLOW
    %% =========================

    TRAINING_DATA -->|I1: Labeled Data| TRAINING
    TRAINING -->|I2: Trained Model| MODEL
    MODEL -->|I3: Model| INFERENCE

    %% =========================
    %% RUNTIME FLOW
    %% =========================

    VIDEO -->|I4: Video| INFERENCE
    GPS -->|I5: Location| INGESTION

    INFERENCE -->|I6: Damage Detection| INGESTION
    INGESTION -->|I7: Damage + Location| DATABASE

    DATABASE -->|I8: Infrastructure Records| API

    API -->|I9: Current Infrastructure Data| MAP

    API -.->|I10: System Integration| CITY
```

### Component Overview

| Component                      | Purpose                                                                                                    |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| **Model Training**             | Trains the infrastructure-damage detection model using labeled vehicle and infrastructure imagery.         |
**Trained Model** | Model with fixed weights based on training, ready to identify potholes from video frames provided |
| **Model Inference**            | Uses the trained model to analyze vehicle camera footage and identify infrastructure damage.               |
| **Ingestion Pipeline**         | Combines damage detections with GPS location data and prepares the resulting information for storage.      |
| **PG Database**                | Stores infrastructure damage records, geographic coordinates, and associated metadata for later retrieval. |
| **Backend API**                | Provides infrastructure records to the map interface and supports integration with external city systems.  |
| **Current Infrastructure Map** | Displays detected infrastructure damage and its geographic locations for city users to review.             |

---

# 3. Component Responsibility Table

| Component                      | Responsibility                                                                                             | Interfaces In | Interfaces Out | Primary Owner |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------- | ------------- | -------------- | ------------- |
| **Model Training**             | Trains and updates the infrastructure-damage detection model using labeled training data.                  | I1            | I2             | Advait Vagerwal           |
| **Trained Model**              | Stores the trained model used by the inference system for infrastructure-damage detection.                 | I2            | I3             | Advait Vagerwal           |
| **Model Inference**            | Processes vehicle camera footage using the trained model to identify infrastructure damage.                | I3, I4        | I6             | Raihan Rafeek           |
| **Ingestion Pipeline**         | Combines detected damage with GPS location data and prepares the resulting information for storage.        | I5, I6        | I7             | Sahil Thakare           |
| **PG Database**                | Stores infrastructure damage records, geographic coordinates, and associated metadata for later retrieval. | I7            | I8             | Sahil Thakare           |
| **Backend API**                | Provides infrastructure records to the map interface and supports integration with external city systems.  | I8            | I9, I10        | Raihan Rafeek, Sahil Thakare           |
| **Current Infrastructure Map** | Displays infrastructure damage and its geographic locations for users to review.                           | I9            | —              | Advait Vagerwal, Sahil Thakare           |

---

# 4. Interface Specification Table

| ID      | Interface                            | Inputs                              | Outputs                           | Data Format                 | Protocol                    | Error Handling                                                   |
| ------- | ------------------------------------ | ----------------------------------- | --------------------------------- | --------------------------- | --------------------------- | ---------------------------------------------------------------- |
| **I1**  | Training Data → Model Training       | Labeled images/annotations          | Training dataset                  | Images + annotation files   | File system / batch process | Invalid or missing labels are rejected/logged                    |
| **I2**  | Model Training → Trained Model       | Training data/configuration         | Trained model artifact            | ONNX model                  | File storage                | Training failure logged; previous valid model retained           |
| **I3**  | Trained Model → Model Inference      | Trained model                       | Loaded model                      | ONNX                        | Local file/model loading    | Model load failure prevents inference and logs error             |
| **I4**  | Camera → Model Inference             | Vehicle footage                     | Video frames                      | Video stream/file           | Local camera/file input     | Invalid/unreadable frames skipped or logged                      |
| **I5**  | GPS → Ingestion Pipeline             | Location readings                   | latitude, longitude, timestamp       | JSON/structured record      | Local device/API            | Missing or invalid coordinates rejected                          |
| **I6**  | Model Inference → Ingestion Pipeline | Video frames                         | Damage type, confidence, timestamp, image reference                | Structured JSON/object      | Internal process/API        | Invalid detections rejected/logged                               |
| **I7**  | Ingestion Pipeline → PG Database     | Damage type, confidence, latitude, longitude, timestamp, image reference        | Stored infrastructure record      | SQL row / structured record | PostgreSQL                  | Database errors logged and record write retried                  |
| **I8**  | PG Database → Backend API            | Stored infrastructure records       | Query results                     | JSON/structured data        | PostgreSQL connection       | Query/connection errors returned and logged                      |
| **I9**  | Backend API → Infrastructure Map     | Infrastructure records              | Map-ready issue data              | JSON                        | HTTP/REST                   | HTTP error returned to client                                    |
| **I10** | Backend API ↔ City Systems           | Infrastructure records/API requests | City-compatible records/responses | JSON                        | HTTP/REST                   | Authentication, validation, and connection errors handled by API |


## Example Payload

```json
{
  "id": "damage_00123",
  "type": "pothole",
  "confidence": 0.94,
  "latitude": 39.1031,
  "longitude": -84.5120,
  "timestamp": "2026-09-29T12:00:00Z",
  "image_url": "https://example.com/images/damage_00123.jpg"
}
```

# 5. Data-Flow Diagram

## Model Training Flow
```mermaid
flowchart LR

    A[/Labeled Training Data/]
    B["Model Training"]
    C[("Trained ONNX Model")]

    A -->|"Labeled images + annotations"| B
    B -->|"Trained model artifact"| C
```

## Runtime Detection Flow

```mermaid
flowchart TD

    A[/Vehicle Camera Footage/]
    B["Model Inference"]
    C["Ingestion Pipeline"]
    D[("PG Database")]
    E["Backend API"]
    F["Current Infrastructure Map"]

    G[/GPS Data/]

    A -->|"Raw video frames"| B
    B -->|"Damage type + confidence + timestamp + image"| C
    G -->|"Latitude + longitude + timestamp"| C
    C -->|"Validated damage record"| D
    D -->|"Stored infrastructure records"| E
    E -->|"Map-ready issue data"| F
```

StreetSmart has two primary data flows: a model training flow that produces the trained detection model, and a runtime detection flow that uses the model to identify and record infrastructure damage.

### Model Training Data Flow

1. **Training Data** - Labeled infrastructure imagery and annotations are provided to the model training process.
2. **Model Training** - The training component processes the labeled data to train an infrastructure damage detection model over a finite number of epochs.
3. **Trained Model** - The resulting model is exported as an ONNX model and made available to the Model Inference component.

### Runtime Data Flow

1. **Capture** - Vehicle-mounted cameras collect road and infrastructure footage while GPS provides the associated location information.
2. **Inference** - Model Inference processes video frames using the trained ONNX model and produces detected infrastructure issues, including damage type, confidence, and associated metadata.
3. **Ingestion** - The Ingestion Pipeline combines the detection results with GPS coordinates and other associated metadata.
4. **Storage** - The resulting validated infrastructure record is stored in the PostgreSQL database.
5. **API Access** - The Backend API retrieves infrastructure records and makes them available to client applications and external integrations.
6. **Visualization** - The Current Infrastructure Map uses the API data to display detected infrastructure issues at their geographic locations.

### Timing Requirements

For the scope of senior design, StreetSmart is not required to perform inference in real time. Captured footage can be processed by the inference pipeline and converted into infrastructure records for later review. Processing and API response times will be evaluated during implementation and refined based on system performance.

---

# 6. Architecture Pattern and Justification

## Selected Architecture Pattern(s)

### Pipeline

**Used for:**
TODO — Explain how footage moves through sequential ingestion, detection, and data-processing stages.

### Client-Server

**Used for:**
TODO — Explain the relationship between the map/client interface and StreetSmart backend.

### Layered / Other Pattern

**Used for:**
TODO — Include only if actually applicable.

---

## Pattern Justification

### Fit to the Problem

TODO

### Team Skills

TODO

### Performance and Timing

TODO

### Scalability

TODO

### Hardware Constraints

TODO

---

## Rejected Alternative

**Pattern considered:** TODO

**Why it was considered:**
TODO

**Why it was rejected:**
TODO

---

# 7. Decision Log

| Decision                             | Alternatives Considered | Chosen Option | Reason |
| ------------------------------------ | ----------------------- | ------------- | ------ |
| D-01: How footage enters the system  | TODO                    | TODO          | TODO   |
| D-02: Where damage detection occurs  | TODO                    | TODO          | TODO   |
| D-03: How detected issues are stored | TODO                    | TODO          | TODO   |
| D-04: How city users access results  | TODO                    | TODO          | TODO   |

### Decision Details

#### D-01 — TODO Decision

**Decision:**
TODO

**Alternatives:**

* Option A
* Option B
* Option C

**Reason:**
TODO

#### D-02 — TODO Decision

**Decision:**
TODO

**Alternatives:**

* Option A
* Option B

**Reason:**
TODO

#### D-03 — TODO Decision

**Decision:**
TODO

**Alternatives:**

* Option A
* Option B

**Reason:**
TODO

#### D-04 — TODO Decision

**Decision:**
TODO

**Alternatives:**

* Option A
* Option B

**Reason:**
TODO
