# Location Provenance Policy

**Decision status:** Provenance safeguards are modeled; authority, access, and display policy remain unresolved.  
**Related existing decisions:** OAD-001, OAD-020.  
**Related requirements:** FR-010, FR-029; NFR-007, NFR-024.

## Location Claim Types and Current Support

| Claim concept | Meaning | Current model support | Governance status |
|---|---|---|---|
| Camera position | Location of the video source/camera installation. | `CAMERA_POSITION`, scoped to a VideoSource; source method can be camera, GPS, or manual. | Do not display as accident location. Source-owner scope and precision remain open. |
| AI-reported/inferred accident location | Estimate associated with a candidate, derived from an event/video. | `ACCIDENT_LOCATION` + `INFERRED`; AI_SERVICE may create this only for a candidate and cannot create incident-level claims. | Accuracy and reviewer interpretation rules need approval. |
| GPS accident location | Accident-location claim originating from GPS metadata. | `ACCIDENT_LOCATION` + `GPS` is representable; source event/source references and `accuracy_m` can be retained. | Device/source trust, timestamp quality, and authorized use are unresolved. |
| Externally reported accident location | Human/source-submitted claim, distinct from model inference. | Not a distinct source method. `MANUAL` exists but does not encode reporter identity/type or external report provenance as a separate claim class. | Gap: define a first-class origin/report reference before relying on it. |
| Human-verified/corrected location | Human marks a current claim verified or corrects coordinates/accuracy with rationale. | `UNVERIFIED`, `VERIFIED`, `CORRECTED`; `LocationCorrectionHistory` records old/new coordinates and accuracy, actor, time, and reason. | Human role and correction scope remain unresolved; no API is enabled. |

`captured_at` and `accuracy_m` are nullable. Unknown capture time or accuracy must stay unknown. Six decimal coordinate places are a storage type, not proof of six-decimal accuracy.

## Provenance Requirements

For each claim preserve the typed subject (`VideoSource`, candidate, or incident), claim kind, source method, source VideoSource and/or DetectionEvent where applicable, original capture timestamp, coordinates, accuracy/uncertainty, creating human/service, verification status/actor/time, and correction history. A location value without known provenance is not a verified accident location.

Never convert a camera position into an accident location by copying coordinates. Candidate-level AI claims remain estimates until a human authority verifies them. A human correction updates the current row but keeps before/after coordinate and accuracy values in correction history; the existing correction history does not by itself create a competing independent claim.

## Authority and Access Matrix

| Action | Recommendation | Preconditions | Current status |
|---|---|---|---|
| Create camera-position claim | Source registry/data custodian or an explicitly authorized human service | Active, authorized VideoSource; source matches subject; provenance retained. | Service supports policy hook; no approved role/API. |
| Create inferred candidate claim | AI_SERVICE for its own authorized event/candidate only | Authenticated machine identity; claim is `ACCIDENT_LOCATION` + `INFERRED`; require a linked event under the recommended policy. | Service enforces claim kind/method/candidate shape and validates event association if an event is supplied; event reference is not currently mandatory. Machine auth is unconfigured and no API is enabled. |
| Create incident-level accident claim | Explicit human-authorized location steward | Verified incident and traceable source; no camera-position substitution. | Human service policy hook exists; API unavailable. |
| Verify a claim | Designated human verifier, with scope separate from mere view | Current, unverified claim; reason/evidence context as approved. | Service hook exists; no approved role/API. |
| Correct a claim | Designated human location steward; require nonblank rationale | Current claim; valid coordinate ranges; a real change; capture old/new values and actor/time. | Service checks rationale and records correction history; authority unresolved/API unavailable. |
| Read/display location | Explicitly scoped human access; minimize precision based on role/purpose | Active incident/assignment and approved precision/display policy. | Location endpoint returns 503; no location in incident summary. |
| AI_SERVICE read/correction | Prohibited | Machine may submit its own inferred candidate claim only; cannot verify or correct. | Enforced in service model for claim creation; no read/correction permission. |

No global role or organization membership alone should authorize all precise location claims. Hospital and Police visibility may require different precision; no such rule is approved.

The AI_SERVICE location capability above describes a narrow domain-service path, not an active API grant. The current service does not apply an `AuthorizationPolicy` to machine claim creation, and it does not require an event reference. Keep the route unavailable until OAD-017 and OAD-020 approval; before enabling it, require a trusted machine actor, source/event provenance, candidate association, and an explicit machine capability policy.

## Conflicting Claims, Correction, and History

The schema permits one `is_current` claim per typed subject. The current service creates a current claim and corrects coordinates/accuracy in place while recording a before/after correction row. It has no explicit workflow for retaining two simultaneous competing current accident claims or adjudicating conflicts between manual, inferred, GPS, or external reports. Recommend preserving each source claim as distinct history and designating an authorized human to select/correct the current claim, but the schema/service flow must be reviewed before implementation.

Corrections must not silently alter source method, source event, or capture timestamp. A change to those provenance facts should require a new, linked claim/history operation after design approval. Keep the original value and correction rationale available under the approved retention policy.

## Precision, Display, and Safety

Use only supplied coordinates and accuracy. Do not round into false confidence or infer accuracy from decimal precision. When claim status is unverified or accuracy is unknown, label it plainly. Camera position must be labeled “camera location.” Inferred accident location must be labeled as an estimate. Map provider is unselected under OAD-001; no provider or map SDK is implied.

## Decisions Required Before Enablement

Approve location claim ownership and source permission; allowed origin types and required provenance; verifier/corrector role and scope; location field visibility and precision for each role; conflict and supersession policy; capture-time quality rules; history retention; and map/provider disclosure. Until approval, location APIs remain blocked and clients must not display coordinates.
