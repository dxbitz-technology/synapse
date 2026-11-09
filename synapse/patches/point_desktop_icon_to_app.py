# Copyright (c) 2026, Dxbitz and contributors
"""The Synapse desktop icon opens the dashboard app at /synapse, not the desk console."""

import frappe


def execute():
	if not frappe.db.table_exists("Desktop Icon"):
		return
	for name in frappe.get_all("Desktop Icon", filters={"app": "synapse", "icon_type": "App"}, pluck="name"):
		frappe.db.set_value("Desktop Icon", name, "link", "/synapse")
	frappe.cache.delete_key("desktop_icons")
