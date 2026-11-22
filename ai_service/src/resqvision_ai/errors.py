"""Stable, non-sensitive operational errors for the AI integration."""


class AIServiceError(Exception):
    """Base class for safe-to-report service errors."""


class ContractValidationError(AIServiceError, ValueError):
    """An event does not satisfy the backend v1 contract."""


class ConfigurationError(AIServiceError):
    """Required runtime configuration is missing or invalid."""


class VideoIngestionError(AIServiceError):
    """A video source could not be opened or decoded."""


class ModelUnavailable(AIServiceError):
    """An explicitly configured detector or model cannot be loaded."""


class BackendSubmissionError(AIServiceError):
    """A backend event submission failed."""


class BackendAuthenticationUnavailable(BackendSubmissionError):
    """No approved machine authenticator was supplied."""


class BackendAuthenticationError(BackendSubmissionError):
    """The backend rejected the machine identity."""


class BackendSourceRejected(BackendSubmissionError):
    """The source is missing, unauthorized, or unavailable for ingestion."""


class BackendContractError(BackendSubmissionError):
    """The backend rejected the payload or contract version."""


class BackendIdempotencyConflict(BackendSubmissionError):
    """An event identity already exists with different content."""


class BackendUnavailable(BackendSubmissionError):
    """The backend could not be reached after bounded retries."""


class OutboxConflict(AIServiceError):
    """An event ID was enqueued with different payload content."""
