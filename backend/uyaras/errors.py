from fastapi.responses import JSONResponse


def error_response(request, status, message, fields=None, headers=None):
    code = {400: "bad_request", 401: "authentication_required", 403: "forbidden", 404: "not_found",
            409: "conflict", 413: "payload_too_large", 422: "validation_error", 429: "rate_limited",
            503: "unavailable"}.get(status, "internal_error")
    response_headers = {"X-Request-ID": getattr(request.state, "request_id", ""), **(headers or {})}
    if status == 429: response_headers["Retry-After"] = "900"
    return JSONResponse(status_code=status, headers=response_headers, content={"detail": message,
        "error": {"code": code, "message": message, "fields": fields or []},
        "request_id": getattr(request.state, "request_id", "")})
