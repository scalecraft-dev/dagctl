"""dagctl - command-line client for the dagctl hosted SQLMesh platform."""

__version__ = "0.4.0"

# Export SQLMesh integration function
from .state import get_state_connection, get_fresh_token
from .protection import check_environment_protection

__all__ = ["get_state_connection", "get_fresh_token", "check_environment_protection", "__version__"]
