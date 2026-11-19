# Candidate Review and Verification Policy

**Decision status:** Proposed; reviewer authority and decision criteria require explicit approval.  
**Related existing decisions:** OAD-005, OAD-012, OAD-015.  
**Related requirements:** FR-004, FR-005, FR-017, FR-018, FR-019; NFR-002, NFR-008, NFR-009, NFR-019.

## Recommendation

Use a designated human reviewer cohort with explicit action permissions and an explicit candidate scope. The authority must be granted independently for candidate visibility, review initiation/annotation, and final verification or rejection. Do not infer these powers from a generic `ADMIN`, `POLICE`, or `HOSPITAL` group. `ADMIN` is one candidate for the reviewer cohort in existing draft requirements; it is not an approved default. Police and Hospital users have no candidate-review permission unless stakeholders explicitly approve a scoped additional responsibility.

For the prototype, recommend one authorized human final decision per candidate, after review of the available event provenance and approved evidence. A single-reviewer rule is easier to operate and matches the current `CandidateReview` uniqueness constraint. Whether high-risk/ambiguous cases need a second reviewer remains a stakeholder decision.

For reviewer assignment, recommend that a separately authorized queue coordinator assign one reviewer of record from the approved cohort to each candidate. Do not assume that coordinator is an Admin. The assigned reviewer may act only within the approved candidate scope; reassignments require a recorded reason and audit. If the team does not approve a coordinator/assignment model, the queue must remain disabled rather than silently allowing any role member to claim all candidates.

## Authority and Scope Matrix

| Action | Recommended authority | Scope and preconditions | Current code/API evidence | Status |
|---|---|---|---|---|
| Read candidate queue | Designated reviewer cohort only | Candidate must have event provenance and be `RECEIVED` or `UNDER_REVIEW`; scope must be explicitly defined, preferably by an approved source/organization relationship. | Domain selector exists behind `candidate.read_queue`; API is blocked and default policy denies. Candidate has no reviewer-assignment entity. | Blocked pending OAD-012. |
| Read candidate detail/evidence references | Reviewer with candidate read permission | Same candidate scope; metadata fields and any media need separate authorization. | `get_candidate` uses policy hook; API returns 503. Evidence is separately blocked. | Blocked/unresolved. |
| Start review | Explicitly authorized human reviewer | Candidate `RECEIVED`, event provenance exists, and actor is within candidate scope. | Service transitions `RECEIVED → UNDER_REVIEW`, locks candidate, and audits; API is blocked. | Blocked pending approval. |
| Annotate/revise a review | Not enabled by current model; recommend immutable review annotations as separate records if required. | Define whether prior notes are editable, append-only, or superseded before implementation. | `CandidateReview` is one final-decision record; no annotation/revision history model is present. | Unresolved. |
| Verify | Explicitly authorized human verifier; recommendation is reviewer cohort | Candidate must be `UNDER_REVIEW`, have at least one associated event, pass an approved checklist, and be within actor scope. | `verify_candidate` accepts policy injection; default policy denies. Rationale is currently optional. API is blocked. | Blocked; OAD-012. |
| Reject | Same or separately approved human verifier | Candidate `UNDER_REVIEW`; nonblank rationale required by current service/model. No incident is created. | `reject_candidate` writes a final review and `REJECTED`; default policy denies; API is blocked. | Blocked; authority unresolved. |
| Dismiss | No permission recommended at present | Do not add until dismissal has a distinct meaning from false-positive rejection, with retention and reporting rules. | No `DISMISSED` state or command exists. | Not applicable to current lifecycle; future decision unresolved. |
| AI_SERVICE decision | Prohibited | Machine may submit observations and evidence only; no review, verification, rejection, or candidate visibility beyond any narrowly defined own-submission receipt. | `require_human` guards final decisions; machine auth itself is unconfigured. | Not applicable/prohibited. |

## Candidate Lifecycle

The current and recommended MVP lifecycle is:

~~~mermaid
stateDiagram-v2
    [*] --> RECEIVED: backend accepts event association
    RECEIVED --> UNDER_REVIEW: authorized review begins
    UNDER_REVIEW --> VERIFIED: authorized human final decision
    UNDER_REVIEW --> REJECTED: authorized human final decision with rationale
    VERIFIED --> [*]: one linked OPEN incident created atomically
    REJECTED --> [*]: retained under approved retention policy
~~~

`NEEDS_EVIDENCE`, `DISMISSED`, duplicate-merged, and reopened states are not part of the current model. If evidence is insufficient, recommend leaving the candidate `UNDER_REVIEW` and recording a safe, attributable reason. Add a new state only after the team defines actor, visibility, transition, notification, and retention semantics.

## Verification Evidence and Rationale

Recommend a documented reviewer checklist that records, at minimum:

- one or more validated, associated DetectionEvents and their source/time provenance;
- the evidence and uncertainty actually available to the reviewer, without treating model confidence as a decision;
- whether information is missing, contradictory, stale, or unverified;
- a nonblank rationale for both `VERIFIED` and `REJECTED` outcomes;
- reviewer identity, timestamp, candidate state before/after, linked incident ID when verified, and command ID.

The requirements describe reviewing temporal evidence and source/evidence provenance and submitting a decision/rationale, but do not establish a specific threshold or evidence sufficiency standard. The service currently checks event provenance exists; it does not require a linked EvidenceAsset or nonblank verification rationale. A checklist and rationale rule must be approved before the API is enabled.

## Conflicting and Concurrent Reviews

The current technical behavior is deterministic: candidate row lock serializes final decisions; only `UNDER_REVIEW` may be finalized; one final `CandidateReview` and one incident per candidate are constrained; reusing a command ID with different intent is rejected. Recommend treating the first valid committed final decision as authoritative and rejecting a later competing final command as stale/conflict. Do not silently overwrite the first review. If a second-review requirement is approved, the schema and transition contract must change before implementation.

Starting review also locks the candidate and rejects a second start while already `UNDER_REVIEW`. No reviewer assignment or claim/lease timeout exists. The team must decide whether any reviewer in the authorized cohort may start and finalize, or whether assignment/claim ownership is required.

## Duplicate Candidates and Event Grouping

Event-level idempotency uses the stable source/event identity; retrying that same event does not create a second event. Similar but distinct events can be associated to one candidate only under an approved grouping policy, and one event cannot belong to two candidates. The repository does not implement candidate-to-candidate merge, duplicate dismissal, or incident merge. Recommend keeping potentially duplicated candidates distinct until an authorized human resolves the relationship under an approved, audited workflow; never silently merge or discard provenance.

## Rejection, Correction, and Retention

Recommend retaining a rejected candidate and its DetectionEvent/evidence links and audit trail through the approved retention period. Do not erase a false positive from evaluation history by deleting it. A later correction or reversal must be a separately approved, auditable command; the current unique final-review rule does not support revision or reopening.

## Required Approvals

The project team must approve reviewer identity/role, scope, review assignment or queue rules, one versus multiple final reviewers, the verification checklist, whether verification rationale is mandatory, conflict handling, candidate visibility, and treatment of insufficient/contradictory evidence. Domain stakeholders must approve any Police/Hospital review role and evidence fields they may see. Institutional data governance must approve retention and use of rejected cases for evaluation.
