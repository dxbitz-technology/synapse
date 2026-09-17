__version__ = "16.0.0-dev"

# Public API for other apps that add custom tools. See synapse/extend.py.
from synapse.extend import tool

__all__ = ["tool"]
