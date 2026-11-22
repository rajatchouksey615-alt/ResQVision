"""Stable, non-disclosing JSON errors for the versioned API."""

from django.core.exceptions import RequestDataTooBig
from django.http import Http404
from rest_framework import exceptions
from rest_framework.views import exception_handler

from common.domain.exceptions import (
    AuthorizationDenied,
    BusinessRuleViolation,
    IdempotencyConflict,
    InvalidStateTransition,
    PolicyNotConfigured,
    ResourceConflict,
    ResourceNotFound,
)

_DOMAIN_ERRORS = {
    AuthorizationDenied: (403, "authorization_denied", "This action is not permitted."),
    ResourceNotFound: (404, "not_found", "Resource not found."),
    InvalidStateTransition: (409, "invalid_state", "The command conflicts with current state."),
    IdempotencyConflict: (
        409,
        "idempotency_conflict",
        "The command conflicts with a prior request.",
    ),
    ResourceConflict: (409, "resource_conflict", "The command conflicts with current data."),
    BusinessRuleViolation: (400, "business_rule_violation", "The request violates a domain rule."),
    PolicyNotConfigured: (
        503,
        "policy_unavailable",
        "This operation is unavailable until its authorization policy is approved.",
    ),
}


def _request_id(context: dict) -> str | None:
    request = context.get("request")
    value = getattr(request, "request_id", None)
    return str(value) if value else None


def api_exception_handler(exc, context):
    request_id = _request_id(context)
    for error_type, (status, code, detail) in _DOMAIN_ERRORS.items():
        if isinstance(exc, error_type):
            return _json_response(status, code, detail, request_id)

    if isinstance(exc, RequestDataTooBig):
        return _json_response(
            413, "request_too_large", "The request body exceeds the size limit.", request_id
        )

    response = exception_handler(exc, context)
    if response is None:
        return None

    status = response.status_code
    data = response.data
    errors = None
    if isinstance(exc, exceptions.ValidationError):
        code = "validation_error"
        detail = "Request data is invalid."
        errors = data
    elif isinstance(exc, exceptions.Throttled):
        code = "rate_limited"
        detail = "Too many requests. Please try again later."
    elif isinstance(exc, (exceptions.AuthenticationFailed, exceptions.NotAuthenticated)):
        code = "authentication_failed"
        detail = "Authentication is required or invalid."
    elif isinstance(exc, exceptions.PermissionDenied):
        code = "authorization_denied"
        detail = "This action is not permitted."
    elif isinstance(exc, (exceptions.NotFound, Http404)):
        code = "not_found"
        detail = "Resource not found."
    elif isinstance(exc, exceptions.MethodNotAllowed):
        code = "method_not_allowed"
        detail = "This method is not available for the resource."
    elif status == 503:
        code = str(getattr(exc, "default_code", "service_unavailable"))
        detail = str(getattr(exc, "detail", "The service is temporarily unavailable."))
    else:
        code = "request_failed"
        detail = "The request could not be completed."

    response.data = _payload(code, detail, request_id, errors)
    return response


def _payload(code: str, detail: str, request_id: str | None, errors=None) -> dict:
    payload = {"code": code, "detail": detail}
    if errors is not None:
        payload["errors"] = errors
    if request_id:
        payload["request_id"] = request_id
    return payload


def _json_response(status: int, code: str, detail: str, request_id: str | None):
    from rest_framework.response import Response

    return Response(_payload(code, detail, request_id), status=status)
