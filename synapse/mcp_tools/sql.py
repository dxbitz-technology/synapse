# Copyright (c) 2026, Dxbitz and contributors
"""The read-only SQL tool, the escape hatch, not the front door."""

import frappe

from synapse.mcp import mcp
from synapse.mcp_core import ToolAnnotations
from synapse.mcp_tools import audit, connection, serialise, settings
from synapse.mcp_tools.guard import UnsafeQuery, validate_read_only
from synapse.mcp_tools.policy import Denied

TIMEOUT_SECONDS = 15


@mcp.tool(
	annotations=ToolAnnotations(title="Run read-only SQL", readOnlyHint=True),
	enabled=settings.sql_tool_enabled,
)
@audit.audited(audit.SQL)
def run_sql_query(query: str, limit: int | None = None):
	"""Run a read-only SQL SELECT query against the ERPNext/Frappe database.

	Args:
	        query: A single SELECT or WITH statement. No semicolons, no comments.
	        limit: Maximum rows to return. Clamped to the site's Synapse row limit."""

	entry = audit.current()
	entry.sql(query if isinstance(query, str) else str(query))

	try:
		normalised = validate_read_only(query, frappe.conf.get("mcp_sql_blocked_tables"))
		_check_frappe_layer(normalised)
	except UnsafeQuery as e:
		raise Denied(str(e)) from e

	applied_limit = settings.row_limit(limit)
	final_query = f"SELECT * FROM ({normalised}) AS synapse_result LIMIT {applied_limit + 1}"

	if connection.is_configured():
		columns, rows = _run_read_only(final_query, applied_limit)
	else:
		columns, rows = _run_fallback(final_query, applied_limit)

	truncated = False
	if len(rows) > applied_limit:
		rows = rows[:applied_limit]
		truncated = True

	rows = [serialise.to_client(dict(row), settings.output_formats()) for row in rows]
	entry.rows(len(rows))

	return {
		"row_count": len(rows),
		"truncated": truncated,
		"columns": columns,
		"rows": rows,
	}


def _run_read_only(query: str, limit: int):
	"""Run on the SELECT-only database user. The strong path."""

	with connection.read_only_cursor(TIMEOUT_SECONDS) as cursor:
		cursor.execute(query)
		columns = [d[0] for d in (cursor.description or [])]
		rows = list(cursor.fetchmany(limit + 1))

	return columns, rows


def _run_fallback(query: str, limit: int):
	"""Run on Frappe's own connection when no read-only user is configured."""

	try:
		frappe.db.sql("SET SESSION max_statement_time = %s", (float(TIMEOUT_SECONDS),))
		rows = frappe.db.sql(query, as_dict=True)  # nosemgrep
	finally:
		frappe.db.rollback()

	rows = list(rows or [])[: limit + 1]
	columns = list(rows[0].keys()) if rows else []
	return columns, rows


def _check_frappe_layer(query: str):
	"""Run Frappe's own read-only check as an extra layer, where it applies."""

	if query.lstrip("( \t\r\n").lower().startswith("with"):
		return

	try:
		from frappe.utils.safe_exec import check_safe_sql_query
	except ImportError:
		return

	if not check_safe_sql_query(query, throw=False):
		raise UnsafeQuery("Rule 'frappe': rejected by frappe's own read-only SQL check.")
