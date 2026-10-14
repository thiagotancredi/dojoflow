class AppError(Exception):
    """Base exception for application errors."""

    default_code = 'APP_ERROR'

    def __init__(self, message: str = '', *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code or self.default_code


class NotFoundError(AppError):
    """Raised when a requested record is not found."""

    default_code = 'NOT_FOUND'


class ConflictError(AppError):
    """Raised when an operation finds conflicting data."""

    default_code = 'CONFLICT'


class UnauthorizedError(AppError):
    """Raised when authentication fails or is missing."""

    default_code = 'UNAUTHORIZED'


class ForbiddenError(AppError):
    """Raised when the caller is not allowed to perform an action."""

    default_code = 'FORBIDDEN'
