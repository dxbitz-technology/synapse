# Version tracks the Frappe major it targets (16.x), the Frappe app convention.
# version-16 is stable, develop is nightly (16.0.0-dev).
__version__ = "16.0.0"

# Public API for other apps that add custom tools. See synapse/extend.py.
from synapse.extend import tool

__all__ = ["tool"]
