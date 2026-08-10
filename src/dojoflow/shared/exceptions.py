class AppError(Exception):
    """Base exception for application errors."""


class NotFoundError(AppError):
    """Raised when a requested record is not found."""


class ConflictError(AppError):
    """Raised when an operation finds conflicting data."""


class UnauthorizedError(AppError):
    """Raised when authentication fails or is missing."""


class ForbiddenError(AppError):
    """Raised when the caller is not allowed to perform an action."""
