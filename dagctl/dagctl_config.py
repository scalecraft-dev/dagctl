"""Manage ~/.dagctl/ directory configuration and credentials."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class DagctlConfig:
    """Manage ~/.dagctl/ directory and config for local development."""

    CONFIG_DIR = Path.home() / ".dagctl"
    AUTH_FILE = CONFIG_DIR / "auth.json"
    CONFIG_FILE = CONFIG_DIR / "config.yaml"
    CREDENTIALS_DIR = CONFIG_DIR / "credentials"

    def __init__(self) -> None:
        """Initialize config, creating directories if needed."""
        self._ensure_config_dir()
        self._config: Dict[str, Any] = self._load_config()

    def _ensure_config_dir(self) -> None:
        """Ensure ~/.dagctl/ and subdirectories exist with proper permissions."""
        self.CONFIG_DIR.mkdir(mode=0o700, exist_ok=True)
        self.CREDENTIALS_DIR.mkdir(mode=0o700, exist_ok=True)

    def _load_config(self) -> Dict[str, Any]:
        """Load config from ~/.dagctl/config.yaml."""
        if self.CONFIG_FILE.exists():
            with open(self.CONFIG_FILE, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _save_config(self) -> None:
        """Save config to ~/.dagctl/config.yaml."""
        with open(self.CONFIG_FILE, "w") as f:
            yaml.dump(self._config, f, default_flow_style=False)
        os.chmod(self.CONFIG_FILE, 0o600)

    # Organization context
    def get_current_org(self) -> Optional[str]:
        """Get current organization ID."""
        return self._config.get("current_org")

    def set_current_org(self, org_id: str, org_name: Optional[str] = None) -> None:
        """Set current organization."""
        self._config["current_org"] = org_id
        if org_name:
            self._config["current_org_name"] = org_name
        self._save_config()

    def get_current_org_name(self) -> Optional[str]:
        """Get current organization name."""
        return self._config.get("current_org_name")

    # Project context
    def get_current_project(self) -> Optional[str]:
        """Get current project name."""
        return self._config.get("current_project")

    def set_current_project(self, project: str) -> None:
        """Set current project."""
        self._config["current_project"] = project
        self._save_config()

    def get_current_project_id(self) -> Optional[str]:
        """Get current project ID."""
        return self._config.get("current_project_id")

    def set_current_project_id(self, project_id: str) -> None:
        """Set current project ID."""
        self._config["current_project_id"] = project_id
        self._save_config()

    # Auth tokens
    def get_auth_tokens(self) -> Optional[Dict[str, Any]]:
        """Get stored auth tokens."""
        if self.AUTH_FILE.exists():
            with open(self.AUTH_FILE, "r") as f:
                return json.load(f)
        return None

    def save_auth_tokens(self, tokens: Dict[str, Any]) -> None:
        """Save auth tokens to ~/.dagctl/auth.json."""
        with open(self.AUTH_FILE, "w") as f:
            json.dump(tokens, f, indent=2)
        os.chmod(self.AUTH_FILE, 0o600)

    def clear_auth_tokens(self) -> None:
        """Clear stored auth tokens."""
        if self.AUTH_FILE.exists():
            self.AUTH_FILE.unlink()

    def is_authenticated(self) -> bool:
        """Check if user has valid auth tokens."""
        tokens = self.get_auth_tokens()
        if not tokens:
            return False

        # Check if access token exists
        if not tokens.get("access_token"):
            return False

        # Check expiry if available
        expires_at = tokens.get("expires_at")
        if expires_at:
            try:
                expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if datetime.now(expiry.tzinfo) >= expiry:
                    # Token expired, but we might have refresh token
                    return bool(tokens.get("refresh_token"))
            except (ValueError, TypeError):
                pass

        return True

    def get_access_token(self) -> Optional[str]:
        """Get the current access token (uses id_token for API auth)."""
        tokens = self.get_auth_tokens()
        # The API validates ID tokens, not access tokens
        return tokens.get("id_token") if tokens else None

    # Credentials cache
    def _get_credentials_file(self, org: str, project: str) -> Path:
        """Get path to credentials cache file."""
        safe_name = f"{org}_{project}".replace("/", "_").replace(" ", "_")
        return self.CREDENTIALS_DIR / f"{safe_name}.json"

    def get_cached_credentials(
        self, org: Optional[str] = None, project: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached credentials for a project."""
        org = org or self.get_current_org()
        project = project or self.get_current_project()
        if not org or not project:
            return None

        creds_file = self._get_credentials_file(org, project)
        if not creds_file.exists():
            return None

        with open(creds_file, "r") as f:
            creds = json.load(f)

        # Check if credentials are expired
        expires_at = creds.get("expires_at")
        if expires_at:
            try:
                expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if datetime.now(expiry.tzinfo) >= expiry:
                    return None  # Expired
            except (ValueError, TypeError):
                pass

        return creds

    def save_credentials(
        self, creds: Dict[str, Any], org: Optional[str] = None, project: Optional[str] = None
    ) -> None:
        """Save credentials to cache."""
        org = org or self.get_current_org()
        project = project or self.get_current_project()
        if not org or not project:
            raise ValueError("Organization and project must be set")

        creds_file = self._get_credentials_file(org, project)
        with open(creds_file, "w") as f:
            json.dump(creds, f, indent=2)
        os.chmod(creds_file, 0o600)

    def clear_credentials(self) -> None:
        """Clear all cached credentials."""
        for creds_file in self.CREDENTIALS_DIR.glob("*.json"):
            creds_file.unlink()

    # API URL
    def get_api_url(self) -> str:
        """Get the dagctl API URL."""
        return self._config.get("api_url", "https://api.dagctl.io")

    def set_api_url(self, url: str) -> None:
        """Set the dagctl API URL."""
        self._config["api_url"] = url
        self._save_config()

    # Auth0 config
    def get_auth0_domain(self) -> str:
        """Get Auth0 domain."""
        return self._config.get("auth0_domain", "dagctl-us-1.us.auth0.com")

    def get_auth0_client_id(self) -> str:
        """Get Auth0 client ID."""
        return self._config.get("auth0_client_id", "JxXl18ostdRfEpnLkgcv2i2DfcdjOChI")

    # PostgreSQL Proxy config
    def get_pg_proxy_host(self) -> str:
        """Get PostgreSQL proxy host (auto-derived from API URL)."""
        # Allow manual override if set
        if "pg_proxy_host" in self._config:
            return self._config["pg_proxy_host"]
        
        # Auto-derive from API URL
        # api.dev-us-1.dagctl.io → pg-proxy.dev-us-1.dagctl.io
        # api.dagctl.io → pg-proxy.dagctl.io
        api_url = self.get_api_url()
        
        # Extract hostname from URL
        import urllib.parse
        parsed = urllib.parse.urlparse(api_url)
        hostname = parsed.hostname or "localhost"
        
        # Replace 'api' with 'pg-proxy'
        if hostname.startswith("api."):
            return hostname.replace("api.", "pg-proxy.", 1)
        
        # Fallback to localhost
        return "localhost"

    def get_pg_proxy_port(self) -> int:
        """Get PostgreSQL proxy port."""
        return self._config.get("pg_proxy_port", 5432)

    # Summary
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current context."""
        creds = self.get_cached_credentials()
        creds_expiry = None
        if creds and creds.get("expires_at"):
            creds_expiry = creds.get("expires_at")

        return {
            "authenticated": self.is_authenticated(),
            "organization": self.get_current_org_name() or self.get_current_org(),
            "organization_id": self.get_current_org(),
            "project": self.get_current_project(),
            "project_id": self.get_current_project_id(),
            "api_url": self.get_api_url(),
            "credentials_expire": creds_expiry,
        }
