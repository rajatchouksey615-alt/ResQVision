# AI Service Source

The source tree is reserved for the future video analysis pipeline. The subdirectories describe responsibilities only; no code or implementation contracts exist yet.

- core/: service-level configuration and orchestration boundaries.
- preprocessing/: video and frame input preparation.
- detection/: object and vehicle detection.
- tracking/: object tracking.
- verification/: temporal verification of accident candidates.
- evidence/: evidence selection and processing.
- api/: a service API if the reviewed architecture requires one.
- utils/: small shared utilities used by this service.

Keep candidate detection separate from verification. Document interfaces and test important pipeline behavior with controlled, privacy-safe fixtures.
