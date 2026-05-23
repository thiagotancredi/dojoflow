class AppError(Exception):
    """Base exception for application errors."""


class NotFoundError(AppError):
    """Raised when a requested record is not found."""


class ConflictError(AppError):
    """Raised when an operation finds conflicting data."""
