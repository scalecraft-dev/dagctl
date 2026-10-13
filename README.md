# dagctl

The command-line client for [dagctl](https://dagctl.io), a hosted platform that runs SQLMesh and dbt projects in production. dagctl keeps your project's SQLMesh state, runs your models on a schedule, holds deployments for approval on the environments you protect, and alerts you in Slack when something breaks. When a run fails, its remediation agent diagnoses the problem and opens a pull request with a fix. Your project stays a standard open-source SQLMesh project.

This package is for SQLMesh projects. It signs you in to your dagctl organization and hands SQLMesh a connection to your project's hosted state, so `sqlmesh plan` and `sqlmesh run` on a laptop see the same state as production. There is nothing to run locally and no state-database credentials to manage.

- Product: <https://dagctl.io>
- Documentation: <https://docs.dagctl.io>
- Pricing: <https://dagctl.io/#pricing>
- Support: <support@scalecraft.dev>

## What it does

- Signs you in to a dagctl organization from the browser and keeps the session fresh.
- Sets which project you are working in.
- Gives SQLMesh the state connection for that project through `get_state_connection()`, so your `config.py` carries no state-database credentials.
- Converts an existing `config.yaml` into a `config.py` wired to dagctl.

## Requirements

- Python 3.9 or newer
- A dagctl organization. If you do not have one, start a 14-day free trial at <https://dagctl.io>.

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

`dagctl config generate` needs a `config.yaml` (or `config.yml`) in the project directory. It writes `config.py` and keeps the original with a `.bak` suffix. Use `dagctl auth status` and `dagctl config current` to see who you are signed in as and which project is selected.

## The dagctl platform

- **Semantic layer for agents:** expose a SQLMesh project's models and definitions as an MCP server. Your analysts point Claude or any MCP client at it and query governed data through dagctl, without warehouse credentials of their own.
- **Automatic fixes:** when a run fails, dagctl diagnoses it and opens a pull request with a proposed fix.
- **Change control:** plan review and approval on the environments you protect. Approval on a protected environment is limited to the named users, API tokens, or roles you list.
- **Scheduling and state:** hosted SQLMesh state, scheduled runs, run history, and logs.
- **Alerts:** plan and run alerts to Slack.
- **Enterprise access control:** single sign-on over SAML or OIDC through your identity provider, on the Team plan and above, configured for you by our team. Users who sign in through your SSO connection are added to your organization automatically with the Reader role. Owner, Admin, Developer, Reader, and Analyst roles and API tokens are on every plan. Owners and admins can view an audit log of configuration changes (protections, members, tokens, variables, and integrations).
- **dbt:** dbt projects run on the same platform and are managed from the web app. This CLI is for SQLMesh.
- **Set up from your AI assistant:** connect Claude or any MCP client to dagctl and go from sign-up to a first run without leaving the chat.
- **Pricing:** one flat monthly price per organization, set by how many models you run. Every user and every run is included. Self-serve plans start with a 14-day free trial, no credit card required. Current plans and prices: <https://dagctl.io/#pricing>.

## How it works

SQLMesh keeps track of what has run and what changed in a state database. dagctl hosts that database for your project. When SQLMesh starts, it calls `get_state_connection()` from this package, which:

1. Reads your sign-in from `~/.dagctl/`
2. Refreshes the session if it has expired
3. Returns the connection details SQLMesh expects

The connection authenticates with a short-lived access token in place of a database password. A refresh token, stored in `~/.dagctl/` and readable only by you, keeps the session fresh. `dagctl auth logout` removes it.

If a project environment is protected, `get_state_connection()` refuses to connect when SQLMesh targets that environment from your machine unless you are one of its approved users. Deploy to protected environments through dagctl so the change goes through approval.

## Documentation

- [Usage](https://github.com/scalecraft-dev/dagctl/blob/main/docs/usage.md): signing in, choosing a project, generating the SQLMesh config, the command reference, the files in `~/.dagctl/`, and troubleshooting.
- [API reference](https://github.com/scalecraft-dev/dagctl/blob/main/docs/api-reference.md): `get_state_connection()`, `get_fresh_token()`, and how authentication to the hosted state database works.
- [docs.dagctl.io](https://docs.dagctl.io): the dagctl platform documentation.

## License

[Apache-2.0](https://github.com/scalecraft-dev/dagctl/blob/main/LICENSE)
