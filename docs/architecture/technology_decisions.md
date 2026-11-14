# Technology Decisions

**Status:** REVISED_DRAFT — planned stack and recommendations pending team approval.

This is an index of the current planned stack and unresolved choices. A planned technology is not a claim that it is implemented or that a version/provider is approved. Record accepted significant choices as [architecture decision records](../decisions/README.md).

## Planned Stack

| Area | Current direction | Status and implication |
|---|---|---|
| Mobile | Flutter and Dart | Planned; SDK and state management TBD |
| Backend | Python, Django, Django REST Framework | Planned; versions and service topology TBD |
| Structured data | PostgreSQL | Planned; logical entities may be described, schema not approved |
| AI and vision | Python, YOLO, OpenCV, PyTorch, NumPy | Planned; model/version, tracking, thresholds, and evaluation method TBD |
| Authentication | JWT and role-based access | Required direction; token lifecycle and service identity design TBD |
| Push notification | Firebase Cloud Messaging | Planned only; no credentials or live delivery configured; prototype remains simulated |
| Maps | No provider selected | Provider, terms, precision, and disclosure policy TBD |
| Object storage | No provider selected | Media provider, access mechanism, retention, and deletion TBD |
| Local development | Docker | Planned; configuration not created |
| Deployment | No provider selected | Hosting, topology, operations, and recovery objectives TBD |
| License | No license selected | Team and institutional approval required |

## Architectural Implications

- Keep service boundaries provider-neutral until a decision is recorded.
- Treat backend authorization and incident state as authoritative regardless of client or AI technology.
- Keep raw evidence out of PostgreSQL and the public repository.
- Do not infer model capability, real-time performance, or accuracy from the selected tooling names.

## Open Choices

See [open architecture decisions](open_architecture_decisions.md) for alternatives and trade-offs covering the map provider, storage, model, tracking, verification, video ingestion, notification strategy, backend/AI communication, deployment, mobile state management, and background work.
