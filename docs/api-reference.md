# API reference

The Python functions this package exposes, and how authentication to the hosted state database works. Back to the [README](../README.md).

## Functions

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

## Security

- **JWT-Based Auth**: No passwords stored, only JWT tokens
- **Auto-Refresh**: Tokens automatically refresh when expired
- **Short-Lived**: Access tokens expire after 1 hour
- **Secure Storage**: All files in `~/.dagctl/` have 0600 permissions
- **No Shared Secrets**: Each user authenticates individually
