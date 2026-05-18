"""
Global exception handler middleware.

Converts all GradeOpsError subclasses into structured JSON responses.
Catches unhandled exceptions and returns 500 without leaking tracebacks to clients.
"""
import traceback
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.exceptions import GradeOpsError
from backend.core.logging import get_logger, request_id_var

logger = get_logger("middleware.errors")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except GradeOpsError as e:
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": e.error_code,
                    "message": e.message,
                    "details": e.details,
                    "request_id": request_id_var.get(),
                },
            )
        except Exception as e:
            req_id = request_id_var.get()
            logger.error(
                "Unhandled exception on %s %s (request_id=%s): %s\n%s",
                request.method, request.url.path, req_id, e, traceback.format_exc(),
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred. Please try again.",
                    "request_id": req_id,
                },
            )
