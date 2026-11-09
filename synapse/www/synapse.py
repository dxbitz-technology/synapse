# Copyright (c) 2026, Dxbitz and contributors
"""Serve the Synapse dashboard app at /synapse, for signed-in desk users."""

import json

import frappe
from frappe import _

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=" + frappe.utils.quote(
			frappe.request.path if frappe.request else "/synapse"
		)
		raise frappe.Redirect

	if "Desk User" not in frappe.get_roles():
		frappe.throw(_("The Synapse app is for desk users."), frappe.PermissionError)

	context.no_cache = 1
	context.title = "Synapse"
	context.boot = json.dumps(boot(), default=str).replace("</", "<\\/")
	context.asset_version = _asset_version()
	return context


def _asset_version() -> int:
	"""Cache key for the plain files the page loads: the newest change time among them."""
	import os

	files = (("synapse-ui", "synapse-ui.js"), ("synapse-ui", "synapse-ui.css"), ("css", "synapse_app.css"))
	try:
		return max(int(os.path.getmtime(frappe.get_app_path("synapse", "public", *f))) for f in files)
	except OSError:
		return 1


def boot() -> dict:
	from frappe.apps import get_apps

	from synapse.api import ADMIN_ROLE, endpoint_url, user_is_covered

	user = frappe.get_cached_doc("User", frappe.session.user)
	defaults = frappe.defaults.get_defaults()
	apps = [a for a in get_apps() if a.get("name") != "synapse"]
	return {
		"user": user.name,
		"full_name": user.full_name or user.name,
		"user_image": user.user_image,
		"theme": user.desk_theme or "Light",
		"is_admin": ADMIN_ROLE in frappe.get_roles(),
		# The MCP link shows only to users an enabled Synapse Profile covers, like the user form shortcut.
		"mcp_endpoint": endpoint_url() if user_is_covered() else None,
		"csrf_token": frappe.sessions.get_csrf_token(),
		"site_name": frappe.local.site,
		"apps": [{"title": "Desk", "route": "/app", "logo": None, "name": "desk"}, *apps],
		"currency": defaults.get("currency") or "AED",
		"date_format": frappe.db.get_single_value("System Settings", "date_format") or "dd-mm-yyyy",
		"number_format": frappe.db.get_single_value("System Settings", "number_format") or "#,###.##",
	}
