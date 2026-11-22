from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from resqvision_ai.contracts import DetectionEventPayload
from resqvision_ai.errors import ContractValidationError


def sample_payload(**overrides):
    values = {
        "video_source_id": uuid4(),
        "external_event_id": "event-one",
        "model_name": "simulated-detector",
        "model_version": "test-1",
        "detected_at": datetime(2026, 11, 22, 12, tzinfo=UTC),
        "processing_outcome": "OBSERVATION",
        "confidence": Decimal("0.87654"),
        "auxiliary_metadata": {"frame_index": 12, "detections": [{"label": "vehicle"}]},
    }
    values.update(overrides)
    return DetectionEventPayload(**values)


def test_payload_round_trips_v1_with_timezone_and_four_decimal_confidence():
    payload = sample_payload()

    encoded = payload.to_mapping()
    decoded = DetectionEventPayload.from_mapping(encoded)

    assert encoded["contract_version"] == "v1"
    assert encoded["detected_at"].endswith("Z")
    assert encoded["confidence"] == "0.8765"
    assert decoded == payload
    assert len(payload.content_digest()) == 64


@pytest.mark.parametrize(
    "change",
    [
        {"confidence": Decimal("1.0001")},
        {"processing_outcome": "VERIFIED"},
        {"contract_version": "v2"},
        {"auxiliary_metadata": {"reviewer_id": "untrusted"}},
        {"auxiliary_metadata": {"detections": [{"incident_status": "OPEN"}]}},
        {"detected_at": datetime(2026, 11, 22, 12)},
    ],
)
def test_payload_rejects_invalid_or_authority_bearing_values(change):
    with pytest.raises(ContractValidationError):
        sample_payload(**change)


def test_payload_rejects_unknown_v1_fields():
    body = sample_payload().to_mapping()
    body["police_organization_id"] = str(uuid4())

    with pytest.raises(ContractValidationError):
        DetectionEventPayload.from_mapping(body)
