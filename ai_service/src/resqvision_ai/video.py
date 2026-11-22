"""Video ingestion boundary. OpenCV is optional and imported only when requested."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

from .errors import VideoIngestionError


@dataclass(frozen=True, slots=True)
class VideoFrame:
    index: int
    captured_at: datetime
    image: Any


class OpenCVVideoSource:
    """Bounded OpenCV reader for a configured file or stream locator."""

    def __init__(
        self,
        locator: str | int,
        *,
        max_frames: int = 10_000,
        cv2_module=None,
    ) -> None:
        if max_frames < 1:
            raise ValueError("max_frames must be positive")
        if isinstance(locator, str):
            parsed = urlsplit(locator)
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise VideoIngestionError(
                    "Video source credentials or query parameters must use a protected adapter."
                )
        self.locator = locator
        self.max_frames = max_frames
        self._cv2 = cv2_module

    def __iter__(self) -> Iterator[VideoFrame]:
        cv2 = self._cv2
        if cv2 is None:
            try:
                import cv2
            except ImportError as exc:
                raise VideoIngestionError("OpenCV is not installed in this runtime.") from exc
        capture = None
        try:
            capture = cv2.VideoCapture(self.locator)
            if not capture.isOpened():
                raise VideoIngestionError("The configured video source could not be opened.")
            for index in range(self.max_frames):
                ok, image = capture.read()
                if not ok:
                    break
                yield VideoFrame(index=index, captured_at=datetime.now(UTC), image=image)
        except Exception as exc:
            if isinstance(exc, VideoIngestionError):
                raise
            raise VideoIngestionError(
                "The configured video source failed while opening or decoding."
            ) from None
        finally:
            if capture is not None:
                capture.release()
