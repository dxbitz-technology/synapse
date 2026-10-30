# Copyright (c) 2026, Dxbitz and contributors
"""Named, restricted data functions for Synapse dashboards."""

import frappe
from frappe.model.document import Document
from frappe.utils.safe_exec import FrappeTransformer
from RestrictedPython import compile_restricted


class SynapseScript(Document):
	def validate(self):
		frappe.only_for("System Manager")
		compile_restricted(self.script, filename=self.name or "Synapse Script", policy=FrappeTransformer)
