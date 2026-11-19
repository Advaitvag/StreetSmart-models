# StreetSmart: Run Sheet and Rehearsal Log

CS 5001 Fall Design Presentation, Assignment 13. Deck: `StreetSmart_Presentation_Final.pptx` (10 main slides, 8 backup slides).

- **Time limit:** 10 minutes presenting, then 5 minutes of questions.
- **Planned length:** 9:00, which leaves a 60-second buffer.
- **Presentation slot:** November 25

## Speaking Roles

| Member | Slides | Section | Planned time |
| --- | --- | --- | --- |
| Advait Vagerwal | 1, 2, 3, 7 | Opening, abstract, progress and risks | 180 s |
| Sahil Thakare | 4, 6, 9 | Users, constraints, division of work | 175 s |
| Raihan Rafeek | 5, 8, 10 | System design, end of term, Expo demo and close | 185 s |

Speaking times are within 10 s of each other.

- **Timekeeper:** Sahil. Signals at 4:10 (start of slide 6) and 8:15 (start of slide 10). Holds up a card if the team is more than 20 s behind.
- **Q&A:** the owner in the questions table answers first. Others add only if the owner hands off.
- **Uploads deck to the LMS:** Advait, at or before the start of class.
- **Posts deck and video links in the Senior Design Team Table:** Sahil.
- **Backup copy on USB and offline cloud, tested on another machine:** Raihan.

## Slide Run Sheet

| Slide | Title | Speaker | Starts at | Seconds | Hand-off line |
| --- | --- | --- | --- | --- | --- |
| 1 | StreetSmart (title, purpose, goal) | Advait | 0:00 | 40 | "Here is who is building it." |
| 2 | Team and Advisor | Advait | 0:40 | 20 | "In short, here is the project." |
| 3 | Abstract | Advait | 1:00 | 50 | To Sahil: "Who is this for?" |
| 4 | Who It Is For (US-01 to US-05) | Sahil | 1:50 | 55 | To Raihan: "Here is how the system meets these." |
| 5 | How StreetSmart Works (D0) | Raihan | 2:45 | 85 | To Sahil: "These choices came from our constraints." |
| 6 | What Shaped the Design (CON-01 to CON-05) | Sahil | 4:10 | 65 | To Advait: "So how far along are we?" |
| 7 | Where We Are (done, not done, risks) | Advait | 5:15 | 70 | To Raihan: "Here is what we finish this term." |
| 8 | By the End of Fall (M2, M3, M4) | Raihan | 6:25 | 55 | To Sahil: "Here is how we split the work." |
| 9 | Who Does What | Sahil | 7:20 | 55 | To Raihan: "Here is what you will see at Expo." |
| 10 | What We Will Demo | Raihan | 8:15 | 45 | "Thank you. We are happy to take questions." |
| | **Total** | | **9:00** | **540** | |

Backup slides for questions:

- B1 (11): original D0
- B2 (12): D1 data model
- B3 (13): D2 flow and error paths
- B4 (14): hardware parts
- B5 (15): Gantt
- B6 (16): model accuracy
- B7 (17): risk register

## Anticipated Questions

Questions 2, 4 and 6 do not have a full answer yet. For those, say what is still open and give the next step.

| # | Question | Owner | Short answer | Backup |
| --- | --- | --- | --- | --- |
| 1 | Why did detection move from the server to the vehicle? | Raihan | The Oct 30 advisor review picked Design 1. Only pothole photos go over LTE (CON-01). Unblurred video never leaves the vehicle (CON-02). | B1, B4 |
| 2 | How accurate is the model, really? | Advait | 0.81 mAP@0.5 on held-out images with no Cincinnati photos. **Not resolved yet.** Next step: finish the run, report its test score against the 0.75 gate (NFR-04), then retrain with field data (T18). | B6 |
| 3 | Why not test on Cincinnati photos? | Advait | Their labels were made by a model, so they may be wrong. We also cannot share those images. | B6 |
| 4 | Will the 5 m merge radius work with real GPS error? | Raihan | **Not known yet** (R1, NFR-05). The clock check (T07) comes first. Then we measure the spread of repeat sightings on the January drive (T11) and set the threshold from data (T14). | B7 |
| 5 | How do you protect faces and license plates? | Advait | Blur runs on the vehicle unit. If the blur fails or is unsure, the image is withheld and only the detection is kept (E-15). The target is at least 95% of faces and plates (NFR-07). | B3, B7 |
| 6 | Can the unit keep up with a full shift? | Advait | **Not tested yet** (R2, NFR-01: 60 minutes of video in 20). The December benchmark (T10, M4) decides between YOLO26m and 26s and sets the frame rate. Fallback: fewer frames per second. | B7 |
| 7 | Does it file 311 requests by itself? | Sahil | No. A person reviews each pothole on the map first. The 311 system is not changed, and Expo never sends to the real 311. | — |
| 8 | What does a vehicle unit cost? | Advait | $289 for the core parts and $369 with LTE. The city offered to buy the hardware. | B4 |
| 9 | What happens when GPS drops out, for example under a bridge? | Sahil | The detection is marked `LOCATION_UNRESOLVED` and kept out of the database. It is listed in the run summary for review (REQ-15). | B3 |
| 10 | Raihan owns most of the critical path. What if he is out? | Sahil | Every critical-path task has a named backup member. Hours are compared at M6 and M9, and anyone more than 10% over the mean hands off a task (R5). | B5, B7 |
| 11 | Which login provider are you using? | Sahil | Not chosen yet (T03, D2 §1.4 #9). The API is built behind an auth interface, so the provider plugs in later without changes (R9). | — |
| 12 | Why Go for the backend? | Raihan | One codebase for the worker and the API. ONNX Runtime already runs our model from Go (Oct 12). Go's counts are checked against Python at M2 (R10). | B7 |

## Rehearsal Log

Log at least one full-group timed rehearsal. Record the actual times, not the plan. The per-slide splits, Q&A drill results and the changes made after each run are in [Rehearsal_Log.md](Rehearsal_Log.md).

| Date | Members present | Slides 1–3 (Advait, plan 1:50) | Slides 4–6 (Sahil / Raihan, plan 3:25) | Slide 7 (Advait, plan 1:10) | Slides 8–10 (Raihan / Sahil, plan 2:35) | Total (plan 9:00) | Changes made after |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-17 | Advait, Raihan, Sahil | 2:05 | 4:06 | 1:28 | 2:59 | 10:38 (+18%) | Streamlined D0; grouped US-01–05; moved model split details & deep edge cases to backup slides. |
| 2026-11-18 | Advait, Raihan, Sahil | 1:49 | 3:28 | 1:14 | 2:37 | 9:08 (+8 s) | Pacing on target (52 s buffer). Practiced timekeeper cue cards at 4:10 and 8:15. |
| 2026-11-18 | Advait, Raihan, Sahil | 1:46 | 3:23 | 1:11 | 2:34 | 8:54 (-6 s) | Final dress run (66 s buffer). Drilled 5-min Q&A simulation with backup slides B1–B8; deck frozen. |

Per-member totals from the timed rehearsal:

| Member | Planned | Actual |
| --- | --- | --- |
| Advait | 180 s | 181 s |
| Sahil | 175 s | 173 s |
| Raihan | 185 s | 180 s |
