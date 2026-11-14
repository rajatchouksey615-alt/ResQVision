# AI Detection Workflow

**Status:** REVISED_DRAFT — pending team approval; no detection, source registry, or evidence-transfer implementation exists.

~~~mermaid
flowchart TD
    A[Register VideoSource and owner/policy] --> B{Source authorized?}
    B -- No --> Z[Reject; audit source denial]
    B -- Yes --> C[Receive controlled file or approved replaceable stream]
    C --> D[Validate format, resource limits, source time/location provenance]
    D --> E[Decode/sample and preprocess frames]
    E --> F[Detect relevant objects and preserve timing/confidence]
    F --> G[Track objects where useful]
    G --> H[Analyze temporal observations]
    H --> I{Detection observations emitted?}
    I -- No --> J[Record no-candidate or uncertain processing outcome]
    I -- Yes --> K[Create distinct DetectionEvent(s)]
    K --> L[Create EvidenceAsset metadata]
    L --> M[Request backend-scoped upload authorization]
    M --> N[Upload one authorized object; report completion]
    N --> O{Object, metadata, integrity and validation pass?}
    O -- No --> P[Keep FAILED/QUARANTINED; no retrieval]
    O -- Yes --> Q[EvidenceAsset AVAILABLE after required validation]
    Q --> R[Submit authenticated DetectionEvent(s)]
    R --> S{AI_SERVICE, source, event identity valid?}
    S -- No --> T[Reject safely; retry same identity only]
    S -- Yes --> U[Backend persists events and creates/associates AccidentCandidate]
    U --> V[Candidate RECEIVED then UNDER_REVIEW]
    V --> W[Authorized human reviewer decides]
    W --> X{Verified or rejected?}
    X -- Verified --> Y[Backend creates linked OPEN AccidentIncident]
    X -- Rejected --> AA[REJECTED candidate retained by policy; no incident]
~~~

## Stage Responsibilities

1. **Source registry:** Represent owner, source type, authorization status, location reference, input-config reference, timestamp provenance, processing policy, and retention policy. Registration authority is TBD.
2. **Input:** Support controlled approved files for academic demonstrations. RTSP/stream and camera-health support remain replaceable/open; source credentials stay in protected runtime configuration and never Git.
3. **Validation/preprocessing:** Validate source authorization, format, resource limits, timestamps, and policy; distinguish unavailable/invalid input from completed analysis with no observation.
4. **Detection/tracking:** Record each observation with source/event identity, timing, processing provenance, and confidence/uncertainty when available. Tracking is optional and method TBD.
5. **Event production:** AI creates distinct DetectionEvents. The backend, not the AI service, associates one or more events to a candidate. Same event ID is idempotent; candidate similarity is a separate reviewed rule.
6. **Evidence authorization:** AI submits DetectionEvent/evidence metadata; the backend associates the event to a candidate, creates a server-controlled EvidenceAsset reference, and grants short-lived, single-object, operation-scoped upload authorization where supported. Backend-mediated upload is fallback.
7. **Evidence validation:** Upload is PENDING_UPLOAD/UPLOADING then QUARANTINED while object identity, allowed type/size, integrity/checksum, and required scan are checked. Only validated asset becomes AVAILABLE; failures remain FAILED/QUARANTINED.
8. **Human verification:** Candidate states are RECEIVED, UNDER_REVIEW, VERIFIED, REJECTED. Authorized human alone verifies/rejects; AI temporal score is evidence, not authority.
9. **Incident creation:** Backend atomically creates a linked OPEN AccidentIncident only after authorized candidate verification; rejected candidates create no incident.

## Outcomes

| Outcome | Meaning | Backend/incident implication |
|---|---|---|
| Processing failure | Input, decoder, model, backend, storage, upload, or validation did not complete | Separate failure outcome; no candidate/incident inferred; retry/reconciliation policy applies |
| No DetectionEvent | Analysis completed without an observation under the selected method | No candidate/incident; retain minimal approved processing outcome |
| DetectionEvent | One machine-generated observation with source/time/provenance | Backend intake outcome is accepted, rejected, or duplicate-safe; event is distinct |
| AccidentCandidate | Backend associates one or more distinct events and evidence | Candidate RECEIVED/UNDER_REVIEW; not an incident and not assignable |
| VERIFIED candidate | Authorized human review satisfied approved policy | Backend atomically creates one linked OPEN AccidentIncident |
| REJECTED candidate | Authorized human rejected it | Retained for approved audit/evaluation; no incident or assignment |
| EvidenceAsset | Media reference with independent transfer/validation lifecycle | Only AVAILABLE is retrievable; other states are unavailable |

## Evaluation and Safety

Before implementation, select model/version, tracking method, temporal windows, confidence handling, evaluation data, candidate-grouping rules, verification criteria, input mode, evidence limits/validation, and retention. Evaluate false positives/negatives on approved labeled data. Do not invent dataset size, accuracy, confidence thresholds, or real-time performance. Camera coordinates must not be asserted as exact accident location; preserve location source, timestamp, uncertainty, verification, and correction history. A failed analysis or AI score must never silently become a verified candidate or incident.
