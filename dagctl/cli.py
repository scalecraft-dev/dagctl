"""Main CLI for dagctl - local development authentication for SQLMesh."""

import click

from . import __version__
from .auth_commands import auth
from .project_commands import use_project, config_current, config_generate


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """dagctl - Authenticate and configure SQLMesh for local development.
    
    Connect your local SQLMesh projects to dagctl-managed state databases.
    
    \b
    Getting started:
        dagctl auth login --org your-org    # Authenticate
        dagctl use-project your-project     # Set project context
        source .env                         # Load credentials
        sqlmesh plan                        # Run SQLMesh
    """
    pass


# Register auth command group
cli.add_command(auth)

# Register project commands
cli.add_command(use_project)


@cli.group()
def config() -> None:
    """View and manage configuration."""
    pass


config.add_command(config_generate, name="generate")
config.add_command(config_current, name="current")


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
