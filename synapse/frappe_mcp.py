# Copyright (c) 2026, Dxbitz and contributors
"""Synapse on Frappe's own MCP server.

Frappe 16.53 and later ships an MCP server at /api/v2/mcp. Synapse now points
users there. Frappe's server has a `call_method` tool that runs any whitelisted
method, so the dashboard tools below are plain whitelisted methods.

Access here is plain Frappe permissions. Synapse Profiles, the Synapse Settings
switches and the backstop belong to the old Synapse endpoint and do not apply.
Calls are still written to the Synapse Log.
"""

import importlib.util
import json
from contextlib import contextmanager

import frappe

ENDPOINT_PATH = "/api/v2/mcp"
METHOD_PREFIX = "synapse.frappe_mcp."
PAGE = "Synapse Page"

# Added once to System Settings > Agent Instructions, so agents know Synapse is here.
AGENT_NOTE_MARKER = "Synapse dashboards:"
AGENT_NOTE = (
	"Synapse dashboards: before building, changing or refreshing a dashboard in the Synapse app, "
	"call_method synapse.frappe_mcp.get_dashboard_guide and follow it."
)

# The guide was written for the old Synapse tools. This maps them to what to call here.
TOOL_MAP = {
	"describe_doctype": "get_doctype_schema",
	"get_list / list_docs": "list_documents",
	"create_doc": "create_document",
	"aggregate": f"call_method {METHOD_PREFIX}aggregate",
	"get_dashboard_guide": f"call_method {METHOD_PREFIX}get_dashboard_guide",
	"list_dashboards": f"call_method {METHOD_PREFIX}list_dashboards",
	"get_dashboard": f"call_method {METHOD_PREFIX}get_dashboard",
	"preview_dashboard_data": f"call_method {METHOD_PREFIX}preview_dashboard_data",
	"save_dashboard": f"call_method {METHOD_PREFIX}save_dashboard",
	"publish_dashboard_snapshot": f"call_method {METHOD_PREFIX}publish_dashboard_snapshot",
}


def available() -> bool:
	"""True when this Frappe has the built-in MCP server and it is switched on."""

	if importlib.util.find_spec("frappe.mcp") is None:
		return False
	try:
		return bool(frappe.get_system_settings("enable_mcp"))
	except Exception:
		return False


def endpoint_url() -> str:
	return frappe.utils.get_url(ENDPOINT_PATH)


@contextmanager
def _frappe_permissions():
	"""Run a Synapse tool body with Frappe permissions as the only limit.

	The tool bodies check a Synapse policy first. Here that policy grants
	everything, so Frappe's own checks (get_list, check_permission, has_permission)
	decide. Built-in control-plane blocks in the policy still apply.
	"""

	from synapse.mcp_tools import settings
	from synapse.mcp_tools.policy import Policy

	can_save = bool(frappe.has_permission(PAGE, "write") or frappe.has_permission(PAGE, "create"))
	policy = Policy(
		enabled=True,
		read_enabled=True,
		write_enabled=True,
		dashboard_tools_on=can_save,
		full_access=True,
	)
	previous = getattr(frappe.local, settings.CACHE_KEY, None)
	setattr(frappe.local, settings.CACHE_KEY, policy)
	try:
		yield
	finally:
		if previous is None:
			settings.clear_cache()
		else:
			setattr(frappe.local, settings.CACHE_KEY, previous)


def _run(fn, **kwargs):
	frappe.only_for("Desk User")
	with _frappe_permissions():
		return fn(**kwargs)


def _json(value):
	"""Accept a JSON string as well as an object, for plain HTTP callers."""

	if isinstance(value, str) and value.strip()[:1] in ("{", "["):
		return json.loads(value)
	return value


@frappe.whitelist()
def get_dashboard_guide():
	"""Read this first, before building, changing or refreshing any Synapse dashboard."""

	from synapse.mcp_tools import dashboards

	result = _run(dashboards.get_dashboard_guide)
	access = result.get("your_access") or {}
	if not access.get("save_dashboards"):
		access["tell_the_user"] = (
			"I can read your data but cannot save dashboards. You need write access to Synapse Page "
			"in Frappe. Ask a System Manager."
		)
		access["do_not"] = "Do not create the Synapse Page with create_document instead."
	result["on_frappe_mcp"] = {
		"note": "You are on Frappe's MCP server. Where this guide names a tool, call the one listed here.",
		"tools": TOOL_MAP,
	}
	return result


@frappe.whitelist()
def list_dashboards(only_due=False):
	from synapse.mcp_tools import dashboards

	return _run(dashboards.list_dashboards, only_due=frappe.utils.sbool(only_due))


@frappe.whitelist()
def get_dashboard(page):
	from synapse.mcp_tools import dashboards

	return _run(dashboards.get_dashboard, page=page)


@frappe.whitelist()
def preview_dashboard_data(page, filters=None):
	from synapse.mcp_tools import dashboards

	return _run(dashboards.preview_dashboard_data, page=page, filters=_json(filters))


@frappe.whitelist(methods=["POST"])
def save_dashboard(
	page,
	layout,
	title=None,
	data_source=None,
	data_script=None,
	view=None,
	group=None,
	subtitle=None,
	description=None,
	keywords=None,
	brief=None,
	refresh_every=None,
	enabled=None,
	validate_only=False,
):
	"""Create a dashboard, or replace one, in a single call. Read get_dashboard_guide first."""

	from synapse.mcp_tools import dashboards

	return _run(
		dashboards.save_dashboard,
		page=page,
		layout=_json(layout),
		title=title,
		data_source=data_source,
		data_script=data_script,
		view=view,
		group=group,
		subtitle=subtitle,
		description=description,
		keywords=keywords,
		brief=brief,
		refresh_every=refresh_every,
		enabled=None if enabled is None else frappe.utils.sbool(enabled),
		validate_only=frappe.utils.sbool(validate_only),
	)


@frappe.whitelist(methods=["POST"])
def publish_dashboard_snapshot(page, data, notes=None):
	from synapse.mcp_tools import dashboards

	return _run(dashboards.publish_dashboard_snapshot, page=page, data=_json(data), notes=notes)


@frappe.whitelist()
def aggregate(doctype, metrics=None, group_by=None, period=None, filters=None, order_by=None, limit=None):
	"""Count, sum, average, min or max over a DocType, grouped if you like."""

	from synapse.mcp_tools import aggregate as tool

	return _run(
		tool.aggregate,
		doctype=doctype,
		metrics=_json(metrics),
		group_by=_json(group_by),
		period=_json(period),
		filters=_json(filters),
		order_by=order_by,
		limit=frappe.utils.cint(limit) if limit not in (None, "") else None,
	)


def add_agent_note():
	"""Tell agents on Frappe's MCP that Synapse dashboards exist. Runs once, at install."""

	if importlib.util.find_spec("frappe.mcp") is None:
		return
	meta = frappe.get_meta("System Settings")
	if not meta.has_field("agent_instructions"):
		return
	current = frappe.db.get_single_value("System Settings", "agent_instructions") or ""
	if AGENT_NOTE_MARKER in current:
		return
	value = (current.rstrip() + "\n\n" + AGENT_NOTE).strip()
	frappe.db.set_single_value("System Settings", "agent_instructions", value)
