"""Authentication commands for dagctl using Authorization Code with PKCE."""

import base64
import hashlib
import http.server
import os
import secrets
import sys
import threading
import urllib.parse
import webbrowser
from typing import Optional

import click
import requests
from rich.console import Console

from .dagctl_config import DagctlConfig

console = Console()

# Local callback server configuration
CALLBACK_PORT = 8080
CALLBACK_PATH = "/callback"


class PKCECallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler to receive OAuth callback."""
    
    authorization_code: Optional[str] = None
    error: Optional[str] = None
    
    def do_GET(self) -> None:
        """Handle GET request (OAuth callback)."""
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path == CALLBACK_PATH:
            params = urllib.parse.parse_qs(parsed.query)
            
            if "code" in params:
                PKCECallbackHandler.authorization_code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                    <html><body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1>&#10003; Authentication Successful</h1>
                    <p>You can close this window and return to the terminal.</p>
                    </body></html>
                """)
            elif "error" in params:
                PKCECallbackHandler.error = params.get("error_description", params["error"])[0]
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                error_msg = PKCECallbackHandler.error
                self.wfile.write(f"""
                    <html><body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1>&#10007; Authentication Failed</h1>
                    <p>{error_msg}</p>
                    <p>Please return to the terminal and try again.</p>
                    </body></html>
                """.encode())
            else:
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format: str, *args) -> None:
        """Suppress HTTP server logs."""
        pass


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code verifier and challenge."""
    # Generate code verifier (43-128 characters)
    code_verifier = secrets.token_urlsafe(64)[:128]
    
    # Generate code challenge (S256)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip("=")
    
    return code_verifier, code_challenge


def start_callback_server(timeout: int = 300) -> Optional[str]:
    """Start local server to receive OAuth callback.
    
    Returns the authorization code or None if timeout/error.
    """
    PKCECallbackHandler.authorization_code = None
    PKCECallbackHandler.error = None
    
    server = http.server.HTTPServer(("localhost", CALLBACK_PORT), PKCECallbackHandler)
    server.timeout = timeout
    
    # Handle one request
    server.handle_request()
    server.server_close()
    
    if PKCECallbackHandler.error:
        raise Exception(PKCECallbackHandler.error)
    
    return PKCECallbackHandler.authorization_code


@click.group()
def auth() -> None:
    """Manage authentication."""
    pass


@auth.command("login")
@click.option("--org", required=True, help="Organization name or ID")
@click.option("--api-url", default=None, help="API URL (default: https://api.dagctl.io)")
@click.option("--insecure", "-k", is_flag=True, help="Skip SSL certificate verification (for dev environments)")
def auth_login(org: str, api_url: Optional[str], insecure: bool) -> None:
    """Authenticate to an organization via browser.
    
    Opens your browser to complete authentication, then saves
    credentials for use with dagctl commands.
    
    Examples:
    
      dagctl auth login --org acme
      dagctl auth login --org acme --api-url https://api.staging.dagctl.io
    """
    config = DagctlConfig()
    
    # Set API URL if provided
    if api_url:
        config.set_api_url(api_url)
    
    api = config.get_api_url()
    auth0_domain = config.get_auth0_domain()
    client_id = config.get_auth0_client_id()
    
    console.print()
    console.print("[bold]dagctl Authentication[/bold]")
    console.print()
    
    try:
        # Generate PKCE pair
        code_verifier, code_challenge = generate_pkce_pair()
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Build authorization URL
        redirect_uri = f"http://localhost:{CALLBACK_PORT}{CALLBACK_PATH}"
        auth_params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": "openid profile email offline_access",
            "audience": api,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
        }
        auth_url = f"https://{auth0_domain}/authorize?" + urllib.parse.urlencode(auth_params)
        
        console.print(f"  Opening browser for authentication...")
        console.print(f"  [dim]Listening on http://localhost:{CALLBACK_PORT}[/dim]")
        console.print()
        
        # Open browser
        webbrowser.open(auth_url)
        
        console.print("  Waiting for authentication...", end="")
        
        # Start server and wait for callback
        try:
            authorization_code = start_callback_server(timeout=300)
        except Exception as e:
            console.print(" [red]✗[/red]")
            console.print(f"[red]Authentication failed: {e}[/red]")
            sys.exit(1)
        
        if not authorization_code:
            console.print(" [red]✗[/red]")
            console.print("[red]Authentication timed out. Please try again.[/red]")
            sys.exit(1)
        
        console.print(" [green]✓[/green]")
        
        # Exchange code for tokens
        console.print("  Exchanging code for tokens...", end="")
        
        token_url = f"https://{auth0_domain}/oauth/token"
        token_response = requests.post(token_url, json={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": authorization_code,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
        })
        
        if token_response.status_code != 200:
            console.print(" [red]✗[/red]")
            error = token_response.json().get("error_description", token_response.text)
            console.print(f"[red]Token exchange failed: {error}[/red]")
            sys.exit(1)
        
        tokens = token_response.json()
        console.print(" [green]✓[/green]")
        
        # Calculate expiry
        from datetime import datetime, timezone, timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens.get("expires_in", 86400))
        tokens["expires_at"] = expires_at.isoformat()
        
        # Save tokens
        config.save_auth_tokens(tokens)
        
        # Verify organization membership
        console.print("  Verifying organization membership...", end="")
        
        verify_ssl = not insecure
        
        if insecure:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Decode the ID token to get Auth0 ID (sub claim)
        id_token = tokens.get("id_token")
        if not id_token:
            console.print(f" [red]✗[/red]")
            console.print("[red]No ID token in response[/red]")
            sys.exit(1)
        
        # Decode JWT without verification (we already verified with Auth0)
        import json
        id_token_parts = id_token.split(".")
        if len(id_token_parts) != 3:
            console.print(f" [red]✗[/red]")
            console.print("[red]Invalid ID token format[/red]")
            sys.exit(1)
        
        # Decode payload (middle part)
        payload = id_token_parts[1]
        # Add padding if needed
        payload += "=" * (4 - len(payload) % 4)
        try:
            claims = json.loads(base64.urlsafe_b64decode(payload))
        except Exception as e:
            console.print(f" [red]✗[/red]")
            console.print(f"[red]Failed to decode ID token: {e}[/red]")
            sys.exit(1)
        
        auth0_id = claims.get("sub")
        user_email = claims.get("email", "unknown")
        
        # Get user's organization via onboarding status endpoint (no org header needed)
        status_response = requests.get(
            f"{api}/api/v1/onboarding/status",
            params={"auth0_id": auth0_id},
            verify=verify_ssl
        )
        
        if status_response.status_code != 200:
            console.print(f" [red]✗[/red]")
            console.print(f"[red]Failed to get user status (HTTP {status_response.status_code}): {status_response.text}[/red]")
            sys.exit(1)
        
        status_data = status_response.json()
        
        if not status_data.get("onboarded"):
            console.print(f" [red]✗[/red]")
            console.print("[red]User is not onboarded. Please complete onboarding at the web UI first.[/red]")
            sys.exit(1)
        
        user_org = status_data.get("organization", {})
        org_id = user_org.get("id")
        org_name = user_org.get("name")
        
        # Verify the user's org matches what they requested
        if org.lower() not in [org_name.lower() if org_name else "", org_id if org_id else ""]:
            console.print(f" [red]✗[/red]")
            console.print(f"[red]You don't have access to organization '{org}'[/red]")
            console.print(f"[dim]Your organization is: {org_name}[/dim]")
            sys.exit(1)
        
        config.set_current_org(org_id, org_name)
        console.print(f" [green]✓[/green]")
        
        # Fetch environment info (pg-proxy hostname)
        console.print("  Fetching environment configuration...", end="")
        try:
            env_response = requests.get(
                f"{api}/api/v1/env/info",
                headers={
                    "Authorization": f"Bearer {id_token}",
                    "X-Organization-ID": org_id
                },
                verify=verify_ssl
            )
            
            if env_response.status_code == 200:
                env_data = env_response.json()
                state_proxy = env_data.get("state_proxy", {})
                if state_proxy.get("host"):
                    config._config["pg_proxy_host"] = state_proxy["host"]
                    config._config["pg_proxy_port"] = state_proxy.get("port", 5432)
                    config._save_config()
                console.print(" [green]✓[/green]")
            else:
                console.print(" [yellow]⚠[/yellow]")
                console.print(f"[yellow]Could not fetch environment config (HTTP {env_response.status_code})[/yellow]")
        except Exception as e:
            console.print(" [yellow]⚠[/yellow]")
            console.print(f"[yellow]Could not fetch environment config: {e}[/yellow]")
        
        console.print()
        console.print(f"[green]✓ Authenticated as [bold]{user_email}[/bold][/green]")
        console.print(f"[green]✓ Organization: [bold]{org_name}[/bold] (ID: {org_id})[/green]")
        console.print()
        console.print("Next step: [cyan]dagctl use-project <project-name>[/cyan]")
            
    except requests.RequestException as e:
        console.print(f"[red]Network error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@auth.command("logout")
def auth_logout() -> None:
    """Clear authentication tokens and cached credentials."""
    config = DagctlConfig()
    
    config.clear_auth_tokens()
    config.clear_credentials()
    
    console.print("[green]✓ Logged out successfully[/green]")
    console.print("[dim]Cleared tokens and cached credentials[/dim]")


@auth.command("status")
def auth_status() -> None:
    """Show current authentication status."""
    config = DagctlConfig()
    
    context = config.get_context_summary()
    
    console.print()
    console.print("[bold]Authentication Status[/bold]")
    console.print()
    
    if context["authenticated"]:
        console.print(f"  [green]✓ Authenticated[/green]")
    else:
        console.print(f"  [red]✗ Not authenticated[/red]")
        console.print()
        console.print("  Run: [cyan]dagctl auth login --org <org>[/cyan]")
        return
    
    if context["organization"]:
        console.print(f"  Organization: [bold]{context['organization']}[/bold]")
    
    if context["project"]:
        console.print(f"  Project: [bold]{context['project']}[/bold]")
    else:
        console.print(f"  Project: [dim]not set[/dim]")
    
    if context["credentials_expire"]:
        console.print(f"  Credentials expire: {context['credentials_expire']}")
    
    console.print(f"  API URL: {context['api_url']}")
    console.print()
