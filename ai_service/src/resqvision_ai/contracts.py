"""Validated, versioned transport contract for AI observation events."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from .errors import ContractValidationError

AI_EVENT_CONTRACT_VERSION = "v1"
METADATA_SCHEMA_VERSION = 1
MAX_METADATA_BYTES = 16_384
_FORBIDDEN_METADATA_KEYS = {
    "candidate_id",
    "candidate_status",
    "decision",
    "incident_id",
    "incident_status",
    "police_org_id",
    "police_organization_id",
    "review_decision",
    "reviewer",
    "reviewer_id",
    "verification",
    "verification_status",
    "verified",
}


def _validate_metadata_tree(value: Any) -> None:
    pending = [(value, 0)]
    visited = 0
    while pending:
        node, depth = pending.pop()
        visited += 1
        if depth > 16 or visited > 4096:
            raise ContractValidationError("Metadata nesting or item count exceeds the v1 limit.")
        if isinstance(node, dict):
            for key, nested in node.items():
                if not isinstance(key, str):
                    raise ContractValidationError("Metadata object keys must be strings.")
                if key.casefold() in _FORBIDDEN_METADATA_KEYS:
                    raise ContractValidationError("Metadata cannot carry backend authority fields.")
                pending.append((nested, depth + 1))
        elif isinstance(node, list):
            pending.extend((nested, depth + 1) for nested in node)


def _normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ContractValidationError("detected_at must include a timezone.")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class DetectionEventPayload:
    video_source_id: UUID
    external_event_id: str
    model_name: str
    model_version: str
    detected_at: datetime
    processing_outcome: str
    confidence: Decimal | None = None
    payload_sha256: str | None = None
    metadata_schema_version: int = METADATA_SCHEMA_VERSION
    auxiliary_metadata: dict[str, Any] = field(default_factory=dict)
    contract_version: str = AI_EVENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.video_source_id, UUID):
            raise ContractValidationError("video_source_id must be a UUID.")
        if self.contract_version != AI_EVENT_CONTRACT_VERSION:
            raise ContractValidationError("Only the v1 event contract is supported.")
        for value, label, limit in (
            (self.external_event_id, "external_event_id", 128),
            (self.model_name, "model_name", 100),
            (self.model_version, "model_version", 100),
        ):
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ContractValidationError(
                    f"{label} is required and must be at most {limit} characters."
                )
        if not isinstance(self.processing_outcome, str) or self.processing_outcome not in {
            "OBSERVATION",
            "UNCERTAIN",
        }:
            raise ContractValidationError("processing_outcome must be OBSERVATION or UNCERTAIN.")
        if not isinstance(self.detected_at, datetime):
            raise ContractValidationError("detected_at must be a datetime.")
        _normalize_timestamp(self.detected_at)
        if self.confidence is not None:
            try:
                normalized = Decimal(str(self.confidence)).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_UP
                )
            except (InvalidOperation, ValueError) as exc:
                raise ContractValidationError("confidence must be a finite decimal.") from exc
            if not normalized.is_finite() or not Decimal("0") <= normalized <= Decimal("1"):
                raise ContractValidationError("confidence must be between zero and one.")
            object.__setattr__(self, "confidence", normalized)
        if self.payload_sha256 is not None and (
            not isinstance(self.payload_sha256, str)
            or len(self.payload_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.payload_sha256)
        ):
            raise ContractValidationError("payload_sha256 must be lowercase SHA-256 hex.")
        if not 1 <= self.metadata_schema_version <= 32767:
            raise ContractValidationError("metadata_schema_version is outside the supported range.")
        if not isinstance(self.auxiliary_metadata, dict):
            raise ContractValidationError("auxiliary_metadata must be an object.")
        _validate_metadata_tree(self.auxiliary_metadata)
        try:
            encoded = json.dumps(
                self.auxiliary_metadata,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except (TypeError, ValueError, RecursionError) as exc:
            raise ContractValidationError("auxiliary_metadata must contain JSON values.") from exc
        if len(encoded.encode("utf-8")) > MAX_METADATA_BYTES:
            raise ContractValidationError("auxiliary_metadata exceeds the 16 KiB limit.")

    def to_mapping(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "contract_version": self.contract_version,
            "video_source_id": str(self.video_source_id),
            "external_event_id": self.external_event_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "detected_at": _normalize_timestamp(self.detected_at)
            .isoformat()
            .replace("+00:00", "Z"),
            "processing_outcome": self.processing_outcome,
            "metadata_schema_version": self.metadata_schema_version,
            "auxiliary_metadata": self.auxiliary_metadata,
        }
        if self.confidence is not None:
            value["confidence"] = format(self.confidence, ".4f")
        if self.payload_sha256 is not None:
            value["payload_sha256"] = self.payload_sha256
        return value

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> DetectionEventPayload:
        if not isinstance(value, dict):
            raise ContractValidationError("Event payload must be an object.")
        allowed = {
            "contract_version",
            "video_source_id",
            "external_event_id",
            "model_name",
            "model_version",
            "detected_at",
            "processing_outcome",
            "confidence",
            "payload_sha256",
            "metadata_schema_version",
            "auxiliary_metadata",
        }
        if set(value) - allowed:
            raise ContractValidationError("Event payload contains fields outside the v1 contract.")
        try:
            raw_detected_at = value["detected_at"]
            if not isinstance(raw_detected_at, str):
                raise TypeError("detected_at must be a string")
            detected_at = datetime.fromisoformat(raw_detected_at.replace("Z", "+00:00"))
            source_id = UUID(str(value["video_source_id"]))
            confidence = (
                Decimal(str(value["confidence"])) if value.get("confidence") is not None else None
            )
            return cls(
                contract_version=value["contract_version"],
                video_source_id=source_id,
                external_event_id=value["external_event_id"],
                model_name=value["model_name"],
                model_version=value["model_version"],
                detected_at=detected_at,
                processing_outcome=value["processing_outcome"],
                confidence=confidence,
                payload_sha256=value.get("payload_sha256"),
                metadata_schema_version=int(value.get("metadata_schema_version", 0)),
                auxiliary_metadata=value.get("auxiliary_metadata", {}),
            )
        except ContractValidationError:
            raise
        except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
            raise ContractValidationError(
                "Event payload is missing or has invalid fields."
            ) from exc

    def content_digest(self) -> str:
        body = self.to_mapping()
        body.pop("payload_sha256", None)
        return hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
