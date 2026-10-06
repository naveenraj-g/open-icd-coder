from app.errors.base import ApplicationError


class NotFoundError(ApplicationError):
    """Raised by service methods when a requested record doesn't exist — lets
    the service raise directly instead of returning None for the router to check."""

    def __init__(self, message: str = "Resource not found", metadata=None):
        super().__init__(
            name="NotFoundError",
            message=message,
            status_code=404,
            code="NOT_FOUND",
            metadata=metadata,
        )


class ResourceConflictError(ApplicationError):
    def __init__(self, message: str, metadata=None):
        super().__init__(
            name="ResourceConflictError",
            message=message,
            status_code=409,
            code="RESOURCE_CONFLICT",
            metadata=metadata,
        )


class BusinessRuleViolationError(ApplicationError):
    """The request is well-formed but not allowed in the current state
    (e.g. approving an encounter while items are still unreviewed)."""

    def __init__(self, message: str, metadata=None):
        super().__init__(
            name="BusinessRuleViolationError",
            message=message,
            status_code=422,
            code="BUSINESS_RULE_VIOLATION",
            metadata=metadata,
        )
