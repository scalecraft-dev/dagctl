"""State connection management for SQLMesh integration."""

import requests
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .dagctl_config import DagctlConfig


def get_state_connection(
    gateway: Optional[str] = None, 
    default_environment: Optional[str] = None,
    insecure: bool = False
) -> Dict[str, Any]:
    """Get state connection configuration for SQLMesh.
    
    This function fetches fresh credentials from dagctl, automatically refreshing
    the JWT token if it has expired. Also checks environment protection to ensure
    the user has access to the target environment.
    
    Args:
        gateway: Gateway name (optional, uses current project if not specified)
        default_environment: Default environment to use if not specified on command line.
                     This should match your SQLMesh config's default_target_environment.
        insecure: Skip SSL verification (for dev environments)
    
    Returns:
        Dictionary with PostgreSQL connection configuration
    
    Raises:
        RuntimeError: If not authenticated, no project is set, or environment is protected
    
    Example:
        ```python
        # In your SQLMesh config.py
        from dagctl import get_state_connection
        
        DEFAULT_ENVIRONMENT = f'dev_{getpass.getuser()}'
        
        gateways = {
            "snowflake": {
                "connection": {
                    # Your Snowflake config...
                },
                "state_connection": get_state_connection(
                    gateway="snowflake",
                    default_environment=DEFAULT_ENVIRONMENT
                ),
            }
        }
        ```
    """
    config = DagctlConfig()
    
    # Check authentication
    if not config.is_authenticated():
        raise RuntimeError(
            "Not authenticated. Run: dagctl auth login --org <org>"
        )
    
    # Check project context
    project = config.get_current_project()
    if not project:
        raise RuntimeError(
            "No project set. Run: dagctl use-project <project>"
        )
    
    # Check environment protection (will raise RuntimeError if not allowed)
    project_id = config.get_current_project_id()
    if project_id:
        from .protection import check_environment_protection
        
        # Check protection (will auto-parse from command line and fall back to default)
        check_environment_protection(
            default_environment=default_environment,
            project_id=project_id, 
            insecure=insecure
        )
    
    # Get fresh token (will auto-refresh if expired)
    access_token = get_fresh_token(config, insecure)
    
    # Compute credentials locally (no API call needed)
    credentials = _compute_state_credentials(config, project, access_token)
    
    # Return connection dict for SQLMesh
    return {
        "type": "postgres",
        "host": credentials["host"],
        "port": credentials["port"],
        "database": credentials["database"],
        "user": credentials["user"],
        "password": credentials["password"],
    }


def get_fresh_token(config: Optional[DagctlConfig] = None, insecure: bool = False) -> str:
    """Get a fresh JWT token, refreshing if necessary.
    
    Args:
        config: DagctlConfig instance (creates one if not provided)
        insecure: Skip SSL verification
    
    Returns:
        Fresh JWT access token (for pg-proxy authentication)
    
    Raises:
        RuntimeError: If authentication fails or token cannot be refreshed
    """
    if config is None:
        config = DagctlConfig()
    
    tokens = config.get_auth_tokens()
    if not tokens:
        raise RuntimeError("Not authenticated. Run: dagctl auth login --org <org>")
    
    # Check if token is expired
    expires_at = tokens.get("expires_at")
    if expires_at:
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            
            # Refresh if expired or expiring in next 5 minutes
            if now >= expiry or (expiry - now).total_seconds() < 300:
                refresh_token = tokens.get("refresh_token")
                if not refresh_token:
                    raise RuntimeError("Token expired and no refresh token available. Please re-authenticate.")
                
                # Refresh the token
                new_tokens = _refresh_auth_token(config, refresh_token, insecure)
                tokens = new_tokens
        except (ValueError, TypeError) as e:
            # If we can't parse the expiry, just try to use the existing token
            pass
    
    # Use access_token (has correct audience for pg-proxy), not id_token
    access_token = tokens.get("access_token")
    if not access_token:
        raise RuntimeError("No access token found. Please re-authenticate.")
    
    return access_token


def _refresh_auth_token(config: DagctlConfig, refresh_token: str, insecure: bool = False) -> Dict[str, Any]:
    """Refresh the Auth0 access token using a refresh token.
    
    Args:
        config: DagctlConfig instance
        refresh_token: Refresh token from Auth0
        insecure: Skip SSL verification
    
    Returns:
        New tokens dictionary
    
    Raises:
        RuntimeError: If token refresh fails
    """
    auth0_domain = config.get_auth0_domain()
    client_id = config.get_auth0_client_id()
    
    token_url = f"https://{auth0_domain}/oauth/token"
    
    verify_ssl = not insecure
    if insecure:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    try:
        response = requests.post(
            token_url,
            json={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "refresh_token": refresh_token,
            },
            verify=verify_ssl,
            timeout=10,
        )
        
        if response.status_code != 200:
            error = response.json().get("error_description", response.text)
            raise RuntimeError(f"Token refresh failed: {error}")
        
        new_tokens = response.json()
        
        # Calculate new expiry
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=new_tokens.get("expires_in", 86400))
        new_tokens["expires_at"] = expires_at.isoformat()
        
        # Preserve refresh token if not provided in response
        if "refresh_token" not in new_tokens:
            new_tokens["refresh_token"] = refresh_token
        
        # Save new tokens
        config.save_auth_tokens(new_tokens)
        
        return new_tokens
        
    except requests.RequestException as e:
        raise RuntimeError(f"Network error refreshing token: {e}")


def _compute_state_credentials(
    config: DagctlConfig,
    project: str,
    access_token: str,
) -> Dict[str, Any]:
    """Compute state credentials locally without API call.
    
    The JWT token from authentication IS the password for the pg-proxy.
    No need for a separate state-credentials API endpoint.
    
    Args:
        config: DagctlConfig instance
        project: Project name
        access_token: JWT access token (used as password)
    
    Returns:
        Credentials dictionary with host, port, database, user, password
    
    Raises:
        RuntimeError: If configuration is missing
    """
    org_name = config.get_current_org_name() or config.get_current_org()
    if not org_name:
        raise RuntimeError("Organization not set. Please re-authenticate.")
    
    # Get pg-proxy endpoint from config (or use defaults)
    pg_proxy_host = config.get_pg_proxy_host()
    pg_proxy_port = config.get_pg_proxy_port()
    
    # Sanitize names for database naming
    def sanitize(name: str) -> str:
        return name.lower().replace("-", "_").replace(" ", "_")
    
    # Build connection details
    return {
        "host": pg_proxy_host,
        "port": pg_proxy_port,
        "database": f"org_{sanitize(org_name)}_{sanitize(project)}",
        "user": f"{org_name}/{project}",
        "password": access_token,  # JWT token is the password
    }
