"""Safe service boundary errors."""

from rest_framework.exceptions import APIException


class MachineAuthenticationUnavailable(APIException):
    status_code = 503
    default_detail = "Machine authentication is not configured."
    default_code = "machine_authentication_unavailable"


class EvidenceStorageUnavailable(APIException):
    status_code = 503
    default_detail = "Evidence storage is not configured."
    default_code = "evidence_storage_unavailable"
