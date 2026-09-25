# Copyright (c) 2026, Dxbitz and contributors
"""Validate saved page blocks against the component catalog."""

import json

import frappe
from frappe import _
from frappe.model.document import Document
from jsonschema import Draft7Validator

from synapse.components.catalog import catalog

FULL_WIDTH_ONLY = {"section_break", "spacer"}


class SynapsePage(Document):
	def validate(self):
		components = {component["key"]: component for component in catalog()}
		for i, block in enumerate(self.blocks or [], start=1):
			component = components.get(block.component_type)
			if not component or component.get("not_implemented"):
				frappe.throw(_("Block {0}: this component is not available.").format(i))
			self._clamp_columns(block)
			self._check_json(block, "config", i, component["options_schema"])
			self._check_json(block, "frozen_data", i, component["data_template"])

	def _clamp_columns(self, block):
		if block.component_type in FULL_WIDTH_ONLY:
			block.columns = 12
			return
		try:
			cols = int(block.columns or 12)
		except (TypeError, ValueError):
			cols = 12
		block.columns = max(1, min(cols, 12))

	def _check_json(self, block, field, row, schema):
		raw = block.get(field)
		try:
			value = json.loads(raw) if raw else {}
		except Exception as e:
			frappe.throw(_("Block {0}: {1} is not valid JSON ({2}).").format(row, field, str(e)))

		errors = list(Draft7Validator(schema).iter_errors(value))
		if errors:
			error = errors[0]
			path = ".".join(str(part) for part in error.path) or field
			frappe.throw(_("Block {0}: invalid {1} at {2}.").format(row, field, path))
