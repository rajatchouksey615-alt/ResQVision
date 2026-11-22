# AI Service Source

Python source is under `resqvision_ai/` and is grouped by responsibility:

- `video.py`: frame ingestion and timestamps.
- `detectors.py`: optional model adapters.
- `pipeline.py`: thresholding and observation event generation.
- `contracts.py`: v1 payload schema and validation.
- `client.py`: backend transport and injected machine-authenticator boundary.
- `outbox.py` and `publisher.py`: durable local retries and recovery.
- `service.py` and `health.py`: composition and safe readiness reporting.

No trained weights or active detector are included. Keep event intake separate from candidate association and human verification. See the package [README](../README.md) for security and local integration details.
