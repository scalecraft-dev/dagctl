"""Tests for state.py - State connection management."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict
from unittest import mock

import pytest
import requests

from dagctl.dagctl_config import DagctlConfig
from dagctl.state import (
    _compute_state_credentials,
    _refresh_auth_token,
    get_fresh_token,
    get_state_connection,
)


class TestComputeStateCredentials:
    """Test _compute_state_credentials function."""

    def test_compute_credentials_basic(self, temp_dagctl_home: Path):
        """Test basic credential computation."""
        config = DagctlConfig()
        config.set_current_org("test-org-id", "TestOrg")
        
        creds = _compute_state_credentials(config, "my-project", "jwt_token_xyz")
        
        assert creds["host"] == "pg-proxy.dagctl.io"
        assert creds["port"] == 5432
        assert creds["database"] == "org_testorg_my_project"
        # Username is lowercased to stay consistent with the lowercased org
        # namespace and project secret that management-api resolves against.
        assert creds["user"] == "testorg/my-project"
        assert creds["password"] == "jwt_token_xyz"

    def test_compute_credentials_sanitizes_names(self, temp_dagctl_home: Path):
        """Test that database names are sanitized properly."""
        config = DagctlConfig()
        config.set_current_org("org-123", "Test-Org Name")
        
        creds = _compute_state_credentials(config, "my-test-project", "token")
        
        # Spaces and hyphens should be converted to underscores
        assert creds["database"] == "org_test_org_name_my_test_project"

    def test_compute_credentials_custom_pg_proxy(self, temp_dagctl_home: Path):
        """Test with custom PG proxy configuration."""
        config = DagctlConfig()
        config.set_current_org("org-456", "CustomOrg")
        config._config["pg_proxy_host"] = "custom-proxy.example.com"
        config._config["pg_proxy_port"] = 5433
        config._save_config()
        
        creds = _compute_state_credentials(config, "project", "token")
        
        assert creds["host"] == "custom-proxy.example.com"
        assert creds["port"] == 5433

    def test_compute_credentials_no_org_raises(self, temp_dagctl_home: Path):
        """Test that missing organization raises error."""
        config = DagctlConfig()
        
        with pytest.raises(RuntimeError, match="Organization not set"):
            _compute_state_credentials(config, "project", "token")


class TestRefreshAuthToken:
    """Test _refresh_auth_token function."""

    @mock.patch("dagctl.state.requests.post")
    def test_refresh_token_success(self, mock_post, temp_dagctl_home: Path):
        """Test successful token refresh."""
        config = DagctlConfig()
        
        # Mock successful response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "id_token": "new_id_token",
            "expires_in": 86400,
        }
        mock_post.return_value = mock_response
        
        new_tokens = _refresh_auth_token(config, "refresh_token_xyz", insecure=False)
        
        assert new_tokens["access_token"] == "new_access_token"
        assert new_tokens["id_token"] == "new_id_token"
        assert "expires_at" in new_tokens
        assert "refresh_token" in new_tokens  # Should preserve old refresh token

    @mock.patch("dagctl.state.requests.post")
    def test_refresh_token_failure(self, mock_post, temp_dagctl_home: Path):
        """Test failed token refresh."""
        config = DagctlConfig()
        
        # Mock failed response
        mock_response = mock.Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Invalid refresh token",
        }
        mock_post.return_value = mock_response
        
        with pytest.raises(RuntimeError, match="Token refresh failed"):
            _refresh_auth_token(config, "invalid_token", insecure=False)

    @mock.patch("dagctl.state.requests.post")
    def test_refresh_token_network_error(self, mock_post, temp_dagctl_home: Path):
        """Test network error during token refresh."""
        config = DagctlConfig()
        
        # Mock network error
        mock_post.side_effect = requests.RequestException("Network error")
        
        with pytest.raises(RuntimeError, match="Network error refreshing token"):
            _refresh_auth_token(config, "refresh_token", insecure=False)

    @mock.patch("dagctl.state.requests.post")
    def test_refresh_token_saves_to_config(self, mock_post, temp_dagctl_home: Path):
        """Test that refreshed tokens are saved to config."""
        config = DagctlConfig()
        
        # Mock successful response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "id_token": "new_id_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 86400,
        }
        mock_post.return_value = mock_response
        
        _refresh_auth_token(config, "old_refresh_token", insecure=False)
        
        # Verify tokens were saved
        saved_tokens = config.get_auth_tokens()
        assert saved_tokens["access_token"] == "new_access_token"
        assert saved_tokens["refresh_token"] == "new_refresh_token"


class TestGetFreshToken:
    """Test get_fresh_token function."""

    def test_get_fresh_token_valid(self, temp_dagctl_home: Path, sample_auth_tokens: Dict[str, Any]):
        """Test getting token when it's still valid."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        
        token = get_fresh_token(config, insecure=False)
        
        assert token == sample_auth_tokens["access_token"]

    def test_get_fresh_token_not_authenticated(self, temp_dagctl_home: Path):
        """Test error when not authenticated."""
        config = DagctlConfig()
        
        with pytest.raises(RuntimeError, match="Not authenticated"):
            get_fresh_token(config, insecure=False)

    @mock.patch("dagctl.state._refresh_auth_token")
    def test_get_fresh_token_expired_refreshes(
        self, mock_refresh, temp_dagctl_home: Path, expired_auth_tokens: Dict[str, Any]
    ):
        """Test that expired token triggers refresh."""
        config = DagctlConfig()
        config.save_auth_tokens(expired_auth_tokens)
        
        # Mock refresh response
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        refreshed_tokens = {
            "access_token": "refreshed_access_token",
            "id_token": "refreshed_id_token",
            "refresh_token": "refresh_token",
            "expires_at": expires_at.isoformat(),
        }
        mock_refresh.return_value = refreshed_tokens
        
        token = get_fresh_token(config, insecure=False)
        
        assert token == "refreshed_access_token"
        mock_refresh.assert_called_once()

    def test_get_fresh_token_expired_no_refresh(self, temp_dagctl_home: Path):
        """Test error when token expired and no refresh token."""
        config = DagctlConfig()
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        tokens = {
            "access_token": "expired_token",
            "expires_at": expires_at.isoformat(),
        }
        config.save_auth_tokens(tokens)
        
        with pytest.raises(RuntimeError, match="no refresh token available"):
            get_fresh_token(config, insecure=False)

    @mock.patch("dagctl.state._refresh_auth_token")
    def test_get_fresh_token_expiring_soon_refreshes(
        self, mock_refresh, temp_dagctl_home: Path
    ):
        """Test that token expiring in <5 minutes triggers refresh."""
        config = DagctlConfig()
        
        # Token expiring in 2 minutes
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=2)
        tokens = {
            "access_token": "expiring_soon_token",
            "refresh_token": "refresh_token",
            "expires_at": expires_at.isoformat(),
        }
        config.save_auth_tokens(tokens)
        
        # Mock refresh response
        new_expires = datetime.now(timezone.utc) + timedelta(hours=24)
        refreshed_tokens = {
            "access_token": "refreshed_token",
            "expires_at": new_expires.isoformat(),
        }
        mock_refresh.return_value = refreshed_tokens
        
        token = get_fresh_token(config, insecure=False)
        
        assert token == "refreshed_token"
        mock_refresh.assert_called_once()


class TestGetStateConnection:
    """Test get_state_connection function."""

    def test_get_state_connection_success(
        self, temp_dagctl_home: Path, sample_auth_tokens: Dict[str, Any]
    ):
        """Test successful state connection retrieval."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        config.set_current_org("test-org", "TestOrg")
        config.set_current_project("test-project")
        
        conn = get_state_connection(gateway="snowflake", insecure=False)
        
        assert conn["type"] == "postgres"
        assert conn["host"] == "pg-proxy.dagctl.io"
        assert conn["port"] == 5432
        assert conn["database"] == "org_testorg_test_project"
        # Username is lowercased to match management-api's org/project lookups.
        assert conn["user"] == "testorg/test-project"
        assert conn["password"] == sample_auth_tokens["access_token"]
        # sslmode defaults to require so the JWT is never sent in cleartext.
        assert conn["sslmode"] == "require"
        # verify-full is unimplementable against the pinned SQLMesh config
        # (extra="forbid", no sslrootcert field); ensure we never emit it.
        assert "sslrootcert" not in conn

    def test_get_state_connection_sslmode_config_override(
        self, temp_dagctl_home: Path, sample_auth_tokens: Dict[str, Any]
    ):
        """sslmode can be overridden via config for a non-TLS proxy."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        config.set_current_org("test-org", "TestOrg")
        config.set_current_project("test-project")
        config.set_pg_proxy_sslmode("disable")

        conn = get_state_connection(gateway="snowflake", insecure=False)

        assert conn["sslmode"] == "disable"

    def test_get_state_connection_sslmode_env_override(
        self, temp_dagctl_home: Path, sample_auth_tokens: Dict[str, Any], monkeypatch
    ):
        """DAGCTL_STATE_SSLMODE takes precedence over config."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        config.set_current_org("test-org", "TestOrg")
        config.set_current_project("test-project")
        config.set_pg_proxy_sslmode("disable")
        monkeypatch.setenv("DAGCTL_STATE_SSLMODE", "prefer")

        conn = get_state_connection(gateway="snowflake", insecure=False)

        assert conn["sslmode"] == "prefer"

    def test_get_state_connection_sslmode_invalid(
        self, temp_dagctl_home: Path, sample_auth_tokens: Dict[str, Any], monkeypatch
    ):
        """An invalid sslmode raises a clear error rather than reaching libpq."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        config.set_current_org("test-org", "TestOrg")
        config.set_current_project("test-project")
        monkeypatch.setenv("DAGCTL_STATE_SSLMODE", "bogus")

        with pytest.raises(RuntimeError, match="Invalid sslmode"):
            get_state_connection(gateway="snowflake", insecure=False)

    def test_get_state_connection_not_authenticated(self, temp_dagctl_home: Path):
        """Test error when not authenticated."""
        config = DagctlConfig()
        
        with pytest.raises(RuntimeError, match="Not authenticated"):
            get_state_connection()

    def test_get_state_connection_no_project(
        self, temp_dagctl_home: Path, sample_auth_tokens: Dict[str, Any]
    ):
        """Test error when no project is set."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        config.set_current_org("test-org", "TestOrg")
        # Don't set project
        
        with pytest.raises(RuntimeError, match="No project set"):
            get_state_connection()

    @mock.patch("dagctl.state.get_fresh_token")
    def test_get_state_connection_refreshes_token(
        self, mock_get_fresh, temp_dagctl_home: Path, sample_auth_tokens: Dict[str, Any]
    ):
        """Test that get_state_connection calls get_fresh_token."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        config.set_current_org("test-org", "TestOrg")
        config.set_current_project("test-project")
        
        mock_get_fresh.return_value = "fresh_token_xyz"
        
        conn = get_state_connection(insecure=False)
        
        assert conn["password"] == "fresh_token_xyz"
        mock_get_fresh.assert_called_once()

    def test_get_state_connection_optional_gateway(
        self, temp_dagctl_home: Path, sample_auth_tokens: Dict[str, Any]
    ):
        """Test that gateway parameter is optional."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        config.set_current_org("test-org", "TestOrg")
        config.set_current_project("test-project")
        
        # Should work without gateway parameter
        conn = get_state_connection()
        
        assert conn["type"] == "postgres"
        assert conn["database"] == "org_testorg_test_project"
