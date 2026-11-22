# ResQVision AI Service

This package implements the event-processing and Django transport boundaries. It does not include a trained accident model, model weights, production machine identity, source grants, or a live camera configuration. Repository inspection found no existing YOLO/OpenCV/PyTorch pipeline to reuse, so model inference is a pluggable adapter; the optional Ultralytics adapter uses a model path supplied by the operator.

## Processing Layout

- `src/resqvision_ai/video.py` ingests bounded OpenCV frames and records UTC timestamps.
- `detectors.py` defines the optional Ultralytics YOLO adapter; no model is bundled.
- `pipeline.py` applies an explicitly configured confidence threshold, produces observation events, and writes them to a sink.
- `contracts.py` validates the `/api/v1/ai/detection-events/` v1 contract and refuses Police, reviewer, verification, candidate, or incident authority fields in metadata.
- `outbox.py` persists pending event payloads in SQLite so transport failures survive process restarts.
- `client.py` submits the same event identity with bounded timeout/retry behavior. It has no default authenticator and fails closed.
- `publisher.py`, `service.py`, and `health.py` provide delivery orchestration and safe readiness reporting.

The AI service emits observations only. The confidence field is the detector's score for the reported class, not an accident probability or verification. It does not create or select `AccidentCandidate` records, verify accidents, create `AccidentIncident` records, choose Police organizations/reviewers, or trigger notifications or dispatch. The backend remains authoritative for source authorization and event idempotency.

## Configuration

`AIServiceConfig.from_environment()` requires all of these values; no confidence threshold or model version is assumed:

| Variable | Purpose |
|---|---|
| `RESQVISION_VIDEO_SOURCE_ID` | Existing registered VideoSource UUID |
| `RESQVISION_MODEL_NAME`, `RESQVISION_MODEL_VERSION` | Detector provenance |
| `RESQVISION_CONFIDENCE_THRESHOLD` | Explicitly selected score cutoff in `[0, 1]` |
| `RESQVISION_OBSERVATION_LABELS` | Comma-separated model labels eligible to produce an event |
| `RESQVISION_MODEL_PATH` | Operator-provided model file |
| `RESQVISION_BACKEND_BASE_URL` | Backend origin; HTTPS required outside loopback |
| `RESQVISION_OUTBOX_PATH` | Local SQLite pending-event store |
| `RESQVISION_REQUEST_TIMEOUT_SECONDS` | Optional request timeout, default 5 seconds |
| `RESQVISION_REQUEST_RETRY_ATTEMPTS` | Optional bounded attempts, default 3 |
| `RESQVISION_RETRY_BACKOFF_SECONDS` | Optional exponential backoff base, default 0.25 seconds |

The library depends on the Python standard library for its core contract, outbox, health, and transport code. OpenCV and Ultralytics are imported only if their adapters are used. Select and pin compatible OpenCV, Ultralytics, and PyTorch versions only after the model, license, runtime, and hardware are approved. No dependency installation or model download is performed by this repository.

## Authentication and Local Integration

Production submission stays disabled unless a separately approved machine authenticator is injected into `BackendEventClient`. Human JWT is never used. The backend's `TestMachineCredentialAuthenticator` and this package's `ExplicitTestMachineTokenAuthenticator` are for isolated tests only; both require explicit test configuration and a caller-provided test token. No token is stored in source or logged.

The Django endpoint accepts only v1 observation payloads and its domain service requires the referenced `VideoSource` to be authorized and available. Authentication and source checks occur before persistence. Same-source event replays are idempotent; reuse of an event ID with different content is a conflict. Ingestion creates only `DetectionEvent`; candidate and Police review workflows remain separate.

Run the local simulated integration checks from the repository root:

```powershell
python -m pytest ai_service\tests -q
backend\.venv\Scripts\python.exe -m pytest backend\api\tests\test_ai_service_integration.py -q
```

The AI tests generate synthetic frame detections and never require CCTV, a real model, or a backend credential. The Django integration test injects the explicit test-only machine authenticator and passes a simulated event through the AI client into the API, verifying source authorization, idempotent replay, and that no candidate is created during event intake.

For service deployment, configure approved source/model values, provide an external model file and reviewed dependencies, supply an approved machine authenticator, monitor the health report and outbox queue, and define local outbox protection/retention. Until those approvals and operational dependencies exist, the AI pipeline is not production-ready.
