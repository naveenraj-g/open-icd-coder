"""Every error — domain, validation, HTTP, or unhandled — leaves the API in
one shape:

    {"error": {"code": "NOT_FOUND", "message": "...", "details": [...]?}}
"""

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.errors.base import ApplicationError

logger = get_logger(__name__)


def _error(status_code: int, code: str, message: str, details=None) -> JSONResponse:
    body: dict = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status_code, content={"error": body})


def _base_log_payload(request: Request) -> dict:
    return {"method": request.method, "path": request.url.path}


async def application_error_handler(request: Request, exc: ApplicationError):
    payload = {
        **_base_log_payload(request),
        "error_name": exc.name,
        "error_code": exc.code,
        "status_code": exc.status_code,
        "metadata": exc.metadata,
    }
    if exc.is_operational:
        logger.warning("Operational application error", extra={**payload, "event": "error.operational"})
    else:
        logger.error(
            "Non-operational application error",
            extra={**payload, "event": "error.non_operational"},
            exc_info=exc,
        )
    message = "Internal server error" if exc.status_code >= 500 else exc.message
    return _error(exc.status_code, exc.code, message)


async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.info(
        "Request validation failed",
        extra={**_base_log_payload(request), "event": "error.request_validation", "errors": exc.errors()},
    )
    details = [
        {
            "field": ".".join(str(loc) for loc in err["loc"] if loc not in ("body", "query", "path")),
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    return _error(422, "VALIDATION_ERROR", "Request validation failed", details)


async def http_exception_handler(request: Request, exc: HTTPException):
    return _error(exc.status_code, "HTTP_ERROR", str(exc.detail))


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.critical(
        "Unhandled exception occurred",
        extra={**_base_log_payload(request), "event": "error.unhandled", "error_type": type(exc).__name__},
        exc_info=exc,
    )
    return _error(500, "INTERNAL_ERROR", "Internal server error")
