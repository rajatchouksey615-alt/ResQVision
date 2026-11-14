# Requirements Traceability

**Status:** Draft planning baseline. Test cases are planned, not implemented or executed.

| Requirement | Capability / component | Workflow | Acceptance coverage | Planned test coverage | Phase | Status |
|---|---|---|---|---|---|---|
| FR-001 | Backend identity; mobile authentication UI | User-role UC-01 | Valid account access; invalid/disabled account denied | Unit, API, client integration | Backend/mobile foundation | Draft |
| FR-002 | Backend user and role administration | UC-05 | Admin-only account changes; supported roles; audit | API authorization and domain tests | Backend foundation | Draft |
| FR-003 | AI input validation and source policy | AI workflow; UC-02 | Unauthorized/invalid source rejected distinctly | AI unit and ingestion integration | AI foundation | Draft |
| FR-004 | Detection, tracking, candidate event | AI workflow; UC-02/06 | Provenance and uncertainty retained; no false certainty | AI evaluation and event contract tests | AI detection | Draft |
| FR-005 | Verification workflow and review UI/backend | Incident workflow; UC-03 | AI score alone cannot verify; decision is auditable | Domain transition and reviewer-permission tests | Verification | Draft |
| FR-006 | Evidence metadata and object storage boundary | System and data-flow workflows; UC-04 | No public media access; scoped retrieval | Storage authorization and expiry tests | Evidence | Draft |
| FR-007 | Backend incident service and PostgreSQL | System/incident workflows; UC-06/09 | Authoritative record; invalid transition denied; duplicates handled | Domain and database integration | Incident management | Draft |
| FR-008 | Assignment service and Admin UI | Incident workflow; UC-05 | Only verified incidents assigned; action audited | Permission and state-transition tests | Response coordination | Draft |
| FR-009 | Notification simulation component | System workflow; UC-07 | Simulation labeled; no live emergency contact | Configuration and end-to-end safety tests | Prototype integration | Draft |
| FR-010 | Location metadata and optional map UI | Data flow; user-role workflows | Unknown precision disclosed; no fabricated location | Data validation and client fallback tests | Mobile integration | Draft |
| FR-011 | Police client view and response service | User-role workflow; UC-04 | Scope enforced; permitted response changes audited | API permission and mobile workflow tests | Response coordination | Draft |
| FR-012 | Hospital client view and readiness service | User-role workflow; UC-04 | Minimized scope; readiness changes audited | API permission and mobile workflow tests | Response coordination | Draft |
| FR-013 | Admin client and backend capabilities | User-role workflow; UC-05 | Admin actions permission-checked and audited | API and role workflow tests | Admin capabilities | Draft |
| FR-014 | Backend history/audit query and client | UC-08 | Scoped, ordered, non-editable history | API scope and integrity tests | Incident management | Draft |
| FR-015 | Backend aggregate reporting | UC-08 | Reports label scope and limitations | Aggregation correctness/privacy tests | Later prototype increment | Draft |
| FR-016 | Audit/event logging across backend | All workflows | Actor/time/outcome recorded without secrets | Audit persistence and redaction tests | Cross-cutting | Draft |
| NFR-001–005 | Identity, authorization, validation, service boundaries | UC-01/05/06 | Authenticated protected calls; safe errors | Security/API test suite | Backend foundation | Draft |
| NFR-006–008 | Evidence, privacy, and audit controls | UC-03/04/08 | Restricted media and attributable actions | Security/privacy review and integration tests | Cross-cutting | Draft |
| NFR-009–010 | Persistence, idempotency, failure isolation | UC-02/06/09 | No silent verification or unintended duplicate work | Domain and fault-injection tests | Cross-cutting | Draft |
| NFR-011–018 | Availability, performance, scalability, maintainability, UX, compatibility, recovery | All | Targets or matrices approved before claims | Environment-specific checks after targets are set | Deployment readiness | Open/Draft |
| NFR-019 | AI evaluation | AI workflow; UC-02/09 | Approved data, documented false positive/negative measures | Reproducible evaluation protocol | AI evaluation | Draft |
| NFR-020 | Prototype safety | System and incident workflows; UC-07 | No real emergency action | End-to-end safety review | All prototype phases | Draft |

## Traceability Notes

- Acceptance evidence in this table refers to future test scenarios; it is not evidence that a test has run.
- Detailed API schemas, field-level data models, and concrete test IDs are deferred until contracts and implementation owners are agreed.
- Requirements with proposed authority or TBD targets must be resolved or explicitly accepted as deferred before the affected feature is implemented.
