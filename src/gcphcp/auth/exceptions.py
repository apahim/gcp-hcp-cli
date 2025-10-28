"""Authentication exceptions for GCP HCP CLI."""


class AuthenticationError(Exception):
    """Base exception for authentication errors."""

    def __init__(self, message: str, cause: Exception = None) -> None:
        """Initialize the authentication error.

        Args:
            message: Human-readable error message
            cause: Optional underlying exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


class TokenRefreshError(AuthenticationError):
    """Exception raised when token refresh fails."""
    pass


class CredentialsNotFoundError(AuthenticationError):
    """Exception raised when user credentials are not found."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Exception raised when credentials are invalid or expired."""
    pass