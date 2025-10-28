"""Unit tests for API client module."""

import pytest
import requests
from unittest.mock import Mock, patch

from gcphcp.client.api_client import APIClient
from gcphcp.client.exceptions import (
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
from gcphcp.auth.google_auth import GoogleCloudAuth


class TestAPIClient:
    """Test suite for APIClient class."""

    @pytest.fixture
    def mock_auth(self):
        """Create mock authentication manager."""
        auth = Mock(spec=GoogleCloudAuth)
        auth.get_auth_headers.return_value = {
            "Authorization": "Bearer test_token",
            "X-User-Email": "test@example.com",
        }
        return auth

    @pytest.fixture
    def api_client(self, mock_auth):
        """Create APIClient instance for testing."""
        return APIClient(
            base_url="https://api.example.com",
            auth=mock_auth,
            timeout=10.0,
            retries=2,
        )

    def test_init(self, mock_auth):
        """Test API client initialization."""
        client = APIClient(
            base_url="https://api.example.com/",
            auth=mock_auth,
            timeout=15.0,
            retries=3,
            backoff_factor=2.0,
            user_agent="test-agent/1.0",
        )

        assert client.base_url == "https://api.example.com"
        assert client.auth == mock_auth
        assert client.timeout == 15.0
        assert client.user_agent == "test-agent/1.0"
        assert client.session is not None

    def test_build_url(self, api_client):
        """Test URL building."""
        # Test with leading slash
        url = api_client._build_url("/api/v1/clusters")
        assert url == "https://api.example.com/api/v1/clusters"

        # Test without leading slash
        url = api_client._build_url("api/v1/clusters")
        assert url == "https://api.example.com/api/v1/clusters"

        # Test empty path
        url = api_client._build_url("")
        assert url == "https://api.example.com/"

    def test_get_auth_headers_success(self, api_client, mock_auth):
        """Test successful authentication header retrieval."""
        headers = api_client._get_auth_headers()
        assert headers == {
            "Authorization": "Bearer test_token",
            "X-User-Email": "test@example.com",
        }

    def test_get_auth_headers_failure(self, api_client, mock_auth):
        """Test authentication header retrieval failure."""
        mock_auth.get_auth_headers.side_effect = Exception("Auth failed")

        with pytest.raises(AuthenticationRequiredError) as exc_info:
            api_client._get_auth_headers()

        assert "Authentication failed" in str(exc_info.value)

    def test_handle_response_success(self, api_client):
        """Test successful response handling."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"status": "success"}

        result = api_client._handle_response(mock_response)
        assert result == {"status": "success"}

    def test_handle_response_validation_error(self, api_client):
        """Test handling 400 validation error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {
            "Content-Type": "application/json",
            "X-Request-ID": "req-123",
        }
        mock_response.json.return_value = {"message": "Validation failed"}

        with pytest.raises(ValidationError) as exc_info:
            api_client._handle_response(mock_response)

        error = exc_info.value
        assert error.message == "Validation failed"
        assert error.status_code == 400
        assert error.request_id == "req-123"

    def test_handle_response_authentication_error(self, api_client):
        """Test handling 401 authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"message": "Unauthorized"}

        with pytest.raises(AuthenticationRequiredError) as exc_info:
            api_client._handle_response(mock_response)

        assert exc_info.value.message == "Unauthorized"
        assert exc_info.value.status_code == 401

    def test_handle_response_authorization_error(self, api_client):
        """Test handling 403 authorization error."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"message": "Forbidden"}

        with pytest.raises(AuthorizationError) as exc_info:
            api_client._handle_response(mock_response)

        assert exc_info.value.message == "Forbidden"
        assert exc_info.value.status_code == 403

    def test_handle_response_not_found_error(self, api_client):
        """Test handling 404 not found error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"message": "Resource not found"}

        with pytest.raises(ResourceNotFoundError) as exc_info:
            api_client._handle_response(mock_response)

        assert exc_info.value.message == "Resource not found"
        assert exc_info.value.status_code == 404

    def test_handle_response_rate_limit_error(self, api_client):
        """Test handling 429 rate limit error."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {
            "Content-Type": "application/json",
            "Retry-After": "60",
        }
        mock_response.json.return_value = {"message": "Rate limit exceeded"}

        with pytest.raises(RateLimitError) as exc_info:
            api_client._handle_response(mock_response)

        error = exc_info.value
        assert error.message == "Rate limit exceeded"
        assert error.status_code == 429
        assert error.retry_after == 60

    def test_handle_response_server_error(self, api_client):
        """Test handling 500 server error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"message": "Internal server error"}

        with pytest.raises(ServerError) as exc_info:
            api_client._handle_response(mock_response)

        assert exc_info.value.message == "Internal server error"
        assert exc_info.value.status_code == 500

    def test_handle_response_non_json(self, api_client):
        """Test handling non-JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.text = "Plain text response"

        result = api_client._handle_response(mock_response)
        assert result == {"message": "Plain text response"}

    def test_handle_response_invalid_json(self, api_client):
        """Test handling response with invalid JSON."""
        import json

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
        mock_response.text = "Invalid JSON content"

        result = api_client._handle_response(mock_response)
        assert result == {"message": "Invalid JSON content"}

    @patch("gcphcp.client.api_client.requests.Session.request")
    def test_make_request_success(self, mock_request, api_client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"data": "success"}
        mock_request.return_value = mock_response

        result = api_client._make_request("GET", "/test", params={"key": "value"})

        assert result == {"data": "success"}
        mock_request.assert_called_once()

        # Verify request parameters
        call_args = mock_request.call_args
        assert call_args[1]["method"] == "GET"
        assert call_args[1]["url"] == "https://api.example.com/test"
        assert call_args[1]["params"] == {"key": "value"}
        assert "Authorization" in call_args[1]["headers"]
        assert "X-User-Email" in call_args[1]["headers"]

    @patch("gcphcp.client.api_client.requests.Session.request")
    def test_make_request_timeout(self, mock_request, api_client):
        """Test request timeout handling."""
        mock_request.side_effect = requests.Timeout("Request timed out")

        with pytest.raises(APITimeoutError) as exc_info:
            api_client._make_request("GET", "/test")

        assert "timed out" in str(exc_info.value)

    @patch("gcphcp.client.api_client.requests.Session.request")
    def test_make_request_connection_error(self, mock_request, api_client):
        """Test connection error handling."""
        mock_request.side_effect = requests.ConnectionError("Connection failed")

        with pytest.raises(APIConnectionError) as exc_info:
            api_client._make_request("GET", "/test")

        assert "Failed to connect" in str(exc_info.value)

    @patch("gcphcp.client.api_client.requests.Session.request")
    def test_make_request_general_error(self, mock_request, api_client):
        """Test general request error handling."""
        mock_request.side_effect = requests.RequestException("General error")

        with pytest.raises(APIConnectionError) as exc_info:
            api_client._make_request("GET", "/test")

        assert "Request to" in str(exc_info.value)

    def test_get_method(self, api_client):
        """Test GET method."""
        with patch.object(api_client, "_make_request") as mock_request:
            mock_request.return_value = {"result": "get"}

            result = api_client.get("/test", params={"key": "value"})

            assert result == {"result": "get"}
            mock_request.assert_called_once_with(
                "GET", "/test", params={"key": "value"}, headers=None
            )

    def test_post_method(self, api_client):
        """Test POST method."""
        with patch.object(api_client, "_make_request") as mock_request:
            mock_request.return_value = {"result": "post"}

            result = api_client.post(
                "/test",
                json_data={"data": "value"},
                params={"key": "value"},
            )

            assert result == {"result": "post"}
            mock_request.assert_called_once_with(
                "POST",
                "/test",
                params={"key": "value"},
                json_data={"data": "value"},
                headers=None,
            )

    def test_put_method(self, api_client):
        """Test PUT method."""
        with patch.object(api_client, "_make_request") as mock_request:
            mock_request.return_value = {"result": "put"}

            result = api_client.put("/test", json_data={"data": "value"})

            assert result == {"result": "put"}
            mock_request.assert_called_once_with(
                "PUT", "/test", params=None, json_data={"data": "value"}, headers=None
            )

    def test_delete_method(self, api_client):
        """Test DELETE method."""
        with patch.object(api_client, "_make_request") as mock_request:
            mock_request.return_value = {"result": "delete"}

            result = api_client.delete("/test")

            assert result == {"result": "delete"}
            mock_request.assert_called_once_with(
                "DELETE", "/test", params=None, headers=None
            )

    def test_health_check(self, api_client):
        """Test health check method."""
        with patch.object(api_client, "get") as mock_get:
            mock_get.return_value = {"status": "healthy"}

            result = api_client.health_check()

            assert result == {"status": "healthy"}
            mock_get.assert_called_once_with("/health")

    def test_close(self, api_client):
        """Test client close method."""
        with patch.object(api_client.session, "close") as mock_close:
            api_client.close()
            mock_close.assert_called_once()


class TestAPIClientExceptions:
    """Test suite for API client exception handling."""

    def test_api_error_with_all_params(self):
        """Test APIError with all parameters."""
        error = APIError(
            message="Test error",
            status_code=400,
            response_data={"detail": "error detail"},
            request_id="req-123",
        )

        assert str(error) == "Test error (status: 400) (request_id: req-123)"
        assert error.status_code == 400
        assert error.response_data == {"detail": "error detail"}
        assert error.request_id == "req-123"

    def test_api_connection_error_with_cause(self):
        """Test APIConnectionError with underlying cause."""
        cause = ConnectionError("Network error")
        error = APIConnectionError("Connection failed", cause=cause)

        assert "Connection failed" in str(error)
        assert "Network error" in str(error)
        assert error.cause == cause

    def test_rate_limit_error_with_retry_after(self):
        """Test RateLimitError with retry_after parameter."""
        error = RateLimitError(
            message="Rate limit exceeded",
            retry_after=60,
            status_code=429,
        )

        assert error.message == "Rate limit exceeded"
        assert error.retry_after == 60
        assert error.status_code == 429
