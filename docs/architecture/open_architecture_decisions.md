# Open Architecture Decisions

**Status:** Open register for team review. Entries are not accepted decisions. Use [ADR_TEMPLATE.md](../decisions/ADR_TEMPLATE.md) when a significant choice is approved.

| ID | Decision | Options to assess | Main trade-offs and dependencies | Status |
|---|---|---|---|---|
| OAD-001 | Maps provider and location display | Provider SDK, open mapping service, static location summary without map | Licensing, privacy/precision, offline behavior, key restrictions, platform support | TBD |
| OAD-002 | Object storage provider | Local development-compatible store, managed cloud object storage, institution-provided storage | Access controls, cost, retention/lifecycle, data residency, signed access, operations | TBD |
| OAD-003 | AI model and version | Candidate YOLO versions/models or another reviewed detector | License, supported classes, compute needs, reproducibility, approved evaluation data | TBD |
| OAD-004 | Object tracking method | Detector-only temporal association, classical tracker, learned tracker | Complexity, identity stability, compute cost, occlusion behavior, evaluation burden | TBD |
| OAD-005 | Accident verification method | Rules over temporal evidence, learned temporal model, hybrid approach with human review | Explainability, false positives/negatives, required labels, threshold calibration, reviewer workload | TBD |
| OAD-006 | Video ingestion approach | Controlled files, local stream adapter, approved camera integration | Source permissions, network/security exposure, buffering, resource limits, privacy | TBD |
| OAD-007 | Notification delivery strategy | Simulated backend records, in-app prototype notification, later push-provider adapter | Prototype safety, delivery observability, credentials, retries, provider terms; live emergency delivery prohibited in prototype | Simulated only for prototype; later choice TBD |
| OAD-008 | AI/backend communication | Synchronous authenticated API, asynchronous queue/event broker, controlled file handoff | Latency, retry/deduplication, coupling, service identity, infrastructure complexity | TBD |
| OAD-009 | Deployment provider and topology | Local-only demonstration, institution-managed environment, selected cloud environment | Data handling, cost, network boundaries, operations, backups, regional/legal constraints | TBD |
| OAD-010 | Flutter state management | Framework-native state, Provider, Riverpod, Bloc, or another reviewed package | Team familiarity, testability, dependency support, complexity | TBD |
| OAD-011 | Background processing | In-process prototype worker, task queue, managed job runner | Reliability, retries, workload, deployment complexity, operational observability | TBD |
| OAD-012 | Human verification authority and scope | Designated Admin reviewers, separate reviewer role, approved human review group | Accountability, separation of duties, workload, access to evidence, institutional approval | TBD |
| OAD-013 | Incident assignment policy | Manual Admin assignment, rules-based proposal with human confirmation, another reviewed policy | Jurisdiction/eligibility data, fairness, explainability, operational ownership | TBD |
| OAD-014 | Retention and evaluation data policy | Short-lived controlled media, selected evidence-only retention, approved research dataset process | Source permissions, privacy, deletion, reproducibility, institutional rules | TBD |

## Review Process

For each decision, name an owner, compare credible options, record security/privacy and maintenance consequences, identify dependencies, and create an ADR when accepted. Do not treat this register or the planned technology stack as provider approval.
