"""
Request ID middleware — attaches a correlation ID to every request.

The ID is:
- Injected into the logging context so every log line carries it
- Returned as X-Request-ID response header for client-side debugging
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.core.logging import generate_request_id, request_id_var, get_logger

logger = get_logger("middleware.request")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID") or generate_request_id()
        token = request_id_var.set(req_id)

        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Response-Time"] = f"{duration_ms}ms"

            # Skip logging static files
            if not request.url.path.startswith("/storage"):
                logger.info(
                    "%s %s → %d (%sms)",
                    request.method,
                    request.url.path,
                    response.status_code,
                    duration_ms,
                )

            request_id_var.reset(token)

        return response
