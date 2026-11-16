"""Video source registration and authorization operations."""

from .registry import (
    authorize_video_source,
    register_video_source,
    revoke_video_source,
    suspend_video_source,
    validate_source_for_ingestion,
)

__all__ = [
    "authorize_video_source",
    "register_video_source",
    "revoke_video_source",
    "suspend_video_source",
    "validate_source_for_ingestion",
]
