# Copyright (c) 2026, Dxbitz and contributors
"""Endpoints for the Synapse app at /synapse (explorer and dashboard views)."""

import frappe
from frappe import _

from synapse import dashboards


def _desk_user():
	frappe.only_for("Desk User")


@frappe.whitelist()
def list_dashboards() -> list[dict]:
	"""Explorer items: every enabled Synapse UI page the caller can read."""
	_desk_user()
	if not frappe.has_permission(dashboards.PAGE, "read"):
		return []
	rows = frappe.get_list(
		dashboards.PAGE,
		filters={"enabled": 1, "layout": ["is", "set"]},
		fields=[
			"name",
			"title",
			"page_group",
			"description",
			"keywords",
			"view_type",
			"data_mode",
			"llm_updated_on",
			"modified",
		],
		order_by="page_group asc, title asc",
		limit_page_length=0,
	)
	return [
		{
			"id": r.name,
			"title": r.title,
			"group": r.page_group or _("Dashboards"),
			"description": r.description,
			"keywords": " ".join(
				filter(None, [r.keywords, "assistant" if r.data_mode == "Assistant" else ""])
			),
			"type": "report" if r.view_type == "Report" else "dashboard",
			"data_mode": r.data_mode or "Script",
			"updated_on": str(r.llm_updated_on or r.modified),
		}
		for r in rows
	]


@frappe.whitelist()
def get_dashboard(name: str) -> dict:
	"""The SynapseUI config for one dashboard, with the caller's saved filters as defaults."""
	_desk_user()
	return dashboards.config_for(dashboards.readable_page(name))


@frappe.whitelist()
def get_dashboard_data(name: str, filters=None):
	"""One call per load: a dict keyed by widget key (dashboard) or a table payload (report)."""
	_desk_user()
	return dashboards.data_for(dashboards.readable_page(name), filters)


@frappe.whitelist()
def request_dashboard_data(name: str, filters=None, refresh=0) -> dict:
	"""Script dashboards: stored data, or a queued run and a ticket to check with dashboard_load_status."""
	_desk_user()
	from synapse import queued_loads

	doc = dashboards.readable_page(name)
	if not dashboards.is_script(doc):
		return {"status": "ready", "data": dashboards.data_for(doc, filters)}
	return queued_loads.request(doc, filters, refresh=frappe.utils.cint(refresh))


@frappe.whitelist()
def dashboard_load_status(name: str, ticket: str) -> dict:
	_desk_user()
	from synapse import queued_loads

	return queued_loads.status(dashboards.readable_page(name), ticket)


@frappe.whitelist(methods=["POST"])
def save_dashboard_filters(name: str, filters=None) -> dict:
	_desk_user()
	return dashboards.save_filters(dashboards.readable_page(name), filters or {})


@frappe.whitelist(methods=["POST"])
def reset_dashboard_filters(name: str) -> None:
	_desk_user()
	dashboards.forget_filters(dashboards.readable_page(name).name)
