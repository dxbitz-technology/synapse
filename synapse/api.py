# Copyright (c) 2026, Dxbitz and contributors
"""Desk-facing helpers for the Synapse console page and the user shortcut."""

import frappe

ENDPOINT_PATH = "/api/method/synapse.mcp.handle_mcp"
ADMIN_ROLE = "System Manager"


def endpoint_url() -> str:
	"""The absolute MCP endpoint URL for this site."""

	return frappe.utils.get_url(ENDPOINT_PATH)


def user_is_covered(user: str | None = None) -> bool:
	"""True if any of the user's roles is listed on an enabled Synapse Profile."""

	user = user or frappe.session.user
	if not user or user == "Guest":
		return False

	roles = set(frappe.get_roles(user))
	if not roles:
		return False

	enabled = frappe.get_all("Synapse Profile", filters={"enabled": 1}, pluck="name", ignore_permissions=True)
	if not enabled:
		return False

	profile_roles = frappe.get_all(
		"Synapse Profile Role",
		filters={"parenttype": "Synapse Profile", "parent": ["in", enabled]},
		pluck="role",
		ignore_permissions=True,
	)
	return bool(roles & set(profile_roles))


def has_admin_permission() -> bool:
	"""Gate for the Synapse tile on the /apps screen, System Manager only."""

	return ADMIN_ROLE in frappe.get_roles()


@frappe.whitelist()
def connect_context() -> dict:
	"""What the connect shortcut and the console need to render.

	Available to any signed-in user. `covered` decides whether the user shortcut
	shows at all; `is_admin` unlocks the console actions.
	"""

	return {
		"endpoint": endpoint_url(),
		"covered": user_is_covered(),
		"is_admin": ADMIN_ROLE in frappe.get_roles(),
	}


def has_desk_permission() -> bool:
	return frappe.session.user != "Guest" and "Desk User" in frappe.get_roles()


@frappe.whitelist()
def list_dashboard_pages():
	"""List only enabled pages the caller can read, including explicit shares."""
	frappe.only_for("Desk User")
	if not frappe.has_permission("Synapse Page", "read"):
		return []
	return frappe.get_list(
		"Synapse Page",
		filters={"enabled": 1},
		fields=["name", "title", "modified"],
		order_by="modified desc",
		limit_page_length=0,
	)


@frappe.whitelist()
def get_component_catalog():
	frappe.only_for("Desk User")
	from synapse.components.contracts import component_contracts

	return component_contracts()


def _page(name):
	doc = frappe.get_doc("Synapse Page", name)
	doc.check_permission("read")
	if not doc.enabled:
		frappe.throw(frappe._("This page is disabled."), frappe.PermissionError)
	return doc


def _block_model(block, include_data=True):
	from synapse.components.contracts import json_object, validate_component
	from synapse.scripts import parameters, run_script

	live = bool(block.get("data_script"))
	data, error = {}, None
	try:
		config = json_object(block.config)
		validate_component(block.component_type, config)
		if not live or include_data:
			data = (
				run_script(block.data_script, parameters(block.script_parameters))
				if live
				else json_object(block.frozen_data)
			)
			validate_component(block.component_type, config, data)
	except Exception:
		config, data = {}, {}
		error = frappe._("Could not load this block. Check its data, configuration and your access.")
	return {
		"name": block.get("name"),
		"component_type": block.component_type,
		"columns": block.columns or 12,
		"config": config,
		"frozen_data": data,
		"data_error": error,
		"live": live,
		"pending": live and not include_data and not error,
	}


@frappe.whitelist()
def get_page_layout(name: str, include_data=True) -> dict:
	"""Return a permission-checked page. Deferred data loads isolate slow blocks."""
	from frappe.utils import cint

	doc = _page(name)
	return {
		"name": doc.name,
		"title": doc.title,
		"enabled": bool(doc.enabled),
		"can_edit": bool(frappe.has_permission("Synapse Page", "write", doc=doc)),
		"blocks": [_block_model(block, bool(cint(include_data))) for block in doc.get("blocks") or []],
	}


@frappe.whitelist()
def get_page_block_data(name: str, block_name: str):
	"""Never accept a client-supplied script or parameters as a saved page block."""
	doc = _page(name)
	block = next((row for row in doc.get("blocks") or [] if row.name == block_name), None)
	if not block:
		frappe.throw(frappe._("Block not found."), frappe.DoesNotExistError)
	return _block_model(block)


@frappe.whitelist()
def preview_component(
	component_type: str,
	config=None,
	frozen_data=None,
	data_script=None,
	script_parameters=None,
	validate_only=False,
):
	"""Preview with exactly the runtime and contracts used by saved dashboards."""
	frappe.only_for("Desk User")
	from synapse.components.contracts import json_object, validate_component
	from synapse.scripts import parameters, run_script

	config = json_object(config)
	definition = validate_component(component_type, config)
	if data_script and definition.get("is_layout"):
		frappe.throw(frappe._("Layout blocks cannot use a data script."))
	if data_script:
		script = frappe.get_doc("Synapse Script", data_script)
		script.check_permission("read")
		if not script.enabled:
			frappe.throw(frappe._("The data script is disabled."))
		parameters(script_parameters)
		from frappe.utils import cint

		if cint(validate_only):
			return {"component_type": component_type, "config": config, "validated": True}
	data = run_script(data_script, parameters(script_parameters)) if data_script else json_object(frozen_data)
	validate_component(component_type, config, data)
	return {"component_type": component_type, "config": config, "data": data}


@frappe.whitelist()
def readiness_report() -> str:
	"""The text of `check.report`, for the console's Health Check action.

	System Manager only, it reveals the site's whole Synapse configuration.
	"""

	frappe.only_for(ADMIN_ROLE)

	from synapse.mcp_tools import check

	return check.report_text()
