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

## Documentation

- [Usage](docs/usage.md): signing in, choosing a project, generating the SQLMesh config, the command reference, the files in `~/.dagctl/`, and troubleshooting.
- [API reference](docs/api-reference.md): `get_state_connection()`, `get_fresh_token()`, and how authentication to the hosted state database works.
- [docs.dagctl.io](https://docs.dagctl.io): the dagctl platform documentation.

## License

[Apache-2.0](LICENSE)
