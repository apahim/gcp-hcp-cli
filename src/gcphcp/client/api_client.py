"""HTTP API client for GCP HCP CLI."""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    RequestException,
    Timeout,
)
from urllib3.util.retry import Retry

from ..auth.google_auth import GoogleCloudAuth
from .exceptions import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationRequiredError,
    AuthorizationError,
    RateLimitError,
    ResourceNotFoundError,
    ServerError,
    ValidationError,
)

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 1.0
DEFAULT_USER_AGENT = "gcphcp-cli/0.1.0"


class APIClient:
    """HTTP client for GCP HCP API."""

    def __init__(
        self,
        base_url: str,
        auth: GoogleCloudAuth,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        """Initialize the API client.

        Args:
            base_url: Base URL for the API
            auth: Authentication manager
            timeout: Request timeout in seconds
            retries: Number of retries for failed requests
            backoff_factor: Backoff factor for retries
            user_agent: User agent string for requests
        """
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.timeout = timeout
        self.user_agent = user_agent

        # Create session with retry strategy
        self.session = requests.Session()
        self._setup_retry_strategy(retries, backoff_factor)
        self._setup_default_headers()

    def _setup_retry_strategy(self, retries: int, backoff_factor: float) -> None:
        """Set up retry strategy for the session.

        Args:
            retries: Number of retries
            backoff_factor: Backoff factor for retries
        """
        retry_strategy = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "PUT", "DELETE"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _setup_default_headers(self) -> None:
        """Set up default headers for all requests."""
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers.

        Returns:
            Dictionary containing authentication headers

        Raises:
            AuthenticationRequiredError: If authentication fails
        """
        try:
            return self.auth.get_auth_headers()
        except Exception as e:
            raise AuthenticationRequiredError(
                f"Authentication failed: {e}"
            ) from e

    def _build_url(self, path: str) -> str:
        """Build full URL from base URL and path.

        Args:
            path: API path

        Returns:
            Full URL
        """
        return urljoin(f"{self.base_url}/", path.lstrip("/"))

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and raise appropriate exceptions.

        Args:
            response: HTTP response object

        Returns:
            Parsed response data

        Raises:
            APIError: For various API error conditions
        """
        request_id = response.headers.get("X-Request-ID")

        # Try to parse response data
        try:
            if response.headers.get("Content-Type", "").startswith("application/json"):
                response_data = response.json()
            else:
                response_data = {"message": response.text}
        except json.JSONDecodeError:
            response_data = {"message": response.text}

        # Handle success responses
        if 200 <= response.status_code < 300:
            return response_data

        # Extract error message
        error_message = "Unknown error"
        if isinstance(response_data, dict):
            error_message = (
                response_data.get("message") or
                response_data.get("error", {}).get("message") or
                response_data.get("error") or
                f"HTTP {response.status_code} error"
            )

        # Handle specific error types
        if response.status_code == 400:
            raise ValidationError(
                error_message,
                status_code=response.status_code,
                response_data=response_data,
                request_id=request_id,
            )
        elif response.status_code == 401:
            raise AuthenticationRequiredError(
                error_message,
                status_code=response.status_code,
                response_data=response_data,
                request_id=request_id,
            )
        elif response.status_code == 403:
            raise AuthorizationError(
                error_message,
                status_code=response.status_code,
                response_data=response_data,
                request_id=request_id,
            )
        elif response.status_code == 404:
            raise ResourceNotFoundError(
                error_message,
                status_code=response.status_code,
                response_data=response_data,
                request_id=request_id,
            )
        elif response.status_code == 429:
            retry_after = None
            if "Retry-After" in response.headers:
                try:
                    retry_after = int(response.headers["Retry-After"])
                except ValueError:
                    pass

            raise RateLimitError(
                error_message,
                status_code=response.status_code,
                response_data=response_data,
                request_id=request_id,
                retry_after=retry_after,
            )
        elif 500 <= response.status_code < 600:
            raise ServerError(
                error_message,
                status_code=response.status_code,
                response_data=response_data,
                request_id=request_id,
            )
        else:
            raise APIError(
                error_message,
                status_code=response.status_code,
                response_data=response_data,
                request_id=request_id,
            )

    def _make_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to API.

        Args:
            method: HTTP method
            path: API path
            params: Query parameters
            json_data: JSON data for request body
            headers: Additional headers

        Returns:
            Parsed response data

        Raises:
            APIError: For various API error conditions
        """
        url = self._build_url(path)

        # Prepare headers
        request_headers = self._get_auth_headers()
        if headers:
            request_headers.update(headers)

        logger.debug(f"Making {method} request to {url}")

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=request_headers,
                timeout=self.timeout,
            )

            return self._handle_response(response)

        except Timeout as e:
            raise APITimeoutError(
                f"Request to {url} timed out after {self.timeout} seconds"
            ) from e
        except ConnectionError as e:
            raise APIConnectionError(
                f"Failed to connect to {url}"
            ) from e
        except RequestException as e:
            raise APIConnectionError(
                f"Request to {url} failed: {e}"
            ) from e

    def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make GET request.

        Args:
            path: API path
            params: Query parameters
            headers: Additional headers

        Returns:
            Parsed response data
        """
        return self._make_request("GET", path, params=params, headers=headers)

    def post(
        self,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make POST request.

        Args:
            path: API path
            json_data: JSON data for request body
            params: Query parameters
            headers: Additional headers

        Returns:
            Parsed response data
        """
        return self._make_request("POST", path, params=params, json_data=json_data, headers=headers)

    def put(
        self,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make PUT request.

        Args:
            path: API path
            json_data: JSON data for request body
            params: Query parameters
            headers: Additional headers

        Returns:
            Parsed response data
        """
        return self._make_request("PUT", path, params=params, json_data=json_data, headers=headers)

    def delete(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make DELETE request.

        Args:
            path: API path
            params: Query parameters
            headers: Additional headers

        Returns:
            Parsed response data
        """
        return self._make_request("DELETE", path, params=params, headers=headers)

    def health_check(self) -> Dict[str, Any]:
        """Check API health status.

        Returns:
            Health status response

        Raises:
            APIError: If health check fails
        """
        return self.get("/health")

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()