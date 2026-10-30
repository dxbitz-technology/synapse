# Copyright (c) 2026, Dxbitz and contributors
"""Expose the same saved data functions to MCP clients and Desk."""

from synapse.mcp import mcp
from synapse.mcp_core import ToolAnnotations
from synapse.mcp_tools import audit, settings
from synapse.mcp_tools.policy import READ, check


@mcp.tool(
	annotations=ToolAnnotations(title="Run a Synapse data script", readOnlyHint=True),
	enabled=settings.read_tools_enabled,
)
@audit.audited(audit.READ)
def execute_synapse_script(name: str, args: dict | None = None):
	"""Run an enabled Synapse Script and return its current data.

	Args:
	        name: The saved Synapse Script name.
	        args: Optional script parameters as an object.
	"""
	from synapse.scripts import execute_script

	check(settings.get_policy(), READ, "Synapse Script")
	audit.current().target("Synapse Script", name)
	return {"data": execute_script(name, args)}


@mcp.tool(
	annotations=ToolAnnotations(title="Get dashboard component and script contracts", readOnlyHint=True),
	enabled=settings.read_tools_enabled,
)
@audit.audited(audit.READ)
def get_dashboard_contract(component_type: str | None = None):
	"""Read this before generating a Synapse dashboard or data script.

	Returns supported component schemas, valid examples, restricted Python templates,
	page/block fields and runtime rules. Use current DocType metadata for real fields.
	Never invent a renderer, config option or script helper.

	Args:
	        component_type: Optional catalog key to return one component.
	"""
	import frappe

	from synapse.components.contracts import component_contracts

	check(settings.get_policy(), READ, "Synapse Component")
	frappe.has_permission("Synapse Component", "read", throw=True)
	items = component_contracts()
	if component_type:
		items = [item for item in items if item["key"] == component_type]
		if not items:
			frappe.throw("Unknown dashboard component.")
	return {
		"components": items,
		"page_fields": {
			"title": "Display title",
			"page_name": "Lowercase slug",
			"enabled": 1,
			"blocks": "Ordered child rows",
		},
		"block_fields": [
			"component_type",
			"columns",
			"config",
			"frozen_data",
			"data_script",
			"script_parameters",
		],
		"rules": [
			"config, frozen_data and script_parameters are JSON object strings in saved child rows.",
			"columns is 1 through 12. section_break and spacer are full width; column_break starts a new row.",
			"Choose frozen_data for a labelled snapshot OR data_script for current data. Layout blocks cannot use scripts.",
			"Scripts read args and assign a dict to result. Templates are examples, never current business data.",
			"Available reads: frappe.get_list, frappe.get_count and frappe.session.user. These retain profile and Frappe permissions.",
			"query(sql, values) and frappe.db.sql require System Manager plus SQL grants. Use bound values. SQL bypasses record permissions.",
			"No imports, document writes, network access or other-script execution. Respect the bench server_script_enabled switch.",
			"Inspect real DocType fields before generating queries. Match labels/series lengths and pivot matrix dimensions.",
			"Create scripts with create_doc only when configuration writes and Synapse Script write grants are enabled; only System Managers can maintain scripts.",
			"Run validate_dashboard_component with the saved script before attaching it. Save pages with create_doc/update_doc using normal grants.",
			"Dashboard readers need a page share or read permission. Scripted blocks also need a script share/read permission and Synapse read grants for the script and source DocTypes.",
			"Frozen snapshots are visible to page readers; source-document permissions are not rechecked for frozen data.",
		],
	}


@mcp.tool(
	annotations=ToolAnnotations(title="Validate dashboard component data", readOnlyHint=True),
	enabled=settings.read_tools_enabled,
)
@audit.audited(audit.READ)
def validate_dashboard_component(
	component_type: str,
	config: dict,
	data: dict | None = None,
	data_script: str | None = None,
	args: dict | None = None,
):
	"""Validate generated data or execute a saved script with the dashboard's runtime.

	Args:
	        component_type: Supported catalog key.
	        config: Component options object.
	        data: Frozen data object, required unless data_script is supplied.
	        data_script: Optional saved script to execute with the caller's grants.
	        args: Optional parameters for the saved script.
	"""
	import frappe

	from synapse.components.contracts import validate_component
	from synapse.scripts import execute_script

	check(settings.get_policy(), READ, "Synapse Component")
	frappe.has_permission("Synapse Component", "read", throw=True)
	definition = validate_component(component_type, config)
	if data_script:
		if definition.get("is_layout"):
			frappe.throw("Layout blocks cannot use scripts.")
		check(settings.get_policy(), READ, "Synapse Script")
		audit.current().target("Synapse Script", data_script)
		data = execute_script(data_script, args)
	if data is None:
		frappe.throw("Provide data or a saved data_script.")
	validate_component(component_type, config, data)
	return {"valid": True, "data": data}
