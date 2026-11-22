# AI Detection Workflow

**Status:** REVISED_DRAFT — pending team approval. The AI event contract, pluggable frame pipeline, local outbox, and Django event-intake adapter are implemented. No trained detector/model, production machine authentication, source registry API, or evidence-transfer implementation is available.

~~~mermaid
flowchart TD
    A[Registered VideoSource] --> B{Source authorized and available?}
    B -- No --> Z[Do not process or accept event]
    B -- Yes --> C[Receive configured video input]
    C --> D[Decode bounded UTC-timestamped frames]
    D --> E[Run explicitly configured detector]
    E --> F{Detection score meets configured threshold?}
    F -- No --> G[Continue; no DetectionEvent]
    F -- Yes --> H[Generate v1 observation and provenance]
    H --> I[Persist event in local SQLite outbox]
    I --> J{Approved AI_SERVICE authenticator configured?}
    J -- No --> K[Remain queued; report not ready]
    J -- Yes --> L[POST /api/v1/ai/detection-events/]
    L --> M{Machine identity, source state, and payload valid?}
    M -- No --> N[Report safe error; retain for bounded retry or operator recovery]
    M -- Yes --> O[Backend idempotently stores DetectionEvent only]
    O --> P[Separate backend candidate-intake policy, if approved]
    P --> Q[Authorized human reviewer decides]
    Q --> R{Verified or rejected?}
    R -- Verified --> S[Backend creates linked OPEN AccidentIncident]
    R -- Rejected --> T[Rejected candidate retained; no incident]
~~~

## Stage Responsibilities

1. **Source registry:** Represent owner, source type, authorization status, location reference, input-config reference, timestamp provenance, processing policy, and retention policy. Registration authority is TBD.
2. **Input:** Support controlled approved files for academic demonstrations. RTSP/stream and camera-health support remain replaceable/open; source credentials stay in protected runtime configuration and never Git.
3. **Validation/preprocessing:** Validate source authorization, format, resource limits, timestamps, and policy; distinguish unavailable/invalid input from completed analysis with no observation.
4. **Detection/tracking:** Record each observation with source/event identity, timing, processing provenance, and confidence/uncertainty when available. Tracking is optional and method TBD.
5. **Event production and submission:** AI generates a versioned v1 observation with source UUID, external event reference, UTC timestamp, model provenance, detector score, metadata, and payload digest. A SQLite outbox retains events across transport failure. The Django ingestion service requires an authenticated AI_SERVICE actor and a source that is authorized and available. Identical event replays are idempotent; changed content under the same identity is rejected.
6. **Candidate and evidence boundary:** DetectionEvent intake does not create candidates, select Police organizations/reviewers, verify accidents, create incidents, or submit evidence. Candidate association and evidence transfer require separate approved backend policies and endpoints.
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
