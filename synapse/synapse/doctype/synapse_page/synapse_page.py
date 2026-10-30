# Copyright (c) 2026, Dxbitz and contributors
"""Validate pages with the same component contracts as previews and scripts."""

import re

import frappe
from frappe.model.document import Document

from synapse.components.contracts import json_object, validate_component

FULL_WIDTH_ONLY = {"section_break", "spacer"}


class SynapsePage(Document):
	def validate(self):
		if not re.fullmatch(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", self.page_name or ""):
			frappe.throw(frappe._("Route Name must use lowercase letters, numbers, hyphens or underscores."))
		for i, block in enumerate(self.blocks or [], start=1):
			try:
				definition = validate_component(block.component_type, json_object(block.config))
				self._clamp_columns(block)
				if block.get("data_script"):
					if definition.get("is_layout"):
						frappe.throw(frappe._("Layout blocks cannot use a data script."))
					json_object(block.script_parameters)
					script = frappe.get_doc("Synapse Script", block.data_script)
					script.check_permission("read")
					if not script.enabled:
						frappe.throw(frappe._("The data script is disabled."))
				else:
					validate_component(
						block.component_type, json_object(block.config), json_object(block.frozen_data)
					)
			except frappe.ValidationError as error:
				frappe.throw(frappe._("Block {0}: {1}").format(i, str(error)))

	def _clamp_columns(self, block):
		if block.component_type in FULL_WIDTH_ONLY:
			block.columns = 12
			return
		try:
			cols = int(block.columns or 12)
		except (TypeError, ValueError):
			cols = 12
		block.columns = max(1, min(cols, 12))
