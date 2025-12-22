"""Environment protection checks for dagctl CLI."""

import sys
import requests
from typing import Optional

from .dagctl_config import DagctlConfig


def _parse_target_environment_from_argv() -> Optional[str]:
    """Parse the target environment from sys.argv for SQLMesh commands.
    
    Examples:
        sqlmesh plan dev → "dev"
        sqlmesh run prod → "prod"
        sqlmesh plan → None (will use default)
    """
    argv = sys.argv
    
    # Find commands that take environment as positional argument
    env_commands = ["plan", "run", "diff", "invalidate"]
    
    for i, arg in enumerate(argv):
        if arg in env_commands:
            # Check if next argument exists and isn't a flag
            if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                return argv[i + 1]
            break
    
    return None


def check_environment_protection(
    environment: Optional[str] = None,
    default_environment: Optional[str] = None,
    project_id: Optional[str] = None,
    insecure: bool = False,
) -> None:
    """
    Check if the current user can access the specified environment.
    
    Raises RuntimeError if the environment is protected and user is not excepted.
    
    Args:
        environment: Environment name (e.g., "prod"). If not provided, 
                     will attempt to parse from command line args or use default_environment.
        default_environment: Default environment to use if not specified on command line.
                     This should match your SQLMesh config's default_target_environment.
        project_id: Project ID. If not provided, uses current project from config.
        insecure: Skip SSL verification.
    
    Raises:
        RuntimeError: If environment is protected and user doesn't have access.
    
    Example:
        # In your SQLMesh config.py - check before loading config
        from dagctl import check_environment_protection
        
        # Check using current project
        check_environment_protection()
        
        # Or check a specific environment
        check_environment_protection(environment="prod")
        
        # Then define your gateways with custom state
        gateways = {
            "snowflake": {
                "connection": {...},
                "state_connection": {
                    "type": "postgres",
                    "host": "my-db.example.com",
                    ...
                },
            }
        }
    """
    config = DagctlConfig()
    
    if not config.is_authenticated():
        raise RuntimeError("Not authenticated. Run: dagctl auth login --org <org>")
    
    # Get project_id if not provided
    if not project_id:
        project_id = config.get_current_project_id()
        if not project_id:
            raise RuntimeError("No project set. Run: dagctl use-project <project>")
    
    api_url = config.get_api_url()
    access_token = config.get_access_token()
    org_id = config.get_current_org()
    
    if not access_token:
        raise RuntimeError("No access token found. Please re-authenticate.")
    
    if not org_id:
        raise RuntimeError("No organization ID found. Please re-authenticate.")
    
    # If environment not explicitly provided, try to parse from command line
    if not environment:
        environment = _parse_target_environment_from_argv()
    
    # If still no environment, use the default_environment
    if not environment and default_environment:
        environment = default_environment
    
    # Build request params
    params = {"project_id": project_id}
    if environment:
        params["environment"] = environment  # Override project's environment
    
    verify_ssl = not insecure
    if insecure:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    try:
        response = requests.get(
            f"{api_url}/api/v1/environment-protections/check",
            params=params,
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Organization-ID": org_id,
            },
            verify=verify_ssl,
            timeout=10,
        )
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("allowed", True):
                env_name = data.get("environment", environment or "unknown")
                raise RuntimeError(
                    f"🔒 Environment '{env_name}' is protected.\n"
                    f"You do not have permission to run commands against this environment.\n"
                    f"Contact your organization admin for access."
                )
        elif response.status_code == 403:
            data = response.json()
            message = data.get("message", "Access denied to protected environment")
            raise RuntimeError(message)
        elif response.status_code == 401:
            raise RuntimeError(
                "Authentication failed. Your token may have expired. "
                "Run: dagctl auth login --org <org>"
            )
        elif response.status_code == 404:
            # 404 means no protection configured - that's OK, allow through
            pass
        else:
            # Other HTTP errors should block execution (fail-closed)
            raise RuntimeError(
                f"Failed to check environment protection (HTTP {response.status_code}). "
                f"Cannot verify access to protected environment."
            )
            
    except requests.RequestException as e:
        # Network/SSL errors should BLOCK execution (fail-closed security)
        # If we can't verify protection status, we must deny access
        import sys
        error_msg = str(e)
        
        # Provide helpful message for SSL errors
        if "SSL" in error_msg or "certificate" in error_msg.lower():
            raise RuntimeError(
                f"🔒 Cannot verify environment protection due to SSL error.\n"
                f"For development environments with self-signed certificates, add insecure=True:\n"
                f"  state_connection = get_state_connection(insecure=True)\n\n"
                f"Error: {e}"
            )
        else:
            raise RuntimeError(
                f"🔒 Cannot verify environment protection due to network error.\n"
                f"Cannot proceed without verifying access.\n\n"
                f"Error: {e}"
            )
