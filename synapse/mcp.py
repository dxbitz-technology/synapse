# Copyright (c) 2026, Dxbitz and contributors
"""The Synapse MCP endpoint."""

import synapse
from synapse.mcp_core import MCP


def _record_refusal(tool_name, reason, tool):
	"""Keep refused calls in the audit trail."""

	from synapse.mcp_tools import audit

	kind = getattr(getattr(tool, "fn", None), "_mcp_kind", None)
	audit.refused(tool_name, reason, kind)


def _external_tools():
	from synapse.extend import load_external_tools

	return load_external_tools()


mcp = MCP(
	"synapse",
	version=getattr(synapse, "__version__", "1.0.0"),
	on_refusal=_record_refusal,
	external_tools=_external_tools,
)


@mcp.register()
def handle_mcp():
	"""Entry point for MCP requests. Body is imports only."""

	import synapse.mcp_tools.documents
	import synapse.mcp_tools.sql
