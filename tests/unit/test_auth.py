"""Unit tests for authentication module."""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock

from gcphcp.auth.google_auth import GoogleCloudAuth, REQUIRED_SCOPES
from gcphcp.auth.exceptions import (
    AuthenticationError,
    TokenRefreshError,
    CredentialsNotFoundError,
    InvalidCredentialsError,
)


class TestGoogleCloudAuth:
    """Test suite for GoogleCloudAuth class."""

    @pytest.fixture
    def temp_credentials_path(self, tmp_path):
        """Provide a temporary credentials path."""
        return tmp_path / "test_credentials.json"

    @pytest.fixture
    def temp_secrets_path(self, tmp_path):
        """Provide a temporary client secrets path."""
        secrets_path = tmp_path / "client_secrets.json"
        secrets_data = {
            "installed": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        secrets_path.write_text(json.dumps(secrets_data))
        return secrets_path

    @pytest.fixture
    def auth_manager(self, temp_credentials_path):
        """Create GoogleCloudAuth instance for testing."""
        return GoogleCloudAuth(credentials_path=temp_credentials_path)

    @pytest.fixture
    def valid_credentials_data(self):
        """Provide valid credentials data."""
        return {
            "token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "token_uri": "https://oauth2.googleapis.com/token",
            "scopes": REQUIRED_SCOPES,
            "user_email": "test@example.com",
        }

    def test_init_with_default_paths(self):
        """Test initialization with default paths."""
        auth = GoogleCloudAuth()
        assert auth.credentials_path == Path.home() / ".gcphcp" / "credentials.json"
        assert auth.client_secrets_path is None
        assert auth._credentials is None
        assert auth._user_email is None

    def test_init_with_custom_paths(self, temp_credentials_path, temp_secrets_path):
        """Test initialization with custom paths."""
        auth = GoogleCloudAuth(
            credentials_path=temp_credentials_path,
            client_secrets_path=temp_secrets_path,
        )
        assert auth.credentials_path == temp_credentials_path
        assert auth.client_secrets_path == temp_secrets_path

    def test_load_stored_credentials_success(self, auth_manager, valid_credentials_data):
        """Test successful loading of stored credentials."""
        # Write credentials to file
        auth_manager.credentials_path.parent.mkdir(parents=True, exist_ok=True)
        with open(auth_manager.credentials_path, "w") as f:
            json.dump(valid_credentials_data, f)

        # Mock the OAuth2Credentials creation
        with patch("gcphcp.auth.google_auth.OAuth2Credentials") as mock_creds:
            mock_instance = Mock()
            mock_creds.return_value = mock_instance

            # Load credentials
            result = auth_manager._load_stored_credentials()

            assert result is True
            assert auth_manager._credentials is not None
            assert auth_manager._user_email == "test@example.com"

    def test_load_stored_credentials_file_not_found(self, auth_manager):
        """Test loading credentials when file doesn't exist."""
        result = auth_manager._load_stored_credentials()
        assert result is False
        assert auth_manager._credentials is None

    def test_load_stored_credentials_invalid_json(self, auth_manager):
        """Test loading credentials with invalid JSON."""
        # Write invalid JSON to file
        auth_manager.credentials_path.parent.mkdir(parents=True, exist_ok=True)
        with open(auth_manager.credentials_path, "w") as f:
            f.write("invalid json")

        result = auth_manager._load_stored_credentials()
        assert result is False

    @patch("gcphcp.auth.google_auth.default")
    def test_perform_oauth_flow_with_default_credentials(self, mock_default, auth_manager):
        """Test OAuth flow using application default credentials."""
        mock_credentials = Mock()
        mock_default.return_value = (mock_credentials, "test-project")

        auth_manager._perform_oauth_flow()

        assert auth_manager._credentials == mock_credentials
        mock_default.assert_called_once_with(scopes=REQUIRED_SCOPES)

    @patch("gcphcp.auth.google_auth.InstalledAppFlow")
    def test_perform_oauth_flow_with_client_secrets(
        self, mock_flow_class, auth_manager, temp_secrets_path
    ):
        """Test OAuth flow with client secrets file."""
        auth_manager.client_secrets_path = temp_secrets_path

        mock_flow = Mock()
        mock_credentials = Mock()
        mock_flow.run_local_server.return_value = mock_credentials
        mock_flow_class.from_client_secrets_file.return_value = mock_flow

        with patch.object(auth_manager, "_save_credentials"):
            auth_manager._perform_oauth_flow()

        assert auth_manager._credentials == mock_credentials
        mock_flow_class.from_client_secrets_file.assert_called_once_with(
            str(temp_secrets_path), scopes=REQUIRED_SCOPES
        )
        mock_flow.run_local_server.assert_called_once()

    @patch("gcphcp.auth.google_auth.default")
    def test_perform_oauth_flow_no_credentials_available(self, mock_default, auth_manager):
        """Test OAuth flow when no credentials are available."""
        from google.auth.exceptions import DefaultCredentialsError

        mock_default.side_effect = DefaultCredentialsError("No credentials")

        with pytest.raises(CredentialsNotFoundError):
            auth_manager._perform_oauth_flow()

    def test_refresh_credentials_success(self, auth_manager):
        """Test successful credential refresh."""
        mock_credentials = Mock()
        mock_credentials.refresh = Mock()
        auth_manager._credentials = mock_credentials

        with patch.object(auth_manager, "_save_credentials"):
            auth_manager._refresh_credentials()

        mock_credentials.refresh.assert_called_once()

    def test_refresh_credentials_no_credentials(self, auth_manager):
        """Test refresh when no credentials are available."""
        with pytest.raises(TokenRefreshError):
            auth_manager._refresh_credentials()

    def test_refresh_credentials_refresh_error(self, auth_manager):
        """Test refresh when refresh fails."""
        from google.auth.exceptions import RefreshError

        mock_credentials = Mock()
        mock_credentials.refresh.side_effect = RefreshError("Refresh failed")
        auth_manager._credentials = mock_credentials

        with pytest.raises(TokenRefreshError):
            auth_manager._refresh_credentials()

    def test_extract_user_email_from_cached(self, auth_manager):
        """Test extracting user email when already cached."""
        auth_manager._user_email = "cached@example.com"
        result = auth_manager._extract_user_email()
        assert result == "cached@example.com"

    def test_extract_user_email_from_id_token(self, auth_manager):
        """Test extracting user email from ID token."""
        import base64
        import json

        # Create a mock ID token
        payload = {"email": "token@example.com"}
        encoded_payload = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")
        id_token = f"header.{encoded_payload}.signature"

        mock_credentials = Mock()
        mock_credentials.id_token = id_token
        auth_manager._credentials = mock_credentials

        result = auth_manager._extract_user_email()
        assert result == "token@example.com"
        assert auth_manager._user_email == "token@example.com"

    def test_save_credentials(self, auth_manager, valid_credentials_data):
        """Test saving credentials to file."""
        # Create mock credentials
        mock_credentials = Mock()
        mock_credentials.token = valid_credentials_data["token"]
        mock_credentials.refresh_token = valid_credentials_data["refresh_token"]
        mock_credentials.client_id = valid_credentials_data["client_id"]
        mock_credentials.client_secret = valid_credentials_data["client_secret"]
        mock_credentials.token_uri = valid_credentials_data["token_uri"]
        mock_credentials.scopes = valid_credentials_data["scopes"]

        auth_manager._credentials = mock_credentials
        auth_manager._user_email = valid_credentials_data["user_email"]

        # Save credentials
        auth_manager._save_credentials()

        # Verify file was created and contains correct data
        assert auth_manager.credentials_path.exists()
        with open(auth_manager.credentials_path) as f:
            saved_data = json.load(f)

        assert saved_data["token"] == valid_credentials_data["token"]
        assert saved_data["user_email"] == valid_credentials_data["user_email"]

    def test_get_auth_headers_success(self, auth_manager):
        """Test getting authentication headers successfully."""
        with patch.object(auth_manager, "authenticate") as mock_authenticate:
            mock_authenticate.return_value = ("test_token", "test@example.com")

            headers = auth_manager.get_auth_headers()

            assert headers == {
                "Authorization": "Bearer test_token",
                "X-User-Email": "test@example.com",
            }

    def test_get_auth_headers_auth_failure(self, auth_manager):
        """Test getting authentication headers when authentication fails."""
        with patch.object(auth_manager, "authenticate") as mock_authenticate:
            mock_authenticate.side_effect = Exception("Auth failed")

            with pytest.raises(Exception) as exc_info:
                auth_manager.get_auth_headers()
            assert "Auth failed" in str(exc_info.value)

    def test_logout(self, auth_manager, valid_credentials_data):
        """Test logout removes stored credentials."""
        # Create credentials file
        auth_manager.credentials_path.parent.mkdir(parents=True, exist_ok=True)
        with open(auth_manager.credentials_path, "w") as f:
            json.dump(valid_credentials_data, f)

        auth_manager._credentials = Mock()
        auth_manager._user_email = "test@example.com"

        # Logout
        auth_manager.logout()

        # Verify cleanup
        assert not auth_manager.credentials_path.exists()
        assert auth_manager._credentials is None
        assert auth_manager._user_email is None

    def test_is_authenticated_true(self, auth_manager):
        """Test is_authenticated returns True for valid credentials."""
        mock_credentials = Mock()
        mock_credentials.expired = False
        mock_credentials.token = "valid_token"
        auth_manager._credentials = mock_credentials

        result = auth_manager.is_authenticated()
        assert result is True

    def test_is_authenticated_false_no_credentials(self, auth_manager):
        """Test is_authenticated returns False when no credentials."""
        with patch.object(auth_manager, "_load_stored_credentials", return_value=False):
            result = auth_manager.is_authenticated()
            assert result is False

    def test_is_authenticated_refresh_expired_credentials(self, auth_manager):
        """Test is_authenticated refreshes expired credentials."""
        mock_credentials = Mock()
        mock_credentials.expired = True
        mock_credentials.token = "valid_token"
        auth_manager._credentials = mock_credentials

        with patch.object(auth_manager, "_refresh_credentials"):
            result = auth_manager.is_authenticated()
            assert result is True

    @patch("gcphcp.auth.google_auth.default")
    def test_authenticate_success(self, mock_default, auth_manager):
        """Test successful authentication."""
        mock_credentials = Mock()
        mock_credentials.expired = False
        mock_credentials.token = "test_token"
        mock_default.return_value = (mock_credentials, "test-project")

        with patch.object(auth_manager, "_extract_user_email", return_value="test@example.com"):
            token, email = auth_manager.authenticate()

        assert token == "test_token"
        assert email == "test@example.com"

    def test_authenticate_force_reauth(self, auth_manager, valid_credentials_data):
        """Test authentication with force reauth."""
        # Setup existing credentials
        auth_manager.credentials_path.parent.mkdir(parents=True, exist_ok=True)
        with open(auth_manager.credentials_path, "w") as f:
            json.dump(valid_credentials_data, f)

        with patch.object(auth_manager, "_perform_oauth_flow") as mock_oauth:
            with patch.object(auth_manager, "_extract_user_email", return_value="test@example.com"):
                mock_credentials = Mock()
                mock_credentials.expired = False
                mock_credentials.token = "new_token"
                auth_manager._credentials = mock_credentials

                token, email = auth_manager.authenticate(force_reauth=True)

        mock_oauth.assert_called_once()
        assert token == "new_token"