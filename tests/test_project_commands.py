"""Tests for project_commands.py - Project command helpers."""

import os
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from dagctl.project_commands import (
    convert_yaml_to_python_config,
    detect_config_format,
    detect_gateways_from_config,
    generate_env_content,
    generate_python_config,
    generate_yaml_config,
)


class TestDetectGatewaysFromConfig:
    """Test detect_gateways_from_config function."""

    def test_detect_from_config_yaml(self, temp_project_dir: Path, sample_yaml_config: Dict[str, Any]):
        """Test detecting gateways from config.yaml."""
        config_file = temp_project_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_yaml_config, f)
        
        os.chdir(temp_project_dir)
        gateways = detect_gateways_from_config()
        
        assert "snowflake" in gateways
        assert "databricks" in gateways
        assert len(gateways) == 2

    def test_detect_from_config_yml(self, temp_project_dir: Path, sample_yaml_config: Dict[str, Any]):
        """Test detecting gateways from config.yml."""
        config_file = temp_project_dir / "config.yml"
        with open(config_file, "w") as f:
            yaml.dump(sample_yaml_config, f)
        
        os.chdir(temp_project_dir)
        gateways = detect_gateways_from_config()
        
        assert "snowflake" in gateways
        assert "databricks" in gateways

    def test_detect_no_config(self, temp_project_dir: Path):
        """Test when no config file exists."""
        os.chdir(temp_project_dir)
        gateways = detect_gateways_from_config()
        
        assert gateways == []

    def test_detect_no_gateways_section(self, temp_project_dir: Path):
        """Test when config exists but has no gateways section."""
        config_file = temp_project_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump({"model_defaults": {"dialect": "snowflake"}}, f)
        
        os.chdir(temp_project_dir)
        gateways = detect_gateways_from_config()
        
        assert gateways == []


class TestDetectConfigFormat:
    """Test detect_config_format function."""

    def test_detect_yaml_format(self, temp_project_dir: Path):
        """Test detecting YAML config format."""
        (temp_project_dir / "config.yaml").touch()
        
        os.chdir(temp_project_dir)
        fmt = detect_config_format()
        
        assert fmt == "yaml"

    def test_detect_yml_format(self, temp_project_dir: Path):
        """Test detecting YML config format."""
        (temp_project_dir / "config.yml").touch()
        
        os.chdir(temp_project_dir)
        fmt = detect_config_format()
        
        assert fmt == "yaml"

    def test_detect_python_format(self, temp_project_dir: Path):
        """Test detecting Python config format."""
        (temp_project_dir / "config.py").touch()
        
        os.chdir(temp_project_dir)
        fmt = detect_config_format()
        
        assert fmt == "python"

    def test_detect_no_config(self, temp_project_dir: Path):
        """Test when no config file exists."""
        os.chdir(temp_project_dir)
        fmt = detect_config_format()
        
        assert fmt is None

    def test_detect_python_takes_precedence(self, temp_project_dir: Path):
        """Test that Python config takes precedence over YAML."""
        (temp_project_dir / "config.py").touch()
        (temp_project_dir / "config.yaml").touch()
        
        os.chdir(temp_project_dir)
        fmt = detect_config_format()
        
        assert fmt == "python"


class TestGenerateYamlConfig:
    """Test generate_yaml_config function."""

    def test_generate_yaml_single_gateway(self, sample_credentials: Dict[str, Any]):
        """Test generating YAML config for single gateway."""
        yaml_str = generate_yaml_config(
            gateways=["snowflake"],
            credentials=sample_credentials,
            org_name="TestOrg",
            project_name="test-project",
        )
        
        assert "snowflake:" in yaml_str
        assert "state_connection:" in yaml_str
        assert f"host: {sample_credentials['host']}" in yaml_str
        assert f"database: {sample_credentials['database']}" in yaml_str
        assert f"user: {sample_credentials['user']}" in yaml_str
        assert "type: postgres" in yaml_str

    def test_generate_yaml_multiple_gateways(self, sample_credentials: Dict[str, Any]):
        """Test generating YAML config for multiple gateways."""
        yaml_str = generate_yaml_config(
            gateways=["snowflake", "databricks", "bigquery"],
            credentials=sample_credentials,
            org_name="TestOrg",
            project_name="test-project",
        )
        
        assert "snowflake:" in yaml_str
        assert "databricks:" in yaml_str
        assert "bigquery:" in yaml_str
        assert yaml_str.count("state_connection:") == 3

    def test_generate_yaml_includes_metadata(self, sample_credentials: Dict[str, Any]):
        """Test that generated YAML includes metadata comments."""
        yaml_str = generate_yaml_config(
            gateways=["snowflake"],
            credentials=sample_credentials,
            org_name="TestOrg",
            project_name="test-project",
        )
        
        assert "# dagctl state config for project: test-project" in yaml_str
        assert "# Organization: TestOrg" in yaml_str
        assert "# Refresh with: dagctl use-project test-project -k" in yaml_str


class TestGeneratePythonConfig:
    """Test generate_python_config function."""

    def test_generate_python_single_gateway(self, sample_credentials: Dict[str, Any]):
        """Test generating Python config for single gateway."""
        py_str = generate_python_config(
            gateways=["snowflake"],
            credentials=sample_credentials,
            org_name="TestOrg",
            project_name="test-project",
        )
        
        assert "from dagctl import get_state_connection" in py_str
        assert '"snowflake"' in py_str
        assert '"state_connection": get_state_connection()' in py_str

    def test_generate_python_multiple_gateways(self, sample_credentials: Dict[str, Any]):
        """Test generating Python config for multiple gateways."""
        py_str = generate_python_config(
            gateways=["snowflake", "databricks"],
            credentials=sample_credentials,
            org_name="TestOrg",
            project_name="test-project",
        )
        
        assert '"snowflake"' in py_str
        assert '"databricks"' in py_str
        assert py_str.count("get_state_connection()") >= 2

    def test_generate_python_includes_metadata(self, sample_credentials: Dict[str, Any]):
        """Test that generated Python includes metadata comments."""
        py_str = generate_python_config(
            gateways=["snowflake"],
            credentials=sample_credentials,
            org_name="TestOrg",
            project_name="test-project",
        )
        
        assert "# dagctl state config for project: test-project" in py_str
        assert "# Organization: TestOrg" in py_str
        assert "Token auto-refreshes via dagctl" in py_str


class TestGenerateEnvContent:
    """Test generate_env_content function."""

    def test_generate_env_basic(self, sample_credentials: Dict[str, Any]):
        """Test basic environment variable generation."""
        env_str = generate_env_content(
            gateways=["snowflake"],
            credentials=sample_credentials,
            org_name="TestOrg",
            project_name="test-project",
        )
        
        assert "SQLMESH__GATEWAYS__SNOWFLAKE__STATE_CONNECTION__TYPE=postgres" in env_str
        assert f"SQLMESH__GATEWAYS__SNOWFLAKE__STATE_CONNECTION__HOST={sample_credentials['host']}" in env_str
        assert f"SQLMESH__GATEWAYS__SNOWFLAKE__STATE_CONNECTION__DATABASE={sample_credentials['database']}" in env_str

    def test_generate_env_export_format(self, sample_credentials: Dict[str, Any]):
        """Test environment variable generation with export format."""
        env_str = generate_env_content(
            gateways=["snowflake"],
            credentials=sample_credentials,
            org_name="TestOrg",
            project_name="test-project",
            export_format=True,
        )
        
        assert "export SQLMESH__GATEWAYS__SNOWFLAKE__STATE_CONNECTION__TYPE=postgres" in env_str
        assert "# dagctl state credentials" not in env_str  # No comments in export format

    def test_generate_env_multiple_gateways(self, sample_credentials: Dict[str, Any]):
        """Test environment variable generation for multiple gateways."""
        env_str = generate_env_content(
            gateways=["snowflake", "databricks"],
            credentials=sample_credentials,
            org_name="TestOrg",
            project_name="test-project",
        )
        
        assert "SQLMESH__GATEWAYS__SNOWFLAKE__STATE_CONNECTION__TYPE=postgres" in env_str
        assert "SQLMESH__GATEWAYS__DATABRICKS__STATE_CONNECTION__TYPE=postgres" in env_str

    def test_generate_env_uppercase_gateway(self, sample_credentials: Dict[str, Any]):
        """Test that gateway names are properly uppercased."""
        env_str = generate_env_content(
            gateways=["my-gateway"],
            credentials=sample_credentials,
            org_name="TestOrg",
            project_name="test-project",
        )
        
        assert "SQLMESH__GATEWAYS__MY-GATEWAY__STATE_CONNECTION__TYPE=postgres" in env_str


class TestConvertYamlToPythonConfig:
    """Test convert_yaml_to_python_config function."""

    def test_convert_basic_config(self, sample_yaml_config: Dict[str, Any]):
        """Test converting basic YAML config to Python."""
        py_str = convert_yaml_to_python_config(
            yaml_config=sample_yaml_config,
            org_name="TestOrg",
            project_name="test-project",
        )
        
        assert "from dagctl import get_state_connection" in py_str
        assert "gateways = {" in py_str
        assert '"snowflake"' in py_str
        assert '"databricks"' in py_str
        assert "get_state_connection()" in py_str

    def test_convert_preserves_connection_config(self, sample_yaml_config: Dict[str, Any]):
        """Test that connection configuration is preserved."""
        py_str = convert_yaml_to_python_config(
            yaml_config=sample_yaml_config,
            org_name="TestOrg",
            project_name="test-project",
        )
        
        assert '"type": "snowflake"' in py_str
        assert '"account": "my_account"' in py_str
        assert '"database": "my_database"' in py_str

    def test_convert_handles_env_vars(self, sample_yaml_config: Dict[str, Any]):
        """Test that environment variable references are handled."""
        py_str = convert_yaml_to_python_config(
            yaml_config=sample_yaml_config,
            org_name="TestOrg",
            project_name="test-project",
        )
        
        assert 'os.environ.get("SNOWFLAKE_USER")' in py_str
        assert 'os.environ.get("SNOWFLAKE_PASSWORD")' in py_str
        assert 'os.environ.get("DATABRICKS_HOST")' in py_str

    def test_convert_preserves_default_gateway(self):
        """Test that default_gateway is preserved."""
        yaml_config = {
            "gateways": {
                "snowflake": {
                    "connection": {"type": "snowflake"}
                }
            },
            "default_gateway": "snowflake",
        }
        
        py_str = convert_yaml_to_python_config(
            yaml_config=yaml_config,
            org_name="TestOrg",
            project_name="test-project",
        )
        
        assert 'default_gateway="snowflake"' in py_str

    def test_convert_preserves_model_defaults(self, sample_yaml_config: Dict[str, Any]):
        """Test that model_defaults are preserved."""
        py_str = convert_yaml_to_python_config(
            yaml_config=sample_yaml_config,
            org_name="TestOrg",
            project_name="test-project",
        )
        
        assert "model_defaults" in py_str
        assert '"dialect": "snowflake"' in py_str

    def test_convert_creates_config_object(self, sample_yaml_config: Dict[str, Any]):
        """Test that Config object is created."""
        py_str = convert_yaml_to_python_config(
            yaml_config=sample_yaml_config,
            org_name="TestOrg",
            project_name="test-project",
        )
        
        assert "config = Config(" in py_str
        assert "gateways=gateways" in py_str

    def test_convert_includes_docstring(self, sample_yaml_config: Dict[str, Any]):
        """Test that generated Python includes docstring."""
        py_str = convert_yaml_to_python_config(
            yaml_config=sample_yaml_config,
            org_name="TestOrg",
            project_name="test-project",
        )
        
        assert '"""SQLMesh configuration for test-project' in py_str
        assert "Auto-generated from config.yaml by dagctl" in py_str

    def test_convert_imports_required_modules(self, sample_yaml_config: Dict[str, Any]):
        """Test that all required imports are included."""
        py_str = convert_yaml_to_python_config(
            yaml_config=sample_yaml_config,
            org_name="TestOrg",
            project_name="test-project",
        )
        
        assert "import datetime" in py_str
        assert "import os" in py_str
        assert "from dagctl import get_state_connection" in py_str
        assert "from sqlmesh.core.config import Config" in py_str
