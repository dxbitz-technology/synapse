# Copyright (c) 2026, Dxbitz and contributors
"""Frappe version differences Synapse has to know about.

Kept import-light on purpose: hooks.py imports it, and hooks are loaded in
every process, before a site or database is necessarily there.
"""

import frappe


def frappe_major_version() -> int:
	try:
		return int(str(frappe.__version__).split(".")[0])
	except (ValueError, AttributeError):
		return 0


def native_oauth_discovery() -> bool:
	"""True when Frappe itself serves the MCP OAuth discovery documents and
	dynamic client registration (Frappe v16+, switched on in OAuth Settings).

	False on v15, where synapse.oauth_compat serves them instead.
	"""

	return frappe_major_version() >= 16


def frappe_has_mcp() -> bool:
	"""True when Frappe ships its own MCP server (16.53 and later)."""

	import importlib.util

	return importlib.util.find_spec("frappe.mcp") is not None


def aggregate_field(function: str, field: str, alias: str | None = None, doctype: str | None = None):
	"""One aggregate column for frappe.get_list, in the form this Frappe takes.

	v16 refuses SQL function strings and wants {"SUM": "field", "as": "alias"}.
	v15 only takes strings, such as "sum(`grand_total`) as `alias`". The field is
	always a checked fieldname or "*", never user text.
	"""

	function = function.upper()
	if frappe_major_version() >= 16:
		column = {function: field}
		if alias:
			column["as"] = alias
		return column

	if field == "*":
		target = "*"
	elif doctype:
		target = f"`tab{doctype}`.`{field}`"
	else:
		target = f"`{field}`"
	column = f"{function.lower()}({target})"
	return f"{column} as `{alias}`" if alias else column
