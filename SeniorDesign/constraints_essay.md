# StreetSmart Constraints

**Team Members:** Advait Vagerwal, Sahil Thakare, Raihan Rafeek

## Economic

Cloud computing and storage are expected to be StreetSmart's primary recurring costs, while the team already has access to a camera and can borrow a vehicle for testing. This makes reducing unnecessary ML inference and data storage an important design consideration.

## Security

StreetSmart will process roadway imagery, geographic coordinates, authentication information, and pothole detection data, requiring JWT-based authentication and protected API endpoints. The system will also avoid retaining unnecessary personally identifiable information that may appear in roadway imagery.

## Ethical
StreetSmart's ML model may produce false positives or false negatives, so StreetSmart will store a model confidence score and track repeated detections of the same pothole location, allowing users to assess the reliability of reported roadway conditions. This provides additional context for prioritizing detections and reduces reliance on a single automated prediction.


## Professional

The project requires machine learning, backend, database, and deployment expertise within a two-semester Senior Design timeline. The team will therefore prioritize technologies that can be reliably implemented and maintained within the project's time and technical resources.

The primary trade-off is between **economic cost and detection coverage**, since processing more roadway frames can improve the opportunity to detect potholes but increases cloud computing and storage costs.