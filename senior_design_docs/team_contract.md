# Senior Design Team Contract

**Project:** StreetSmart
**Team Members:** Advait Vagerwal, Sahil Thakare, Raihan Rafeek 
**Advisor:** Eric Jamison
**Course/Term:** CS 5001 - Senior Design Fall 2026
**Version:** 0.1

---

## 1. Project Purpose

Our team will design and develop StreetSmart to address the lack of an automated pothole detection and reporting system in the Greater Cincinnati Metropolitan Area. StreetSmart will use a machine learning model to identify potholes from roadway imagery captured by cameras mounted on vehicles such as police cars or municipal vehicles, associate detected potholes with geographic locations, store them, and display them on an interactive map to keep track of their specific locations.

The intended users and stakeholders are local transportation and public works organizations that monitor and maintain roadways, as well as organizations operating vehicles equipped with roadway-facing cameras. The primary goal of the project is to provide an automated method for collecting and visualizing pothole locations as vehicles travel through the region, reducing the need for personnel to manually identify and record individual potholes.

The project will be considered successful if it can detect potholes in test roadway imagery, associate detections with geographic locations, display detected potholes on an interactive map, and persist detection data in a database for later retrieval and analysis.

---

## 2. Team Responsibilities

Each team member will contribute to the project through a combination of technical development, research, documentation, testing, and project coordination.

### Advait Vagerwal

* Primary responsibilities: Machine learning models training & testing, Architecture design
* Secondary responsibilities: ML inference and pipeline, System testing, Server administration

### Sahil Thakare

* Primary responsibilities: Frontend development, UI/UX design, Backend testing
* Secondary responsibilities: Status tracking, Documentation

### Raihan Rafeek

* Primary responsibilities: Inference pipeline, Backend Servies (APIs), Database
* Secondary responsibilities: Documentation, CI/CD, Git management (ops)

> Responsibilities may change as the project develops. Any significant redistribution of responsibilities will be discussed and agreed upon by the team.

---

## 3. Communication

Our primary communication channels will be:

* **Primary:** iMessage and Teams
* **Project documentation:** Github, Microsoft OneDrive (UC)
* **Urgent communication:** Phone call

Team members are expected to respond to project-related messages within 2 hours, except when they have communicated that they are unavailable.

Important project decisions will be documented in Github Issues and FigJam so that all team members can access them.

---

## 4. Meetings

The team will meet weekly at approximately 4PM on Wednesdays.

Meetings will generally include:

1. Review of progress since the previous meeting
2. Discussion of current blockers
3. Assignment or confirmation of upcoming tasks
4. Review of project deadlines
5. Decisions requiring team agreement

Team members who cannot attend a meeting should notify the team beforehand when reasonably possible and review the resulting notes afterward.

---

## 5. Task Assignment and Deadlines

Project tasks will be tracked using Github Issues and a FigJam board.

Each task should have:

* A clearly defined objective
* An assigned team member
* A target completion date
* Any relevant dependencies

Team members are responsible for communicating early if they expect to miss a deadline or encounter a significant blocker.

If a deadline cannot be met, the team will determine whether to:
- Reassign the task
- Reschedule for a better time
- Prioritize completion and refine later
- Consult mentor for direction

---

## 6. Decision Making

The team will attempt to make major project decisions through discussion and consensus.

Major decisions include:

* Project scope changes
* Architecture changes
* Technology choices that significantly affect the project
* Changes to requirements
* Changes to deadlines
* Decisions that affect another team member's responsibilities

When consensus cannot be reached, the team will discuss the issue further and, when appropriate, use a team vote to reach a decision.

The mentor will be consulted when a decision significantly affects project scope, technical feasibility, or a requirement that the team cannot resolve independently.

---
## 7. Scope and Requirements

The team's initial scope includes:

* **Automated pothole detection** using a machine learning model applied to roadway imagery captured from a vehicle-mounted camera
* **Geographic localization** of detected potholes using the vehicle's or camera's location data
* **Pothole data management**, including storing detection location, timestamp, confidence, and relevant metadata
* **Interactive map interface** for visualizing detected potholes and updating roadway data
* **Role-based views** for roadway reporters/vehicle operators and organizations responsible for reviewing and managing detected potholes
* **Backend API and database infrastructure** connecting the ML inference pipeline, detection data, and frontend
* **End-to-end vehicle testing** using the team's available camera equipment and a borrowed vehicle

The following items are explicitly outside the initial scope:

* Direct integration with municipal or government work-order systems
* Automated dispatch of repair crews or physical pothole repairs
* Continuous real-time processing of all camera footage at production scale

Scope changes will be evaluated based on their effect on **time, resources, technical feasibility, and project requirements**.

The team will prioritize the core detection, localization, storage, and visualization pipeline before adding features that do not directly support these objectives.


---

## 8. Technical Standards and Development Practices

The team will use:

* **Version control:** Git/GitHub
* **Primary languages:** Python (model training + inference) / JavaScript (frontend) / Go (backend)
* **Frameworks:** YOLO / PyTorch / Flask / React / Gin
* **Documentation:** Markdown in repositories
* **Testing:** Unit tests / accuracy tests / integration tests (all custom)

All code intended for integration into the main project should be committed through **pull requests -> code review -> commits**.

Team members should avoid introducing dependencies, services, or technologies that create significant additional cost, security risk, or maintenance requirements without discussing them with the team.

---

## 9. Code and Repository Practices

Development work should generally occur through feature branches, which are merged into the development branch through pull requests. The main branch will contain stable releases.

Before merging significant changes, team members should:

* Verify that their changes work as intended
* Avoid committing secrets or credentials
* Document significant configuration changes
* Resolve or communicate known issues
* Require at least one team member review before merging

API keys, passwords, authentication tokens, and other credentials must not be committed to the repository.

---

## 10. Documentation

Each team member is responsible for documenting the work they contribute.

Documentation may include:

* Technical decisions
* Architecture decisions
* Setup instructions
* Testing procedures
* Research findings
* Design changes
* Known limitations

Important decisions should be documented when they are made rather than reconstructed near the end of the project.


---

## 11. Security, Privacy, and Data

The team will identify and address security and privacy requirements relevant to **user account information, authentication credentials, geographic coordinates, roadway imagery, and pothole detection data**. StreetSmart will use **JWT-based authentication** to control access to protected API endpoints, while API keys and other credentials will be stored securely rather than committed to the project repository. Sensitive data transmitted between system components will use encrypted connections, and stored credentials or secrets will not be stored in plaintext.

The project will primarily collect **pothole detection results, geographic coordinates, timestamps, roadway imagery, and user account information required for authentication**. The system will minimize collection of information unrelated to pothole detection and roadway analysis, and access to stored data will be restricted based on the user's role and authentication status.

Because roadway imagery may incidentally capture vehicles, license plates, pedestrians, or other identifying information, the team will evaluate whether such information needs to be retained and will avoid storing unnecessary personally identifiable information where possible. Any security or privacy concern that could materially affect users or deployment will be discussed by the team before the relevant design decision is finalized.


---

## 12. Academic and Professional Conduct

All team members will follow applicable University of Cincinnati policies and course requirements.

Team members will appropriately credit:

* External libraries
* Open-source projects
* Research
* Third-party assets
* AI-assisted development
* Other external contributions

No team member will represent another person's work as their own.

---

## 13. Conflict Resolution

If a disagreement occurs, team members will first attempt to resolve it through direct discussion.

If the issue cannot be resolved, the team will:

1. Clearly identify the disagreement and relevant project constraints.
2. Discuss the available alternatives.
3. Attempt to reach a team decision.
4. Consult the advisor if the disagreement affects project scope, feasibility, or technical direction.

Personal disagreements should not prevent the team from communicating necessary project information or completing required work.

---

## 14. Unequal Contribution

If a team member consistently does not complete agreed-upon responsibilities, the team will first address the issue directly with that member.

The team will attempt to determine whether the problem is caused by:

* Unclear expectations
* Unrealistic task assignments
* Technical blockers
* Scheduling conflicts
* Communication problems
* Other circumstances

If the issue continues despite attempts to resolve it, the team may involve the project advisor and/or course staff.

---

## 15. Advisor Interaction

Our advisor, Eric Jamison, will provide guidance throughout the two-semester project.

The team will meet with the advisor at least once every two weeks, or according to the schedule agreed upon with the advisor.

We will use advisor meetings to discuss:

* Project scope
* Technical and design decisions
* Project risks
* Progress and blockers
* Major changes to requirements
* Questions requiring external expertise

The team will provide the advisor with sufficient context before meetings when feedback or a decision is needed.

---

## 16. Project Constraints

The team recognizes the following constraints:

* **Economic:** The primary project cost is cloud computing and storage for ML inference and roadway data. Existing cameras and a borrowed vehicle will minimize hardware and transportation costs.

* **Professional:** The project requires expertise in machine learning, backend development, databases, and deployment. Technologies must remain manageable within the two-semester Senior Design timeline.

* **Ethical:** StreetSmart is intended to assist roadway monitoring, not make decisions affecting individuals. Automated pothole detections will therefore be treated as data requiring appropriate interpretation rather than definitive judgments.

* **Legal:** The team must ensure that any roadway imagery, datasets, pretrained models, and third-party software used by StreetSmart are permitted for project use.

* **Security:** StreetSmart will handle authentication information, geographic coordinates, roadway imagery, and detection data. JWT authentication, protected API endpoints, secure API keys, and encrypted network communication will be used to protect this data.

* **Social:** StreetSmart is designed to help roadway organizations identify and visualize potential potholes more efficiently. The interface should clearly distinguish automated detections from verified roadway conditions.

* **Environmental:** Environmental impact is not a primary project constraint, although the team will consider the computational cost of continuously processing roadway imagery.

* **Diversity and Cultural:** Diversity and cultural considerations are not expected to significantly affect the initial design. The system will prioritize clear and accessible visualization of roadway data.

The constraints most directly affecting the initial design are **economic, professional, ethical, and security**, particularly the trade-off between **cloud compute costs and the frequency of ML inference**.


---

## 17. Risk Management

The team will periodically identify risks involving:

* Technical feasibility
* Schedule
* Team availability
* Hardware/software dependencies
* External services
* Data availability
* Scope expansion
* Testing and deployment

When a significant risk is identified, the team will document the risk and determine an appropriate mitigation strategy.

---

## 18. Changes to This Contract

This contract may be updated when project circumstances require a change to team processes or responsibilities.

Changes should be discussed and agreed upon by the team before being incorporated into the official version.

Major changes will be communicated to the advisor when appropriate.

The final approved version will be maintained as **Version 1.0** and committed to the project repository.

---

## 19. Agreement

By approving this contract, team members agree to the responsibilities, communication practices, decision-making process, and project expectations described above.

**Team Members**

| Name       | Signature / Approval | Date   |
| ---------- | -------------------- | ------ |
| Raihan Rafeek | RR           | 09/16/2026 |
| Advait Vagerwal | AV           | 09/16/2026 |
| Sahil Thakare | SS           | 09/17/2026 |

**Advisor**

| Name           | Signature / Approval | Date   |
| -------------- | -------------------- | ------ |
| Eric Jamison | [Approval]           | [DATE] |
