"""Tests for dagctl_config.py - Configuration management."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from dagctl.dagctl_config import DagctlConfig


class TestDagctlConfigInit:
    """Test DagctlConfig initialization."""

    def test_init_creates_directories(self, temp_dagctl_home: Path):
        """Test that initialization creates necessary directories."""
        config = DagctlConfig()
        assert config.CONFIG_DIR.exists()
        assert config.CREDENTIALS_DIR.exists()

    def test_init_loads_existing_config(self, temp_dagctl_home: Path, sample_config: Dict[str, Any]):
        """Test that initialization loads existing config.yaml."""
        config_file = temp_dagctl_home / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_config, f)

        config = DagctlConfig()
        assert config.get_current_org() == sample_config["current_org"]
        assert config.get_current_project() == sample_config["current_project"]


class TestOrganizationContext:
    """Test organization context management."""

    def test_get_current_org_empty(self, temp_dagctl_home: Path):
        """Test getting organization when not set."""
        config = DagctlConfig()
        assert config.get_current_org() is None

    def test_set_and_get_current_org(self, temp_dagctl_home: Path):
        """Test setting and getting current organization."""
        config = DagctlConfig()
        config.set_current_org("org-123", "Test Org")
        
        assert config.get_current_org() == "org-123"
        assert config.get_current_org_name() == "Test Org"

    def test_set_org_persists_to_file(self, temp_dagctl_home: Path):
        """Test that setting organization persists to config.yaml."""
        config = DagctlConfig()
        config.set_current_org("org-456", "Another Org")
        
        # Load fresh config instance
        config2 = DagctlConfig()
        assert config2.get_current_org() == "org-456"
        assert config2.get_current_org_name() == "Another Org"


class TestProjectContext:
    """Test project context management."""

    def test_get_current_project_empty(self, temp_dagctl_home: Path):
        """Test getting project when not set."""
        config = DagctlConfig()
        assert config.get_current_project() is None

    def test_set_and_get_current_project(self, temp_dagctl_home: Path):
        """Test setting and getting current project."""
        config = DagctlConfig()
        config.set_current_project("my-project")
        config.set_current_project_id("proj-789")
        
        assert config.get_current_project() == "my-project"
        assert config.get_current_project_id() == "proj-789"

    def test_set_project_persists_to_file(self, temp_dagctl_home: Path):
        """Test that setting project persists to config.yaml."""
        config = DagctlConfig()
        config.set_current_project("test-project")
        config.set_current_project_id("proj-123")
        
        # Load fresh config instance
        config2 = DagctlConfig()
        assert config2.get_current_project() == "test-project"
        assert config2.get_current_project_id() == "proj-123"


class TestAuthTokens:
    """Test authentication token management."""

    def test_get_auth_tokens_empty(self, temp_dagctl_home: Path):
        """Test getting tokens when none are saved."""
        config = DagctlConfig()
        assert config.get_auth_tokens() is None

    def test_save_and_get_auth_tokens(self, temp_dagctl_home: Path, sample_auth_tokens: Dict[str, Any]):
        """Test saving and retrieving auth tokens."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        
        tokens = config.get_auth_tokens()
        assert tokens is not None
        assert tokens["access_token"] == sample_auth_tokens["access_token"]
        assert tokens["id_token"] == sample_auth_tokens["id_token"]

    def test_auth_tokens_file_permissions(self, temp_dagctl_home: Path, sample_auth_tokens: Dict[str, Any]):
        """Test that auth tokens file has secure permissions."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        
        auth_file = temp_dagctl_home / "auth.json"
        assert auth_file.exists()
        # Check file is readable/writable only by owner (0600)
        mode = auth_file.stat().st_mode & 0o777
        assert mode == 0o600

    def test_clear_auth_tokens(self, temp_dagctl_home: Path, sample_auth_tokens: Dict[str, Any]):
        """Test clearing auth tokens."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        assert config.get_auth_tokens() is not None
        
        config.clear_auth_tokens()
        assert config.get_auth_tokens() is None

    def test_is_authenticated_valid_tokens(self, temp_dagctl_home: Path, sample_auth_tokens: Dict[str, Any]):
        """Test is_authenticated with valid tokens."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        
        assert config.is_authenticated() is True

    def test_is_authenticated_no_tokens(self, temp_dagctl_home: Path):
        """Test is_authenticated with no tokens."""
        config = DagctlConfig()
        assert config.is_authenticated() is False

    def test_is_authenticated_expired_with_refresh(self, temp_dagctl_home: Path, expired_auth_tokens: Dict[str, Any]):
        """Test is_authenticated with expired tokens but valid refresh token."""
        config = DagctlConfig()
        config.save_auth_tokens(expired_auth_tokens)
        
        # Should return True because refresh_token exists
        assert config.is_authenticated() is True

    def test_is_authenticated_expired_no_refresh(self, temp_dagctl_home: Path):
        """Test is_authenticated with expired tokens and no refresh token."""
        config = DagctlConfig()
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        tokens = {
            "access_token": "expired_token",
            "expires_at": expires_at.isoformat(),
        }
        config.save_auth_tokens(tokens)
        
        assert config.is_authenticated() is False

    def test_get_access_token(self, temp_dagctl_home: Path, sample_auth_tokens: Dict[str, Any]):
        """Test getting access token (returns id_token for API auth)."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        
        token = config.get_access_token()
        assert token == sample_auth_tokens["id_token"]


class TestCredentialsCache:
    """Test credentials caching."""

    def test_get_cached_credentials_empty(self, temp_dagctl_home: Path):
        """Test getting cached credentials when none exist."""
        config = DagctlConfig()
        config.set_current_org("org-123")
        config.set_current_project("project-456")
        
        assert config.get_cached_credentials() is None

    def test_save_and_get_cached_credentials(self, temp_dagctl_home: Path, sample_credentials: Dict[str, Any]):
        """Test saving and retrieving cached credentials."""
        config = DagctlConfig()
        config.set_current_org("org-123")
        config.set_current_project("project-456")
        
        config.save_credentials(sample_credentials)
        
        creds = config.get_cached_credentials()
        assert creds is not None
        assert creds["host"] == sample_credentials["host"]
        assert creds["database"] == sample_credentials["database"]

    def test_cached_credentials_expired(self, temp_dagctl_home: Path):
        """Test that expired credentials return None."""
        config = DagctlConfig()
        config.set_current_org("org-123")
        config.set_current_project("project-456")
        
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        expired_creds = {
            "host": "pg-proxy.dagctl.io",
            "database": "test_db",
            "user": "test_user",
            "password": "test_pass",
            "expires_at": expires_at.isoformat(),
        }
        config.save_credentials(expired_creds)
        
        assert config.get_cached_credentials() is None

    def test_clear_credentials(self, temp_dagctl_home: Path, sample_credentials: Dict[str, Any]):
        """Test clearing all cached credentials."""
        config = DagctlConfig()
        config.set_current_org("org-123")
        config.set_current_project("project-456")
        config.save_credentials(sample_credentials)
        
        config.clear_credentials()
        
        # Verify credentials directory is empty
        creds_dir = temp_dagctl_home / "credentials"
        assert len(list(creds_dir.glob("*.json"))) == 0


class TestAPIURL:
    """Test API URL management."""

    def test_get_api_url_default(self, temp_dagctl_home: Path):
        """Test getting default API URL."""
        config = DagctlConfig()
        assert config.get_api_url() == "https://api.dagctl.io"

    def test_set_and_get_api_url(self, temp_dagctl_home: Path):
        """Test setting and getting custom API URL."""
        config = DagctlConfig()
        config.set_api_url("https://api.staging.dagctl.io")
        
        assert config.get_api_url() == "https://api.staging.dagctl.io"

    def test_api_url_persists(self, temp_dagctl_home: Path):
        """Test that API URL persists across instances."""
        config = DagctlConfig()
        config.set_api_url("https://api.dev.dagctl.io")
        
        config2 = DagctlConfig()
        assert config2.get_api_url() == "https://api.dev.dagctl.io"


class TestAuth0Config:
    """Test Auth0 configuration."""

    def test_get_auth0_domain(self, temp_dagctl_home: Path):
        """Test getting Auth0 domain (prod default)."""
        config = DagctlConfig()
        domain = config.get_auth0_domain()
        assert domain == "dagctl-us-1.us.auth0.com"

    def test_get_auth0_client_id(self, temp_dagctl_home: Path):
        """Test getting Auth0 client ID (prod default)."""
        config = DagctlConfig()
        client_id = config.get_auth0_client_id()
        assert client_id == "JxXl18ostdRfEpnLkgcv2i2DfcdjOChI"


class TestPGProxyConfig:
    """Test PostgreSQL proxy configuration."""

    def test_get_pg_proxy_host_default(self, temp_dagctl_home: Path):
        """Test getting default PG proxy host."""
        config = DagctlConfig()
        assert config.get_pg_proxy_host() == "pg-proxy.dagctl.io"

    def test_get_pg_proxy_host_manual_override(self, temp_dagctl_home: Path):
        """Test that manual override takes precedence."""
        config = DagctlConfig()
        config._config["pg_proxy_host"] = "custom-pg-proxy.example.com"
        config._save_config()
        
        assert config.get_pg_proxy_host() == "custom-pg-proxy.example.com"

    def test_get_pg_proxy_host_derived_from_api(self, temp_dagctl_home: Path):
        """Test PG proxy host is derived from API URL."""
        config = DagctlConfig()
        config.set_api_url("https://api.dev-us-1.dagctl.io")
        
        # Should replace 'api' with 'pg-proxy'
        assert config.get_pg_proxy_host() == "pg-proxy.dev-us-1.dagctl.io"

    def test_get_pg_proxy_port(self, temp_dagctl_home: Path):
        """Test getting PG proxy port."""
        config = DagctlConfig()
        assert config.get_pg_proxy_port() == 5432


class TestContextSummary:
    """Test context summary."""

    def test_get_context_summary_empty(self, temp_dagctl_home: Path):
        """Test context summary with no configuration."""
        config = DagctlConfig()
        summary = config.get_context_summary()
        
        assert summary["authenticated"] is False
        assert summary["organization"] is None
        assert summary["project"] is None
        assert summary["api_url"] == "https://api.dagctl.io"

    def test_get_context_summary_full(
        self, 
        temp_dagctl_home: Path, 
        sample_auth_tokens: Dict[str, Any],
        sample_credentials: Dict[str, Any]
    ):
        """Test context summary with full configuration."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        config.set_current_org("org-123", "Test Org")
        config.set_current_project("test-project")
        config.set_current_project_id("proj-456")
        config.save_credentials(sample_credentials)
        
        summary = config.get_context_summary()
        
        assert summary["authenticated"] is True
        assert summary["organization"] == "Test Org"
        assert summary["organization_id"] == "org-123"
        assert summary["project"] == "test-project"
        assert summary["project_id"] == "proj-456"
        assert summary["credentials_expire"] is not None
