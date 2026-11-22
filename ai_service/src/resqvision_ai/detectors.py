"""Optional detector adapters. No model or detector is bundled with this package."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import ModelUnavailable


@dataclass(frozen=True, slots=True)
class FrameDetection:
    label: str
    confidence: float
    box_xyxy: tuple[float, float, float, float] | None = None


class UltralyticsYoloDetector:
    """Adapt an explicitly supplied Ultralytics YOLO model to the pipeline protocol."""

    def __init__(self, model_path: Path | str, *, yolo_factory=None) -> None:
        path = Path(model_path)
        if not path.is_file():
            raise ModelUnavailable("The configured YOLO model file is unavailable.")
        if yolo_factory is None:
            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise ModelUnavailable("Ultralytics is not installed in this runtime.") from exc
            yolo_factory = YOLO
        try:
            self._model = yolo_factory(str(path))
        except Exception as exc:
            raise ModelUnavailable("The configured YOLO model could not be loaded.") from exc

    def infer(self, image: Any) -> list[FrameDetection]:
        try:
            results = self._model.predict(source=image, conf=0.0, verbose=False)
            observations: list[FrameDetection] = []
            for result in results:
                boxes = getattr(result, "boxes", None)
                if boxes is None:
                    continue
                names = getattr(result, "names", {})
                for box in boxes:
                    class_id = int(box.cls[0].item())
                    confidence = float(box.conf[0].item())
                    coordinates = tuple(float(part) for part in box.xyxy[0].tolist())
                    observations.append(
                        FrameDetection(
                            label=str(names.get(class_id, class_id)),
                            confidence=confidence,
                            box_xyxy=coordinates,
                        )
                    )
            return observations
        except Exception as exc:
            raise ModelUnavailable("The configured YOLO model failed during inference.") from exc
