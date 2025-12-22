"""Project commands for dagctl."""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import requests
import yaml
from rich.console import Console

from .dagctl_config import DagctlConfig

console = Console()


def detect_gateways_from_config() -> List[str]:
    """Detect gateway names from local config.yaml."""
    config_paths = [
        Path("config.yaml"),
        Path("config.yml"),
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config_data = yaml.safe_load(f)
                if config_data and "gateways" in config_data:
                    return list(config_data["gateways"].keys())
            except Exception:
                pass
    
    return []


def detect_config_format() -> Optional[str]:
    """Detect config format based on existing files.
    
    Returns 'yaml', 'python', or None if not detected.
    """
    if Path("config.py").exists():
        return "python"
    elif Path("config.yaml").exists() or Path("config.yml").exists():
        return "yaml"
    return None


def generate_yaml_config(
    gateways: List[str],
    credentials: Dict[str, Any],
    org_name: str,
    project_name: str,
) -> str:
    """Generate YAML config snippet for SQLMesh state connection."""
    lines = [
        f"# dagctl state config for project: {project_name}",
        f"# Organization: {org_name}",
        f"# Expires: {credentials.get('expires_at', 'unknown')}",
        f"# Refresh with: dagctl use-project {project_name} -k",
        "",
        "gateways:",
    ]
    
    for gateway in gateways:
        lines.extend([
            f"  {gateway}:",
            "    state_connection:",
            "      type: postgres",
            f"      host: {credentials['host']}",
            f"      port: {credentials['port']}",
            f"      database: {credentials['database']}",
            f"      user: {credentials['user']}",
            f"      password: {credentials['password']}",
        ])
    
    return "\n".join(lines)


def generate_python_config(
    gateways: List[str],
    credentials: Dict[str, Any],
    org_name: str,
    project_name: str,
) -> str:
    """Generate Python config snippet for SQLMesh state connection."""
    lines = [
        f"# dagctl state config for project: {project_name}",
        f"# Organization: {org_name}",
        f"# Expires: Token auto-refreshes via dagctl",
        f"# Set project: dagctl use-project {project_name} -k",
        "",
        "# Import dagctl state connection helper",
        "from dagctl import get_state_connection",
        "",
        "# Example: Add state_connection to your gateway(s)",
        "gateways = {",
    ]
    
    for i, gateway in enumerate(gateways):
        lines.append(f'    "{gateway}": {{')
        lines.append('        "state_connection": get_state_connection(),')
        lines.append('    },')
    
    lines.append("}")
    lines.append("")
    lines.append("# Note: get_state_connection() will automatically refresh the JWT token")
    lines.append("# when it expires, so you don't need to manually refresh credentials.")
    
    return "\n".join(lines)


def generate_env_content(
    gateways: List[str],
    credentials: Dict[str, Any],
    org_name: str,
    project_name: str,
    export_format: bool = False,
) -> str:
    """Generate environment variables for SQLMesh state connection.
    
    Args:
        gateways: List of gateway names
        credentials: Credentials dict with host, port, database, user, password
        org_name: Organization name for comments
        project_name: Project name for comments
        export_format: If True, output shell export commands (for eval)
    """
    lines = []
    
    if not export_format:
        lines.extend([
            f"# dagctl state credentials for project: {project_name}",
            f"# Organization: {org_name}",
            f"# Expires: {credentials.get('expires_at', 'unknown')}",
            "# Refresh with: dagctl config refresh",
            "",
        ])
    
    prefix_fmt = "export " if export_format else ""
    
    for gateway in gateways:
        gateway_upper = gateway.upper()
        prefix = f"SQLMESH__GATEWAYS__{gateway_upper}__STATE_CONNECTION"
        
        lines.extend([
            f"{prefix_fmt}{prefix}__TYPE=postgres",
            f"{prefix_fmt}{prefix}__HOST={credentials['host']}",
            f"{prefix_fmt}{prefix}__PORT={credentials['port']}",
            f"{prefix_fmt}{prefix}__DATABASE={credentials['database']}",
            f"{prefix_fmt}{prefix}__USER={credentials['user']}",
            f"{prefix_fmt}{prefix}__PASSWORD={credentials['password']}",
        ])
        if not export_format:
            lines.append("")
    
    return "\n".join(lines)


def convert_yaml_to_python_config(yaml_config: Dict[str, Any], org_name: str, project_name: str) -> str:
    """Convert YAML config to Python config with auto-refreshing state connection.
    
    Args:
        yaml_config: Parsed YAML config dictionary
        org_name: Organization name
        project_name: Project name
    
    Returns:
        Python config file content as string
    """
    lines = [
        f'"""SQLMesh configuration for {project_name}',
        "",
        "Auto-generated from config.yaml by dagctl.",
        "State connection uses dagctl's auto-refreshing credentials.",
        '"""',
        "",
        "import datetime",
        "import os",
        "from dagctl import get_state_connection",
        "from sqlmesh.core.config import Config",
        "",
    ]
    
    # Build config dict
    config_dict = {}
    
    # Process gateways
    if "gateways" in yaml_config:
        gateways_dict = {}
        for gateway_name, gateway_config in yaml_config["gateways"].items():
            gateways_dict[gateway_name] = {}
            
            # Add connection config
            if "connection" in gateway_config:
                conn = {}
                for key, value in gateway_config["connection"].items():
                    if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                        # Store as placeholder for os.environ - will be formatted later
                        env_var = value.strip("{{ }}").replace("env_var('", "").replace("')", "").replace('")', '')
                        conn[key] = f"__ENV__{env_var}__"
                    else:
                        conn[key] = value
                gateways_dict[gateway_name]["connection"] = conn
            
            # Note: state_connection will be added dynamically
        
        config_dict["gateways"] = gateways_dict
    
    # Add default_gateway
    if "default_gateway" in yaml_config:
        config_dict["default_gateway"] = yaml_config["default_gateway"]
    
    # Add model_defaults
    if "model_defaults" in yaml_config:
        config_dict["model_defaults"] = yaml_config["model_defaults"]
    
    # Now generate the Python code
    lines.append("# Build gateways with auto-refreshing state connection")
    lines.append("gateways = {")
    
    if "gateways" in config_dict:
        for gateway_name, gateway_config in config_dict["gateways"].items():
            lines.append(f'    "{gateway_name}": {{')
            
            # Add connection config
            if "connection" in gateway_config:
                lines.append('        "connection": {')
                for key, value in gateway_config["connection"].items():
                    if isinstance(value, str) and value.startswith("__ENV__") and value.endswith("__"):
                        env_var = value.replace("__ENV__", "").replace("__", "")
                        lines.append(f'            "{key}": os.environ.get("{env_var}"),')
                    elif isinstance(value, str):
                        lines.append(f'            "{key}": "{value}",')
                    elif isinstance(value, (int, float, bool)):
                        lines.append(f'            "{key}": {value},')
                    else:
                        lines.append(f'            "{key}": {repr(value)},')
                lines.append('        },')
            
            # Add auto-refreshing state connection
            lines.append('        "state_connection": get_state_connection(),')
            
            lines.append('    },')
    
    lines.append("}")
    lines.append("")
    
    # Create Config object
    lines.append("# Create SQLMesh Config object")
    lines.append("config = Config(")
    lines.append("    gateways=gateways,")
    
    if "default_gateway" in config_dict:
        lines.append(f'    default_gateway="{config_dict["default_gateway"]}",')
    
    if "model_defaults" in config_dict:
        lines.append("    model_defaults={")
        for key, value in config_dict["model_defaults"].items():
            if isinstance(value, str):
                lines.append(f'        "{key}": "{value}",')
            else:
                lines.append(f'        "{key}": {repr(value)},')
        lines.append("    },")
    
    lines.append(")")
    lines.append("")
    
    return "\n".join(lines)


def verify_project_exists(config: DagctlConfig, project: str, verify_ssl: bool = True) -> Dict[str, Any]:
    """Verify that a project exists in the organization.
    
    Returns:
        Project data dictionary
    """
    api_url = config.get_api_url()
    org_id = config.get_current_org()
    access_token = config.get_access_token()
    
    if not access_token:
        raise click.ClickException("Not authenticated. Run: dagctl auth login --org <org>")
    
    if not org_id:
        raise click.ClickException("No organization set. Run: dagctl auth login --org <org>")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Organization-ID": org_id,
    }
    
    # Look up the project to verify it exists
    projects_response = requests.get(
        f"{api_url}/api/v1/projects",
        headers=headers,
        verify=verify_ssl,
    )
    
    if projects_response.status_code == 401:
        raise click.ClickException(f"Authentication error (401): {projects_response.text}")
    
    if projects_response.status_code != 200:
        raise click.ClickException(f"Failed to list projects (HTTP {projects_response.status_code}): {projects_response.text}")
    
    projects = projects_response.json()
    
    project_data = None
    
    # Check if response is a list
    if isinstance(projects, list):
        for p in projects:
            if isinstance(p, dict):
                if p.get("name") == project or p.get("id") == project:
                    project_data = p
                    break
            elif isinstance(p, str):
                # If it's just project names/IDs as strings
                if p == project:
                    # Need to get full project details
                    project_data = {"name": p, "id": p}
                    break
    elif isinstance(projects, dict) and "projects" in projects:
        # Handle paginated response
        for p in projects["projects"]:
            if p.get("name") == project or p.get("id") == project:
                project_data = p
                break
    
    if not project_data:
        raise click.ClickException(f"Project '{project}' not found in organization")
    
    return project_data


@click.command("use-project")
@click.argument("project")
@click.option("--insecure", "-k", is_flag=True, help="Skip SSL certificate verification")
def use_project(project: str, insecure: bool) -> None:
    """Set the current project context.
    
    This command verifies the project exists and saves it as your current context.
    Use 'dagctl config generate' to create the SQLMesh config.
    
    Examples:
    
      # Set project context
      dagctl use-project my-project -k
      
      # Then generate config
      dagctl config generate
    """
    config = DagctlConfig()
    
    # Check authentication
    if not config.is_authenticated():
        console.print("[red]Not authenticated.[/red]")
        console.print("Run: [cyan]dagctl auth login --org <org>[/cyan]")
        sys.exit(1)
    
    verify_ssl = not insecure
    
    if insecure:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    console.print()
    console.print(f"[bold]Setting project context: {project}[/bold]")
    console.print()
    console.print("  Verifying project exists...", end="")
    
    try:
        project_data = verify_project_exists(config, project, verify_ssl)
        console.print(" [green]✓[/green]")
    except click.ClickException as e:
        console.print(" [red]✗[/red]")
        console.print(f"[red]{e.message}[/red]")
        sys.exit(1)
    
    # Save project context
    config.set_current_project(project)
    if "id" in project_data:
        config.set_current_project_id(project_data["id"])
    
    console.print()
    console.print(f"[green]✓ Project set: [bold]{project}[/bold][/green]")
    console.print()
    console.print("Next step:")
    console.print("  [cyan]dagctl config generate[/cyan]")
    console.print()


@click.command("generate")
@click.option("--output", "-o", default="config.py", help="Output file (default: config.py)")
def config_generate(output: str) -> None:
    """Translate config.yaml to config.py with auto-refreshing state connection.
    
    Reads your existing config.yaml and converts it to a Python config.py
    that uses dagctl's get_state_connection() for auto-refreshing credentials.
    
    Examples:
    
      # Generate config.py
      dagctl config generate
      
      # Custom output file
      dagctl config generate --output my_config.py
    """
    config = DagctlConfig()
    
    # Check authentication
    if not config.is_authenticated():
        console.print("[red]Not authenticated.[/red]")
        console.print("Run: [cyan]dagctl auth login --org <org>[/cyan]")
        sys.exit(1)
    
    # Check project context
    project = config.get_current_project()
    if not project:
        console.print("[red]No project set.[/red]")
        console.print("Run: [cyan]dagctl use-project <project> -k[/cyan]")
        sys.exit(1)
    
    # Find config.yaml
    config_yaml_path = None
    for path in [Path("config.yaml"), Path("config.yml")]:
        if path.exists():
            config_yaml_path = path
            break
    
    if not config_yaml_path:
        console.print("[red]No config.yaml found in current directory.[/red]")
        sys.exit(1)
    
    # Read and parse config.yaml
    console.print()
    console.print(f"[bold]Translating {config_yaml_path} to Python[/bold]")
    console.print()
    
    try:
        with open(config_yaml_path, "r") as f:
            yaml_config = yaml.safe_load(f)
    except Exception as e:
        console.print(f"[red]Failed to parse {config_yaml_path}: {e}[/red]")
        sys.exit(1)
    
    # Convert to Python config
    org_name = config.get_current_org_name() or config.get_current_org()
    content = convert_yaml_to_python_config(yaml_config, org_name, project)
    
    # Write to file
    output_path = Path(output)
    with open(output_path, "w") as f:
        f.write(content)
    os.chmod(output_path, 0o600)
    
    console.print(f"  Converted config [green]✓[/green]")
    
    # Backup original config.yaml to avoid conflict
    backup_path = config_yaml_path.with_suffix(config_yaml_path.suffix + ".bak")
    config_yaml_path.rename(backup_path)
    console.print(f"  Backed up {config_yaml_path.name} → {backup_path.name} [green]✓[/green]")
    
    console.print()
    console.print(f"[green]✓ Generated: {output}[/green]")
    console.print(f"[green]✓ Original backed up: {backup_path.name}[/green]")
    console.print()
    console.print("Use this config with SQLMesh:")
    console.print(f"  [cyan]sqlmesh plan[/cyan]")
    console.print()


@click.command("current")
def config_current() -> None:
    """Show current organization and project context."""
    config = DagctlConfig()
    
    context = config.get_context_summary()
    
    console.print()
    console.print("[bold]Current Context[/bold]")
    console.print()
    
    if not context["authenticated"]:
        console.print("  [red]Not authenticated[/red]")
        console.print()
        console.print("  Run: [cyan]dagctl auth login --org <org>[/cyan]")
        return
    
    console.print(f"  Organization: [bold]{context['organization'] or 'not set'}[/bold]")
    console.print(f"  Project: [bold]{context['project'] or 'not set'}[/bold]")
    
    if context["credentials_expire"]:
        console.print(f"  Credentials expire: {context['credentials_expire']}")
    
    console.print(f"  API URL: {context['api_url']}")
    console.print(f"  PG Proxy: {config.get_pg_proxy_host()}:{config.get_pg_proxy_port()}")
    console.print()
