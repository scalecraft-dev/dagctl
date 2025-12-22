# dagctl

CLI tool for managing SQLMesh projects with dagctl-hosted state databases.

## Features

- 🔐 **Secure Authentication** - OAuth-based authentication with JWT tokens
- 🔄 **Auto-Refresh** - JWT tokens automatically refresh when expired
- 🚀 **Zero Config** - SQLMesh state connection configured automatically
- 🏢 **Multi-Org** - Support for multiple organizations and projects
- 🔒 **Secure** - No long-lived credentials, JWT-based database authentication

## Installation

```bash
pip install dagctl
```

## Quick Start

```bash
# 1. Authenticate
dagctl auth login --org your-org

# 2. Set project context
dagctl use-project my-project

# 3. Run SQLMesh
cd my-sqlmesh-project
sqlmesh plan
```

## How It Works

dagctl provides a Python function `get_state_connection()` that SQLMesh calls to get state database credentials. This function:

1. Reads your authentication from `~/.dagctl/`
2. Automatically refreshes JWT tokens if expired
3. Returns PostgreSQL connection details for the dagctl-hosted state database
4. Uses JWT tokens for passwordless authentication via pg-proxy

## Usage

### 1. Authentication

Authenticate to your dagctl organization via browser:

```bash
dagctl auth login --org acme

# Output:
# dagctl Authentication
# 
#   Opening browser for authentication...
#   Listening on http://localhost:8080
# 
#   Waiting for authentication... ✓
#   Exchanging code for tokens... ✓
#   Verifying organization membership... ✓
#   Fetching environment configuration... ✓
# 
# ✓ Authenticated as user@company.com
# ✓ Organization: acme (ID: 4710a6f2-dbcf-4966-9427-b91784327d2d)
# 
# Next step: dagctl use-project <project-name>
```

For development environments with self-signed certificates:

```bash
dagctl auth login --org acme --api-url https://api.dagctl.internal -k
```

### 2. Set Project Context

Tell dagctl which project you're working on:

```bash
dagctl use-project my-project

# Output:
# Setting project context: my-project
# 
#   Verifying project exists... ✓
# 
# ✓ Project set: my-project
# 
# Next step:
#   dagctl config generate
```

For development:

```bash
dagctl use-project snowflake -k
```

### 3. Generate SQLMesh Config

If you have a `config.yaml`, generate a Python config:

```bash
dagctl config generate
```

This converts your `config.yaml` to `config.py` with automatic state connection:

**Before (config.yaml):**

```yaml
gateways:
  snowflake:
    connection:
      type: snowflake
      account: abc123.us-east-1
      user: "${SNOWFLAKE_USER}"
      password: "${SNOWFLAKE_PASSWORD}"
```

**After (config.py):**

```python
from dagctl import get_state_connection
from sqlmesh.core.config import Config

gateways = {
    "snowflake": {
        "connection": {
            "type": "snowflake",
            "account": os.environ.get("SNOWFLAKE_ACCOUNT"),
            "user": os.environ.get("SNOWFLAKE_USER"),
            # ...
        },
        "state_connection": get_state_connection(),  # ← Auto-configured!
    },
}

config = Config(
    gateways=gateways,
    default_gateway="snowflake",
)
```

### 4. Use SQLMesh

Just run SQLMesh normally! The state connection is handled automatically:

```bash
sqlmesh plan
sqlmesh run
sqlmesh fetchdf "SELECT * FROM my_model"
```

## Manual Config (No config.yaml)

If you don't have a `config.yaml`, create `config.py` manually:

```python
"""SQLMesh configuration with dagctl state connection."""

import os
from dagctl import get_state_connection
from sqlmesh.core.config import Config

gateways = {
    "my_gateway": {
        "connection": {
            "type": "snowflake",
            "account": os.environ.get("SNOWFLAKE_ACCOUNT"),
            "user": os.environ.get("SNOWFLAKE_USER"),
            "authenticator": "snowflake_jwt",
            "private_key_path": os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH"),
            "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE"),
            "database": os.environ.get("SNOWFLAKE_DATABASE"),
            "role": os.environ.get("SNOWFLAKE_ROLE"),
        },
        "state_connection": get_state_connection(),
    },
}

config = Config(
    gateways=gateways,
    default_gateway="my_gateway",
)
```

## Commands

### Authentication

```bash
# Login
dagctl auth login --org <organization>
dagctl auth login --org acme --api-url https://api.staging.dagctl.io

# Logout
dagctl auth logout

# Check status
dagctl auth status
```

### Project Management

```bash
# Set project
dagctl use-project <project-name>
dagctl use-project my-project -k  # Skip SSL verification (dev)

# Generate config
dagctl config generate

# View current context
dagctl config current
```

## API Reference

### `get_state_connection()`

Returns a dictionary with PostgreSQL connection configuration for SQLMesh.

```python
from dagctl import get_state_connection

# Returns:
# {
#     "type": "postgres",
#     "host": "pg-proxy.dev-us-1.dagctl.internal",
#     "port": 5432,
#     "database": "org_acme_myproject",
#     "user": "acme/myproject",
#     "password": "<jwt-token>"
# }
```

**Features:**

- ✅ Auto-refreshes JWT tokens when expired
- ✅ Uses current org/project from `~/.dagctl/config.yaml`
- ✅ Thread-safe and cached
- ✅ Works with SQLMesh's config system

**Parameters:**

- `gateway` (optional): Gateway name (uses current project if not specified)
- `insecure` (optional): Skip SSL verification for development

### `get_fresh_token()`

Get a fresh JWT access token, refreshing if necessary.

```python
from dagctl import get_fresh_token

token = get_fresh_token()
# Returns: "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## How Authentication Works

1. **Login Flow:**
   - `dagctl auth login` opens browser for OAuth
   - You authenticate with Auth0
   - dagctl receives JWT tokens (access_token, refresh_token, id_token)
   - Tokens stored in `~/.dagctl/auth.json` (0600 permissions)

2. **State Connection:**
   - SQLMesh calls `get_state_connection()`
   - dagctl checks if JWT is expired
   - If expired, automatically refreshes using refresh_token
   - Returns connection with JWT as password

3. **pg-proxy Authentication:**
   - Client connects to pg-proxy with JWT as password
   - pg-proxy validates JWT using Auth0 JWKS
   - If valid, pg-proxy fetches org credentials from management API
   - pg-proxy connects to CoreDB and proxies traffic

## Configuration Directory

dagctl stores configuration in `~/.dagctl/`:

```tree
~/.dagctl/
├── config.yaml      # Current org/project context
├── auth.json        # Auth tokens (0600 permissions)
└── credentials/     # Cached credentials (deprecated, not used)
```

## Security

- **JWT-Based Auth**: No passwords stored, only JWT tokens
- **Auto-Refresh**: Tokens automatically refresh when expired
- **Short-Lived**: Access tokens expire after 1 hour
- **Secure Storage**: All files in `~/.dagctl/` have 0600 permissions
- **No Shared Secrets**: Each user authenticates individually

## Development

For development with self-signed certificates:

```bash
# Login with SSL verification disabled
dagctl auth login --org acme -k

# Set project with SSL verification disabled  
dagctl use-project my-project -k
```

The `-k` flag is equivalent to `curl -k` and skips SSL certificate verification.

## Troubleshooting

### "Not authenticated"

```bash
dagctl auth login --org your-org
```

### "No project set"

```bash
dagctl use-project your-project
```

### "Authentication failed: invalid token"

Your token may have expired. Re-authenticate:

```bash
dagctl auth logout
dagctl auth login --org your-org
```

### "State backend connection failed"

Check that:

1. You're authenticated: `dagctl auth status`
2. Project is set: `dagctl config current`
3. pg-proxy is running and accessible

## License

Apache-2.0

## Support

- Documentation: https://docs.dagctl.io
- Email: support@scalecraft.dev
