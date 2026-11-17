"""Request correlation and safe API failure handling."""

from uuid import UUID, uuid4

from django.http import JsonResponse


class RequestIDMiddleware:
    """Attach a validated UUID correlation id to every request and response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID", "")
        try:
            request.request_id = UUID(request_id)
        except ValueError, TypeError, AttributeError:
            request.request_id = uuid4()
        response = self.get_response(request)
        if request.path.startswith("/api/") and response.status_code == 404:
            content_type = response.get("Content-Type", "")
            if "application/json" not in content_type:
                response = JsonResponse(
                    {
                        "code": "not_found",
                        "detail": "Resource not found.",
                        "request_id": str(request.request_id),
                    },
                    status=404,
                )
        if request.path.startswith("/api/"):
            response["Cache-Control"] = "no-store"
        response["X-Request-ID"] = str(request.request_id)
        return response


class ApiErrorBoundaryMiddleware:
    """Keep unexpected API failures in a non-disclosing JSON envelope."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        del exception
        if not request.path.startswith("/api/"):
            return None
        request_id = getattr(request, "request_id", uuid4())
        response = JsonResponse(
            {
                "code": "internal_error",
                "detail": "An unexpected error occurred.",
                "request_id": str(request_id),
            },
            status=500,
        )
        response["X-Request-ID"] = str(request_id)
        return response
