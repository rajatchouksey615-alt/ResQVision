"""Readiness reporting that never exposes secrets, video locators, or payloads."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class HealthReport:
    status: str
    ready: bool
    checks: dict[str, dict[str, Any]]

    def to_mapping(self) -> dict[str, Any]:
        return asdict(self)


def service_health(
    *,
    configuration_valid: bool,
    model_available: bool,
    video_source_configured: bool,
    backend_authenticator_configured: bool,
    outbox_writable: bool,
) -> HealthReport:
    checks = {
        "configuration": {"ok": configuration_valid},
        "model": {
            "ok": model_available,
            "error": None if model_available else "configured_model_unavailable",
        },
        "video_source": {"ok": video_source_configured},
        "backend_machine_auth": {
            "ok": backend_authenticator_configured,
            "error": None
            if backend_authenticator_configured
            else "approved_machine_authenticator_not_configured",
        },
        "outbox": {"ok": outbox_writable},
    }
    ready = all(check["ok"] for check in checks.values())
    return HealthReport(status="ready" if ready else "not_ready", ready=ready, checks=checks)
