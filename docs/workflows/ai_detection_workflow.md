# AI Detection Workflow

**Status:** Proposed workflow; no detection or verification implementation exists.

~~~mermaid
flowchart TD
    A[Receive approved video and source context] --> B{Permission, format, and limits valid?}
    B -- No --> Z[Reject; record processing failure]
    B -- Yes --> C[Decode and sample frames]
    C --> D[Preprocess under privacy/resource constraints]
    D --> E[Object detection with provenance and timing]
    E --> F[Track objects where useful]
    F --> G[Evaluate temporal evidence]
    G --> H{Possible candidate?}
    H -- No --> I[Record no-candidate or uncertain outcome]
    H -- Yes --> J[Create candidate evidence and metadata]
    J --> K[Store media under approved restricted policy]
    K --> L[Submit authenticated candidate to backend]
    L --> M{Backend accepts event?}
    M -- No --> N[Classify rejection/retry/possible duplicate]
    M -- Yes --> O[Backend records DETECTED / UNDER_VERIFICATION]
    O --> P[Authorized human review under policy]
    P --> Q{Human verification outcome}
    Q -- Verified --> R[Backend may mark VERIFIED]
    Q -- Rejected --> S[Backend records REJECTED]
    Q -- Pending --> T[Remain UNDER_VERIFICATION]
~~~

## Stage Responsibilities

1. **Input validation:** Confirm approved source, supported format, duration/resource policy, and permission to process. Invalid input is a failure, not a no-accident result.
2. **Preprocessing:** Decode and sample frames under approved privacy, storage, and compute constraints.
3. **Detection:** Record relevant detections with confidence, timing, model/config provenance, and limitations when available.
4. **Tracking:** Associate objects across frames where useful; algorithm and identity policy remain TBD.
5. **Candidate evaluation:** Use documented evidence to identify a possible event. YOLO detections alone do not establish an accident.
6. **Temporal verification:** Assess sequence/context using a method and thresholds to be agreed. Preserve uncertainty and contradictory evidence.
7. **Evidence generation:** Create permitted evidence and metadata; store media only under approved provider, access, and retention policy.
8. **Event submission:** Authenticate the AI service at the backend; submit candidate evidence using a future reviewed contract.
9. **Human review:** An authorized human makes any required authoritative verification decision. Reviewer role and review SLA are TBD.

## Outcomes

| Outcome | Meaning | Backend/incident implication |
|---|---|---|
| Processing failure | Input, decoder, model, storage, or service could not complete | Must not be interpreted as no accident or verified incident |
| No candidate | Analysis completed but did not identify a candidate under the selected method | Retain only approved minimal processing outcome |
| Uncertain candidate | Evidence is incomplete or conflicting | Candidate may remain pending review; do not assign |
| Candidate | Possible event with evidence and provenance | Backend records DETECTED then UNDER_VERIFICATION |
| Verified incident | Authorized review criteria were met | Backend may allow assignment |
| Rejected candidate | Review determines the candidate does not meet approved criteria | Terminal for response assignment; correction/reopening policy TBD |

## Evaluation and Safety

Before implementation, select the model/version, tracking method, temporal windows, confidence handling, evaluation data, and decision criteria. Evaluate false positives and false negatives on approved labeled data and report limitations. Do not invent dataset size, accuracy, confidence thresholds, or real-time performance. A failed analysis must never silently become a verified incident.
