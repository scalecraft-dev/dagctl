"""Tests for cli.py - CLI integration tests."""

from pathlib import Path
from typing import Any, Dict
from unittest import mock

import pytest
from click.testing import CliRunner

from dagctl import __version__
from dagctl.cli import cli
from dagctl.dagctl_config import DagctlConfig


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


class TestCLIBasic:
    """Test basic CLI functionality."""

    def test_cli_version(self, cli_runner):
        """Test --version flag."""
        result = cli_runner.invoke(cli, ["--version"])
        
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_cli_help(self, cli_runner):
        """Test --help flag."""
        result = cli_runner.invoke(cli, ["--help"])
        
        assert result.exit_code == 0
        assert "dagctl" in result.output
        assert "Authenticate and configure SQLMesh" in result.output

    def test_cli_no_args(self, cli_runner):
        """Test CLI with no arguments shows help."""
        result = cli_runner.invoke(cli, [])
        
        assert result.exit_code == 0
        assert "Usage:" in result.output


class TestAuthCommands:
    """Test auth command group."""

    def test_auth_help(self, cli_runner):
        """Test auth command help."""
        result = cli_runner.invoke(cli, ["auth", "--help"])
        
        assert result.exit_code == 0
        assert "Manage authentication" in result.output

    def test_auth_status_not_authenticated(self, cli_runner, temp_dagctl_home: Path):
        """Test auth status when not authenticated."""
        result = cli_runner.invoke(cli, ["auth", "status"])
        
        assert result.exit_code == 0
        assert "Not authenticated" in result.output

    def test_auth_status_authenticated(
        self, cli_runner, temp_dagctl_home: Path, sample_auth_tokens: Dict[str, Any]
    ):
        """Test auth status when authenticated."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        config.set_current_org("org-123", "Test Org")
        config.set_current_project("test-project")
        
        result = cli_runner.invoke(cli, ["auth", "status"])
        
        assert result.exit_code == 0
        assert "Authenticated" in result.output
        assert "Test Org" in result.output
        assert "test-project" in result.output

    def test_auth_logout(
        self, cli_runner, temp_dagctl_home: Path, sample_auth_tokens: Dict[str, Any]
    ):
        """Test auth logout command."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        
        result = cli_runner.invoke(cli, ["auth", "logout"])
        
        assert result.exit_code == 0
        assert "Logged out successfully" in result.output
        
        # Verify tokens were cleared
        assert config.get_auth_tokens() is None


class TestConfigCommands:
    """Test config command group."""

    def test_config_help(self, cli_runner):
        """Test config command help."""
        result = cli_runner.invoke(cli, ["config", "--help"])
        
        assert result.exit_code == 0
        assert "View and manage configuration" in result.output

    def test_config_current_not_authenticated(self, cli_runner, temp_dagctl_home: Path):
        """Test config current when not authenticated."""
        result = cli_runner.invoke(cli, ["config", "current"])
        
        assert result.exit_code == 0
        assert "Not authenticated" in result.output

    def test_config_current_authenticated(
        self, cli_runner, temp_dagctl_home: Path, sample_auth_tokens: Dict[str, Any]
    ):
        """Test config current when authenticated."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        config.set_current_org("org-123", "Test Org")
        config.set_current_project("test-project")
        
        result = cli_runner.invoke(cli, ["config", "current"])
        
        assert result.exit_code == 0
        assert "Test Org" in result.output
        assert "test-project" in result.output

    def test_config_generate_not_authenticated(self, cli_runner, temp_dagctl_home: Path):
        """Test config generate when not authenticated."""
        result = cli_runner.invoke(cli, ["config", "generate"])
        
        assert result.exit_code != 0
        assert "Not authenticated" in result.output

    def test_config_generate_no_project(
        self, cli_runner, temp_dagctl_home: Path, sample_auth_tokens: Dict[str, Any]
    ):
        """Test config generate when no project is set."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        config.set_current_org("org-123", "Test Org")
        
        result = cli_runner.invoke(cli, ["config", "generate"])
        
        assert result.exit_code != 0
        assert "No project set" in result.output


class TestUseProjectCommand:
    """Test use-project command."""

    def test_use_project_help(self, cli_runner):
        """Test use-project command help."""
        result = cli_runner.invoke(cli, ["use-project", "--help"])
        
        assert result.exit_code == 0
        assert "Set the current project context" in result.output

    def test_use_project_not_authenticated(self, cli_runner, temp_dagctl_home: Path):
        """Test use-project when not authenticated."""
        result = cli_runner.invoke(cli, ["use-project", "test-project"])
        
        assert result.exit_code != 0
        assert "Not authenticated" in result.output

    @mock.patch("dagctl.project_commands.verify_project_exists")
    def test_use_project_success(
        self, 
        mock_verify, 
        cli_runner, 
        temp_dagctl_home: Path, 
        sample_auth_tokens: Dict[str, Any]
    ):
        """Test successful use-project command."""
        # Setup authentication
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        config.set_current_org("org-123", "Test Org")
        
        # Mock project verification
        mock_verify.return_value = {"name": "test-project", "id": "proj-456"}
        
        result = cli_runner.invoke(cli, ["use-project", "test-project", "-k"])
        
        assert result.exit_code == 0
        assert "Project set" in result.output
        assert "test-project" in result.output
        
        # Verify project was saved (reload config to pick up changes)
        config2 = DagctlConfig()
        assert config2.get_current_project() == "test-project"

    @mock.patch("dagctl.project_commands.verify_project_exists")
    def test_use_project_not_found(
        self,
        mock_verify,
        cli_runner,
        temp_dagctl_home: Path,
        sample_auth_tokens: Dict[str, Any]
    ):
        """Test use-project with non-existent project."""
        # Setup authentication
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        config.set_current_org("org-123", "Test Org")
        
        # Mock project not found
        from click import ClickException
        mock_verify.side_effect = ClickException("Project 'bad-project' not found")
        
        result = cli_runner.invoke(cli, ["use-project", "bad-project", "-k"])
        
        assert result.exit_code != 0
        assert "not found" in result.output


class TestCLIIntegration:
    """Test CLI command integration."""

    def test_complete_workflow(
        self,
        cli_runner,
        temp_dagctl_home: Path,
        sample_auth_tokens: Dict[str, Any]
    ):
        """Test a complete workflow: auth status -> logout -> auth status."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        config.set_current_org("org-123", "Test Org")
        
        # Check authenticated status
        result1 = cli_runner.invoke(cli, ["auth", "status"])
        assert result1.exit_code == 0
        assert "Authenticated" in result1.output
        
        # Logout
        result2 = cli_runner.invoke(cli, ["auth", "logout"])
        assert result2.exit_code == 0
        
        # Check not authenticated
        result3 = cli_runner.invoke(cli, ["auth", "status"])
        assert result3.exit_code == 0
        assert "Not authenticated" in result3.output

    def test_command_chaining_context(
        self,
        cli_runner,
        temp_dagctl_home: Path,
        sample_auth_tokens: Dict[str, Any]
    ):
        """Test that context persists across commands."""
        config = DagctlConfig()
        config.save_auth_tokens(sample_auth_tokens)
        config.set_current_org("org-123", "Test Org")
        config.set_current_project("project-1")
        
        # First command - check current
        result1 = cli_runner.invoke(cli, ["config", "current"])
        assert "project-1" in result1.output
        
        # Context should still be there
        assert config.get_current_project() == "project-1"
