"""Shared pytest fixtures for dagctl tests."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml


@pytest.fixture
def temp_dagctl_home(tmp_path: Path, monkeypatch) -> Path:
    """Create a temporary ~/.dagctl directory for isolated testing."""
    dagctl_dir = tmp_path / ".dagctl"
    dagctl_dir.mkdir(mode=0o700)
    (dagctl_dir / "credentials").mkdir(mode=0o700)
    
    # Patch the DagctlConfig class to use this temp directory
    monkeypatch.setattr("dagctl.dagctl_config.DagctlConfig.CONFIG_DIR", dagctl_dir)
    monkeypatch.setattr("dagctl.dagctl_config.DagctlConfig.AUTH_FILE", dagctl_dir / "auth.json")
    monkeypatch.setattr("dagctl.dagctl_config.DagctlConfig.CONFIG_FILE", dagctl_dir / "config.yaml")
    monkeypatch.setattr("dagctl.dagctl_config.DagctlConfig.CREDENTIALS_DIR", dagctl_dir / "credentials")
    
    return dagctl_dir


@pytest.fixture
def sample_auth_tokens() -> Dict[str, Any]:
    """Sample auth tokens for testing."""
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    return {
        "access_token": "test_access_token_12345",
        "id_token": "test_id_token_67890",
        "refresh_token": "test_refresh_token_abcdef",
        "expires_in": 86400,
        "expires_at": expires_at.isoformat(),
        "token_type": "Bearer",
        "scope": "openid profile email offline_access",
    }


@pytest.fixture
def expired_auth_tokens() -> Dict[str, Any]:
    """Expired auth tokens for testing."""
    expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    return {
        "access_token": "expired_access_token",
        "id_token": "expired_id_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 86400,
        "expires_at": expires_at.isoformat(),
        "token_type": "Bearer",
    }


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample config.yaml content."""
    return {
        "current_org": "test-org-id",
        "current_org_name": "Test Org",
        "current_project": "test-project",
        "current_project_id": "test-project-id",
        "api_url": "https://api.dagctl.io",
        "pg_proxy_host": "pg-proxy.dagctl.io",
        "pg_proxy_port": 5432,
    }


@pytest.fixture
def sample_credentials() -> Dict[str, Any]:
    """Sample credentials for testing."""
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    return {
        "host": "pg-proxy.dagctl.io",
        "port": 5432,
        "database": "org_test_org_test_project",
        "user": "Test Org/test-project",
        "password": "jwt_token_12345",
        "expires_at": expires_at.isoformat(),
    }


@pytest.fixture
def sample_yaml_config() -> Dict[str, Any]:
    """Sample SQLMesh config.yaml structure."""
    return {
        "gateways": {
            "snowflake": {
                "connection": {
                    "type": "snowflake",
                    "account": "my_account",
                    "user": "{{ env_var('SNOWFLAKE_USER') }}",
                    "password": "{{ env_var('SNOWFLAKE_PASSWORD') }}",
                    "database": "my_database",
                    "warehouse": "my_warehouse",
                    "role": "my_role",
                }
            },
            "databricks": {
                "connection": {
                    "type": "databricks",
                    "server_hostname": "{{ env_var('DATABRICKS_HOST') }}",
                    "http_path": "{{ env_var('DATABRICKS_HTTP_PATH') }}",
                    "access_token": "{{ env_var('DATABRICKS_TOKEN') }}",
                }
            },
        },
        "default_gateway": "snowflake",
        "model_defaults": {
            "dialect": "snowflake",
        },
    }


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory for testing."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def config_yaml_file(temp_project_dir: Path, sample_yaml_config: Dict[str, Any]) -> Path:
    """Create a sample config.yaml file in the temp project."""
    config_file = temp_project_dir / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(sample_yaml_config, f)
    return config_file


@pytest.fixture
def config_py_file(temp_project_dir: Path) -> Path:
    """Create a sample config.py file in the temp project."""
    config_file = temp_project_dir / "config.py"
    config_file.write_text("""
from sqlmesh.core.config import Config

config = Config()
""")
    return config_file
