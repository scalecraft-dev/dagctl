# dagctl

The command-line client for [dagctl](https://dagctl.io), a hosted service that runs SQLMesh projects in production. dagctl keeps your project's SQLMesh state, runs your models on a schedule, holds every change for approval before it goes live, and tells you when something breaks. One flat rate covers the whole team.

This package is the part that lives on your machine. It signs you in to your dagctl organization and hands SQLMesh a connection to your project's hosted state, so `sqlmesh plan` and `sqlmesh run` on a laptop see the same state as production. There is nothing to run locally and no database credentials to manage.

- Product: <https://dagctl.io>
- Documentation: <https://docs.dagctl.io>
- Support: <support@scalecraft.dev>

## What it does

- Signs you in to a dagctl organization from the browser and keeps the session fresh.
- Sets which project you are working in.
- Gives SQLMesh the state connection for that project through `get_state_connection()`, so your `config.py` carries no credentials.
- Converts an existing `config.yaml` into a `config.py` wired to dagctl.

## Requirements

- Python 3.9 or newer
- A dagctl organization. If you do not have one, request access at <https://dagctl.io>.

## Installation

```bash
pip install dagctl
```

## Quick start

```bash
# 1. Sign in to your organization
dagctl auth login --org your-org

# 2. Choose the project you are working in
dagctl use-project my-project

# 3. Point SQLMesh at dagctl (converts config.yaml to config.py)
cd my-sqlmesh-project
dagctl config generate

# 4. Use SQLMesh as usual
sqlmesh plan
```

## How it works

SQLMesh keeps track of what has run and what changed in a state database. dagctl hosts that database for your project. When SQLMesh starts, it calls `get_state_connection()` from this package, which:

1. Reads your sign-in from `~/.dagctl/`
2. Refreshes the session if it has expired
3. Returns the connection details SQLMesh expects

The connection uses a short-lived token in place of a password, so nothing long-lived is stored on your machine.

## Usage

### 1. Sign in

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
# ✓ Organization: acme
#
# Next step: dagctl use-project <project-name>
```

### 2. Choose a project

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

### 3. Generate the SQLMesh config

If you have a `config.yaml`, generate a Python config:

```bash
dagctl config generate
```

This converts your `config.yaml` to `config.py` with the state connection filled in:

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
        "state_connection": get_state_connection(),  # ← Filled in by dagctl
    },
}

config = Config(
    gateways=gateways,
    default_gateway="snowflake",
)
```

### 4. Use SQLMesh

Run SQLMesh normally. The state connection is handled for you:

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
#     "host": "<your dagctl state endpoint>",
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
   - You authenticate with your identity provider
   - dagctl receives JWT tokens (access_token, refresh_token, id_token)
   - Tokens stored in `~/.dagctl/auth.json` (0600 permissions)

2. **State Connection:**
   - SQLMesh calls `get_state_connection()`
   - dagctl checks if JWT is expired
   - If expired, automatically refreshes using refresh_token
   - Returns connection with JWT as password

3. **Database Proxy Authentication:**
   - Client connects to the dagctl database proxy with the JWT as the password
   - The dagctl database proxy validates the JWT
   - If valid, the proxy resolves your organization's credentials
   - The proxy connects to the state database and proxies traffic

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
3. Your network allows outbound connections to dagctl

## License

Apache-2.0

## Support

- Documentation: https://docs.dagctl.io
- Email: support@scalecraft.dev
