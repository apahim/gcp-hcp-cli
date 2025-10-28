"""Google Cloud authentication for GCP HCP CLI."""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple

from google.auth import default
from google.auth.credentials import Credentials
from google.auth.exceptions import RefreshError, DefaultCredentialsError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as OAuth2Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore

from .exceptions import (
    AuthenticationError,
    TokenRefreshError,
    CredentialsNotFoundError,
)

logger = logging.getLogger(__name__)

# OAuth 2.0 scopes required for GCP HCP API
REQUIRED_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/cloud-platform",
]

# Default credentials file path
DEFAULT_CREDENTIALS_PATH = Path.home() / ".gcphcp" / "credentials.json"


class GoogleCloudAuth:
    """Google Cloud authentication manager for GCP HCP CLI."""

    def __init__(
        self,
        credentials_path: Optional[Path] = None,
        client_secrets_path: Optional[Path] = None,
        audience: Optional[str] = None,
    ) -> None:
        """Initialize the authentication manager.

        Args:
            credentials_path: Path to stored user credentials file
            client_secrets_path: Path to OAuth client secrets file
            audience: JWT audience for identity tokens
        """
        self.credentials_path = credentials_path or DEFAULT_CREDENTIALS_PATH
        self.client_secrets_path = client_secrets_path
        self.audience = audience
        self._credentials: Optional[Credentials] = None
        self._user_email: Optional[str] = None

    def authenticate(self, force_reauth: bool = False) -> Tuple[str, str]:
        """Authenticate and return identity token and user email.

        Args:
            force_reauth: Force re-authentication even if valid credentials exist

        Returns:
            Tuple of (identity_token, user_email)

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Try to use gcloud print-identity-token without audience first
            try:
                return self._get_identity_token_without_audience()
            except AuthenticationError as e:
                logger.warning(f"Failed to get identity token from gcloud: {e}")
                logger.info("Falling back to OAuth flow")

            # Use the OAuth flow as fallback
            if force_reauth or not self._load_stored_credentials():
                self._perform_oauth_flow()

            # Ensure credentials are fresh
            if self._credentials and self._credentials.expired:
                self._refresh_credentials()

            if not self._credentials:
                raise AuthenticationError("Failed to obtain valid credentials")

            # Use ID token (JWT format) which is what the API expects
            # But without audience claims to avoid rejection
            if hasattr(self._credentials, "id_token") and self._credentials.id_token:
                id_token = self._credentials.id_token
            else:
                raise AuthenticationError("Failed to obtain ID token from credentials")

            # Extract user email from credentials
            user_email = self._extract_user_email()
            if not user_email:
                raise AuthenticationError(
                    "Failed to extract user email from credentials"
                )

            return id_token, user_email

        except (RefreshError, DefaultCredentialsError) as e:
            raise AuthenticationError(f"Authentication failed: {e}", cause=e)

    def _load_stored_credentials(self) -> bool:
        """Load credentials from stored file.

        Returns:
            True if credentials were loaded successfully, False otherwise
        """
        if not self.credentials_path.exists():
            logger.debug(f"No stored credentials found at {self.credentials_path}")
            return False

        try:
            with open(self.credentials_path, "r") as f:
                cred_data = json.load(f)

            # Create credentials from stored data
            self._credentials = OAuth2Credentials(
                token=cred_data.get("token"),
                refresh_token=cred_data.get("refresh_token"),
                id_token=cred_data.get("id_token"),
                token_uri=cred_data.get(
                    "token_uri", "https://oauth2.googleapis.com/token"
                ),
                client_id=cred_data.get("client_id"),
                client_secret=cred_data.get("client_secret"),
                scopes=cred_data.get("scopes", REQUIRED_SCOPES),
            )

            self._user_email = cred_data.get("user_email")
            logger.debug("Successfully loaded stored credentials")
            return True

        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            logger.warning(f"Failed to load stored credentials: {e}")
            return False

    def _perform_oauth_flow(self) -> None:
        """Perform OAuth 2.0 flow to obtain new credentials.

        Raises:
            AuthenticationError: If OAuth flow fails
        """
        if not self.client_secrets_path or not self.client_secrets_path.exists():
            # Try to use application default credentials
            try:
                self._credentials, project_id = default(scopes=REQUIRED_SCOPES)
                logger.info("Using application default credentials")
                return
            except DefaultCredentialsError:
                raise CredentialsNotFoundError(
                    "No OAuth client secrets found and no application default "
                    "credentials available. Please provide client secrets file or "
                    "set up application default credentials."
                )

        try:
            # Perform OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.client_secrets_path), scopes=REQUIRED_SCOPES
            )

            # Use local server flow
            self._credentials = flow.run_local_server(
                port=0,
                prompt="consent",
                authorization_prompt_message="Please visit this URL to authorize:",
                success_message="Authentication successful!",
            )

            logger.info("OAuth flow completed successfully")
            self._save_credentials()

        except Exception as e:
            raise AuthenticationError(f"OAuth flow failed: {e}", cause=e)

    def _refresh_credentials(self) -> None:
        """Refresh expired credentials.

        Raises:
            TokenRefreshError: If token refresh fails
        """
        if not self._credentials:
            raise TokenRefreshError("No credentials available to refresh")

        try:
            request = Request()
            self._credentials.refresh(request)
            logger.debug("Successfully refreshed credentials")

            # Save refreshed credentials
            self._save_credentials()

        except RefreshError as e:
            raise TokenRefreshError(f"Failed to refresh credentials: {e}", cause=e)

    def _extract_user_email(self) -> Optional[str]:
        """Extract user email from credentials.

        Returns:
            User email if available, None otherwise
        """
        if self._user_email:
            return self._user_email

        # Try to get email from token info
        if (
            self._credentials
            and hasattr(self._credentials, "id_token")
            and self._credentials.id_token
        ):
            try:
                # Decode JWT token to extract email
                import base64
                import json

                # JWT tokens have three parts separated by dots
                parts = self._credentials.id_token.split(".")
                if len(parts) >= 2:
                    # Decode the payload (second part)
                    payload = parts[1]
                    # Add padding if needed
                    padding = len(payload) % 4
                    if padding:
                        payload += "=" * (4 - padding)

                    decoded = base64.urlsafe_b64decode(payload)
                    token_data = json.loads(decoded.decode("utf-8"))
                    self._user_email = token_data.get("email")

            except Exception as e:
                logger.warning(f"Failed to extract email from ID token: {e}")

        return self._user_email

    def _save_credentials(self) -> None:
        """Save credentials to file for future use."""
        if not self._credentials:
            return

        # Ensure directory exists
        self.credentials_path.parent.mkdir(parents=True, exist_ok=True)

        # Extract user email before saving
        user_email = self._extract_user_email()

        cred_data = {
            "token": self._credentials.token,
            "refresh_token": getattr(self._credentials, "refresh_token", None),
            "id_token": getattr(self._credentials, "id_token", None),
            "client_id": getattr(self._credentials, "client_id", None),
            "client_secret": getattr(self._credentials, "client_secret", None),
            "token_uri": getattr(
                self._credentials, "token_uri", "https://oauth2.googleapis.com/token"
            ),
            "scopes": getattr(self._credentials, "scopes", REQUIRED_SCOPES),
            "user_email": user_email,
        }

        try:
            with open(self.credentials_path, "w") as f:
                json.dump(cred_data, f, indent=2)

            # Secure the credentials file
            os.chmod(self.credentials_path, 0o600)
            logger.debug(f"Saved credentials to {self.credentials_path}")

        except Exception as e:
            logger.warning(f"Failed to save credentials: {e}")

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests.

        Returns:
            Dictionary containing Authorization and X-User-Email headers

        Raises:
            AuthenticationError: If authentication fails
        """
        access_token, user_email = self.authenticate()

        return {
            "Authorization": f"Bearer {access_token}",
            "X-User-Email": user_email,
        }

    def logout(self) -> None:
        """Remove stored credentials."""
        if self.credentials_path.exists():
            self.credentials_path.unlink()
            logger.info("Stored credentials removed")

        self._credentials = None
        self._user_email = None

    def _get_identity_token_without_audience(self) -> Tuple[str, str]:
        """Get identity token without audience using gcloud.

        Returns:
            Tuple of (identity_token, user_email)

        Raises:
            AuthenticationError: If getting identity token fails
        """
        try:
            # Use gcloud auth print-identity-token without audience
            cmd = ["gcloud", "auth", "print-identity-token"]

            logger.debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Failed to get identity token"
                if (
                    "not logged in" in error_msg.lower()
                    or "no active account" in error_msg.lower()
                ):
                    raise AuthenticationError(
                        "Not authenticated with gcloud. Please run 'gcloud auth login' "
                        "first, or use 'gcphcp auth login' for OAuth flow."
                    )
                raise AuthenticationError(
                    f"gcloud auth print-identity-token failed: {error_msg}"
                )

            identity_token = result.stdout.strip()
            if not identity_token:
                raise AuthenticationError("gcloud returned empty identity token")

            # Get user email from gcloud
            email_cmd = ["gcloud", "config", "get-value", "account"]
            email_result = subprocess.run(
                email_cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )

            user_email = (
                email_result.stdout.strip()
                if email_result.returncode == 0
                else "unknown@example.com"
            )

            logger.debug("Successfully obtained identity token without audience")
            return identity_token, user_email

        except subprocess.TimeoutExpired:
            raise AuthenticationError("Timeout while calling gcloud command")
        except FileNotFoundError:
            raise AuthenticationError(
                "gcloud command not found. Install Google Cloud SDK or use OAuth flow."
            )
        except Exception as e:
            raise AuthenticationError(f"Failed to get identity token: {e}", cause=e)

    def _get_identity_token_with_audience(self) -> Tuple[str, str]:
        """Get identity token with specific audience using gcloud.

        Returns:
            Tuple of (identity_token, user_email)

        Raises:
            AuthenticationError: If getting identity token fails
        """
        try:
            # Use gcloud auth print-access-token instead of identity token
            # since the API rejects JWTs with audience claims
            cmd = ["gcloud", "auth", "print-access-token"]

            logger.debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Failed to get access token"
                if (
                    "not logged in" in error_msg.lower()
                    or "no active account" in error_msg.lower()
                ):
                    raise AuthenticationError(
                        "Not authenticated with gcloud. Please run 'gcloud auth login' "
                        "first, or use 'gcphcp auth login' for OAuth flow."
                    )
                raise AuthenticationError(
                    f"gcloud auth print-access-token failed: {error_msg}"
                )

            access_token = result.stdout.strip()
            if not access_token:
                raise AuthenticationError("gcloud returned empty access token")

            # Get user email from gcloud
            email_cmd = ["gcloud", "config", "get-value", "account"]
            email_result = subprocess.run(
                email_cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )

            user_email = (
                email_result.stdout.strip()
                if email_result.returncode == 0
                else "unknown@example.com"
            )

            logger.debug("Successfully obtained access token")
            return access_token, user_email

        except subprocess.TimeoutExpired:
            raise AuthenticationError("Timeout while calling gcloud command")
        except FileNotFoundError:
            raise AuthenticationError(
                "gcloud command not found. Install Google Cloud SDK or use OAuth flow."
            )
        except Exception as e:
            raise AuthenticationError(f"Failed to get identity token: {e}", cause=e)

    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated.

        Returns:
            True if authenticated with valid credentials, False otherwise
        """
        try:
            if not self._credentials and not self._load_stored_credentials():
                return False

            # Check if credentials are valid and not expired
            if self._credentials and self._credentials.expired:
                self._refresh_credentials()

            return bool(self._credentials and self._credentials.token)

        except Exception:
            return False
