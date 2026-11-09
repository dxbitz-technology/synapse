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


INSTRUCTIONS = """Synapse gives you access to this Frappe / ERPNext site as the signed-in user. Synapse Profiles decide which DocTypes and actions you may use, and Frappe permissions still apply.

- Call describe_doctype before reading or writing a DocType. Never guess field names.
- Prefer get_list and get_count with filters. Use run_sql_query only when they cannot answer, it is read only.
- Writes change real records. Confirm with the user before create, update, submit, cancel or delete. Use the child row tools for child tables.
- Dashboards: call get_dashboard_guide before building, changing or refreshing one. Users open them at /synapse#/<page>.
- A refused call says which rule stopped it. Tell the user, do not work around it."""

mcp = MCP(
	"synapse",
	version=getattr(synapse, "__version__", "1.0.0"),
	on_refusal=_record_refusal,
	external_tools=_external_tools,
	oauth_scopes=(),
	instructions=INSTRUCTIONS,
)


@mcp.register()
def handle_mcp():
	"""Entry point for MCP requests. Body is imports only."""

	import synapse.mcp_tools.dashboards
	import synapse.mcp_tools.documents
	import synapse.mcp_tools.scripts
	import synapse.mcp_tools.sql
