"""HTTP client exceptions for GCP HCP CLI."""

from typing import Optional, Dict, Any


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """Initialize the API error.

        Args:
            message: Human-readable error message
            status_code: HTTP status code from the response
            response_data: Response data from the API
            request_id: Request ID for tracing
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        self.request_id = request_id

    def __str__(self) -> str:
        """Return string representation of the error."""
        parts = [self.message]

        if self.status_code:
            parts.append(f"(status: {self.status_code})")

        if self.request_id:
            parts.append(f"(request_id: {self.request_id})")

        return " ".join(parts)


class APIConnectionError(APIError):
    """Exception raised when API connection fails."""

    def __init__(self, message: str, cause: Exception = None) -> None:
        """Initialize the connection error.

        Args:
            message: Human-readable error message
            cause: Underlying exception that caused this error
        """
        super().__init__(message)
        self.cause = cause

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


class APITimeoutError(APIConnectionError):
    """Exception raised when API request times out."""

    pass


class AuthenticationRequiredError(APIError):
    """Exception raised when authentication is required but not provided."""

    pass


class AuthorizationError(APIError):
    """Exception raised when user is not authorized to perform the action."""

    pass


class ResourceNotFoundError(APIError):
    """Exception raised when a requested resource is not found."""

    pass


class ValidationError(APIError):
    """Exception raised when request validation fails."""

    pass


class ServerError(APIError):
    """Exception raised when server returns a 5xx error."""

    pass


class RateLimitError(APIError):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self, message: str, retry_after: Optional[int] = None, **kwargs
    ) -> None:
        """Initialize the rate limit error.

        Args:
            message: Human-readable error message
            retry_after: Number of seconds to wait before retrying
            **kwargs: Additional arguments passed to APIError
        """
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
