# AI Service

The planned AI service uses Python, YOLO, OpenCV, PyTorch, and NumPy to process video, detect and track objects, identify accident candidates, apply temporal verification, and generate evidence. No model, pipeline, API, or runtime dependencies are configured yet.

## Safety and Data Boundaries

- An AI output is a candidate and must not be treated as a confirmed accident without verification logic.
- Do not commit large model weights, datasets, private CCTV recordings, or real personal data.
- Dataset licensing, provenance, privacy, and permitted use must be reviewed before acquisition or evaluation.
- Evidence metadata and files must use backend-approved contracts and storage policies.
- No real emergency integration is in scope without explicit authorization.

## Future Setup

The files under `requirements/` are placeholders. Select compatible, pinned dependencies and document supported hardware and runtime assumptions as part of AI service implementation. Organize source by pipeline responsibility without introducing unnecessary frameworks.

See the [source organization](src/README.md), [configuration conventions](configs/README.md), [dataset policy](datasets/README.md), and [AI detection workflow](../docs/workflows/ai_detection_workflow.md).
