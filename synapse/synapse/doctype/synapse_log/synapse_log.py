# Copyright (c) 2026, Dxbitz and contributors
"""Audit trail for the Synapse endpoint, one row per call, read or write."""

import frappe
from frappe.model.document import Document


class SynapseLog(Document):
	pass


def delete_old_logs():
	"""Daily. Drop rows past the retention window set in Synapse Settings."""

	from synapse.mcp_tools.settings import retention_days

	cutoff = frappe.utils.add_days(frappe.utils.nowdate(), -retention_days())
	frappe.db.delete("Synapse Log", {"creation": ("<", cutoff)})
	frappe.db.commit()  # nosemgrep
