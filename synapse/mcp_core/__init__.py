# Copyright (c) 2026, Dxbitz and contributors
"""A small, dependency-free MCP (Model Context Protocol) server for Frappe apps.

Vendored instead of `pip install frappe-mcp` for two reasons: frappe-mcp pins
deps that clash with Frappe 16 and would make `bench update` unsafe, and it has
no per-tool authorization. Both are handled here, so a plain `bench install-app`
is the whole install and nothing runs on the request path but stdlib.

Adapted from frappe/frappe-mcp (MIT): JSON-RPC over one Streamable HTTP POST,
with initialize, ping, tools/list, tools/call and the notification sink. Prompts,
resources, completion and SSE are not implemented.
"""

from synapse.mcp_core.server import MCP, ToolAnnotations

__all__ = ["MCP", "ToolAnnotations"]
