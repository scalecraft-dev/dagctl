# Usage

Step-by-step use of the dagctl CLI: signing in, choosing a project, generating the SQLMesh config, and the commands and files involved. Back to the [README](../README.md).

## Walkthrough

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

## Configuration Directory

dagctl stores configuration in `~/.dagctl/`:

```tree
~/.dagctl/
├── config.yaml      # Current org/project context
├── auth.json        # Auth tokens (0600 permissions)
└── credentials/     # Cached credentials (deprecated, not used)
```

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
