# StreetSmart: Presentation Rehearsal Log & Q&A Drill

**Course:** CS 5001 Senior Design (Fall 2026)  
**Deck:** `StreetSmart_Presentation_Final.pptx` / `StreetSmart_Presentation_Final.pdf` (10 main slides, 8 backup slides)  
**Team:** Advait Vagerwal, Raihan Rafeek, Sahil Thakare  
**Presentation Slot:** November 25, 2026  
**Target Length:** 9:00 (540 seconds) to ensure a 60-second safety buffer  

---

## 1. Rehearsal Overview & Log Summary

| Run # | Date & Time | Location | Focus / Objective | Present | Total Time | Variance vs 9:00 Plan | Key Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Run 1** | Tue Nov 17, 2026<br>4:30 PM – 5:45 PM | ERC 427 Study Room | Baseline uncut run; identify pacing bottlenecks | All (Advait, Raihan, Sahil) | **10:38** (638 s) | +1:38 (+18.1%) | Ran ~18% over limit. Identified heavy overruns on Slide 5 (D0) and Slide 7 (Risks). Outlined mandatory cuts. |
| **Run 2** | Wed Nov 18, 2026<br>1:00 PM – 2:15 PM | Rhodes 802 Collab Space | Timed run with cuts implemented; cue card signaling | All (Advait, Raihan, Sahil) | **9:08** (548 s) | +0:08 (+1.5%) | Pacing on track; 52 s under 10:00 limit. Hand-offs crisp. Sahil tested 4:10 and 8:15 cards. |
| **Run 3** | Wed Nov 18, 2026<br>4:00 PM – 5:30 PM | Rhodes 802 / Online Sandbox | Full dress rehearsal + 5:00 simulated Q&A drill | All (Advait, Raihan, Sahil) | **8:54** (534 s) | -0:06 (-1.1%) | Target 9:00 achieved (66 s buffer). Drilled 6 Q&A scenarios including unresolved risks. Deck frozen. |

---

## 2. Rehearsal 1: Baseline Uncut Run (Nov 17, 2026)

*Objective:* Deliver full speaker notes without artificial rushing to establish true baseline timing and locate structural content bloat.  
*Timekeeper:* Sahil Thakare (stopwatch tracking individual slide splits).

### Per-Slide Timing Breakdown

| Slide | Title | Speaker | Planned | Actual | Delta | Observations & Root Causes |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **1** | StreetSmart (Title, Purpose, Goal) | Advait | 40 s | 46 s | +6 s | Clear opening, but spent extra time explaining why Cincinnati lacks automated detection. |
| **2** | Team and Advisor | Advait | 20 s | 22 s | +2 s | Good pacing; mentioned Eric Jamison and City role smoothly. |
| **3** | Abstract | Advait | 50 s | 57 s | +7 s | Delved into historical dataset splits and licensing before moving to user stories. |
| **4** | Who It Is For (US-01 to US-05) | Sahil | 55 s | 71 s | +16 s | Read through each user story title individually rather than synthesizing into driver vs inspector personas. |
| **5** | How StreetSmart Works (D0) | Raihan | 85 s | 114 s | +29 s | Major bottleneck: walked through every single block and arrow on D0; explained edge ONNX inference details that belong on backup slide B1. |
| **6** | What Shaped the Design (CON-01 to CON-05) | Sahil | 65 s | 81 s | +16 s | Thoroughly explained every constraint rationale; repeated the "Checked By" text verbatim rather than summarizing the verification link. |
| **7** | Where We Are (Done, Not Done, Risks) | Advait | 70 s | 88 s | +18 s | Over-explained the held-out mAP discrepancy and got bogged down in R1/R2 risk explanations. |
| **8** | By the End of Fall (M2, M3, M4) | Raihan | 55 s | 64 s | +9 s | Lingered on M2 Go vs Python verification nuance instead of keeping to high-level deliverables. |
| **9** | Who Does What (Division of Work) | Sahil | 55 s | 58 s | +3 s | Clean hand-off from Raihan; balanced coverage of assigned components. |
| **10** | What We Will Demo (Expo Demo & Close) | Raihan | 45 s | 47 s | +2 s | Strong closing; clear transition to Q&A. |
| **Total** | | | **9:00 (540 s)** | **10:38 (638 s)** | **+98 s (+18.1%)** | **Exceeded hard 10-minute cap by 38 seconds.** |

### Speaker Distribution (Run 1)

- **Advait:** 213 s (33.4%)
- **Sahil:** 210 s (32.9%)
- **Raihan:** 225 s (35.3%)
- *Variance between highest and lowest:* 15 s (well balanced, but all speakers ran 15–20% over budget).

### Action Items & Content Cuts Decided

1. **Slide 3 (Abstract):** Cut the historical discussion on dataset splits. Focus strictly on the 3-step pipeline: capture on vehicle, edge inference + blurring, PostGIS map review. Push training split nuances to Backup Slide B6.
2. **Slide 4 (User Stories):** Group US-01 through US-05 into two functional groups (Field Crew capture vs City Engineer web review) rather than reading individual user story headers.
3. **Slide 5 (D0 Diagram):** Streamline explanation to 3 core stages: (1) Vehicle dashcam unit with on-device YOLO + blur, (2) LTE/Wi-Fi ingest to PostGIS, (3) Web frontend & 311 review. Offload architectural edge cases and fallback buses to Backup Slide B1/B3.
4. **Slide 6 (Constraints):** Keep to the four cards. Call out the constraint and immediately name the "Checked By" requirement without recounting historical background.
5. **Slide 7 (Where We Are):** State current status crisply: 19.5k images trained, baseline mAP 0.81, pipeline deployed. Acknowledge R1 (GPS drift) and R2 (edge shift throughput) candidly as open items without lengthy apologies.

---

## 3. Rehearsal 2: Timed Run with Cuts & Signals (Nov 18, 2026)

*Objective:* Execute streamlined speaker notes, test physical timekeeper cue cards at 4:10 (Slide 6 start) and 8:15 (Slide 10 start), and hit the 9:00 target.  
*Timekeeper:* Sahil Thakare.

### Per-Slide Timing Breakdown

| Slide | Title | Speaker | Planned | Actual | Delta | Rehearsal Notes & Cue Compliance |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **1** | StreetSmart (Title, Purpose, Goal) | Advait | 40 s | 41 s | +1 s | Crisp hook; clearly articulated Cincinnati pothole problem. |
| **2** | Team and Advisor | Advait | 20 s | 19 s | -1 s | Smooth introduction of team roles and City advisor Eric Jamison. |
| **3** | Abstract | Advait | 50 s | 49 s | -1 s | Successfully trimmed; clean hand-off line: *"Who is this for?"* |
| **4** | Who It Is For (US-01 to US-05) | Sahil | 55 s | 54 s | -1 s | Personas grouped effectively; hand-off line to Raihan delivered on point at 2:43. |
| **5** | How StreetSmart Works (D0) | Raihan | 85 s | 87 s | +2 s | Much tighter D0 walk-through; avoided rabbit holes on hardware schematics. Hand-off line delivered cleanly. |
| **6** | What Shaped the Design (CON-01 to CON-05) | Sahil | 65 s | 67 s | +2 s | Sahil checked time card at 4:10 (actual start: 4:10!). Highlighted "Checked By" lines rapidly. Hand-off to Advait at 5:17. |
| **7** | Where We Are (Done, Not Done, Risks) | Advait | 70 s | 74 s | +4 s | Handled the split cleanly: Done (model, backend skeleton), Not Done (Cincinnati clip benchmark), Risks (R1 GPS, R2 throughput). Hand-off to Raihan at 6:31. |
| **8** | By the End of Fall (M2, M3, M4) | Raihan | 55 s | 56 s | +1 s | Walked through M2 (benchmark), M3 (Go-Python parity), M4 (board review). Hand-off to Sahil at 7:27. |
| **9** | Who Does What (Division of Work) | Sahil | 55 s | 56 s | +1 s | Walked through Assignment 6 matrix and backup owners. Hand-off to Raihan at 8:23. |
| **10** | What We Will Demo (Expo Demo & Close) | Raihan | 45 s | 45 s | 0 s | Sahil displayed 8:15 cue card right before Slide 10. Raihan closed firmly: *"Thank you. We are happy to take questions."* |
| **Total** | | | **9:00 (540 s)** | **9:08 (548 s)** | **+8 s** | **Well within the 10:00 limit; leaves 52 seconds buffer.** |

### Speaker Distribution (Run 2)

- **Advait:** 183 s (planned 180 s) -> +3 s
- **Sahil:** 177 s (planned 175 s) -> +2 s
- **Raihan:** 188 s (planned 185 s) -> +3 s
- *Balance Check:* The difference between the longest speaker (Raihan, 188 s) and shortest speaker (Sahil, 177 s) is **11 seconds**, easily surpassing the assignment requirement of staying within 30 seconds per member.

---

## 4. Rehearsal 3: Final Dress Rehearsal & Q&A Simulation (Nov 18, 2026)

*Objective:* Final run-through under simulated presentation conditions followed immediately by a 5-minute timed Q&A drill simulating tough questions from the faculty panel and peers.

### Final Timed Presentation Run

| Section | Speaker(s) | Planned Time | Actual Time (Run 3) | Variance |
| :--- | :--- | :---: | :---: | :---: |
| **Slides 1–3 (Opening, Team, Abstract)** | Advait | 1:50 (110 s) | **1:46** (106 s) | -4 s |
| **Slides 4–6 (Users, D0 Architecture, Constraints)** | Sahil / Raihan | 3:25 (205 s) | **3:23** (203 s) | -2 s |
| **Slide 7 (Current Progress, Status, Risks)** | Advait | 1:10 (70 s) | **1:11** (71 s) | +1 s |
| **Slides 8–10 (Fall Milestones, Division, Expo Demo)** | Raihan / Sahil | 2:35 (155 s) | **2:34** (154 s) | -1 s |
| **Total Presentation Time** | **Team** | **9:00 (540 s)** | **8:54 (534 s)** | **-6 s (66 s buffer)** |

#### Member Totals for Run 3

- **Advait Vagerwal:** 181 s
- **Sahil Thakare:** 173 s
- **Raihan Rafeek:** 180 s
- *Evaluation:* Excellent pacing and conversational cadence. Natural transitions with direct eye contact. Timekeeper cards were visible without interrupting speaker flow.
