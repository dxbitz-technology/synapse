# Copyright (c) 2026, Dxbitz and contributors
"""Examples and validation shared by dashboard forms, scripts and MCP clients."""

import copy
import json

import frappe
from jsonschema import Draft7Validator

from synapse.components.catalog import catalog


def component_contracts():
	items = copy.deepcopy(catalog())
	for item in items:
		key = item["key"]
		if key in {"bar_chart", "bar_horizontal", "line_chart", "area_chart", "mixed_chart", "scatter_chart"}:
			data = {
				"labels": [1, 2] if key == "scatter_chart" else ["First", "Second"],
				"series": [{"name": "Total", "values": [10, 20]}],
			}
		elif key in {"pie_chart", "donut_chart", "percentage_chart"}:
			data = {"labels": ["First", "Second"], "values": [10, 20]}
		else:
			data = {
				"number_card": {"value": 10},
				"table": {
					"columns": [{"key": "name", "label": "Name", "type": "text"}],
					"rows": [{"name": "Example"}],
				},
				"list": {"items": [{"label": "Example", "value": 10}]},
				"progress": {"value": 10, "target": 20},
				"pivot": {"rowLabels": ["First"], "colLabels": ["Total"], "cells": [[10]]},
				"callout": {"level": "info", "body": "Example note"},
				"text_block": {"markdown": "Example text"},
				"heatmap": {"dataPoints": {"1790812800": 3}, "start": "2026-10-01", "end": "2026-10-31"},
				"map": {"points": [{"label": "Dubai", "latitude": 25.2, "longitude": 55.27, "value": 10}]},
			}.get(key, {})
		item["example_config"] = {}
		item["example_data"] = data
		item["script_template"] = (
			None
			if item.get("is_layout")
			else (
				"# Example data only. Replace with permitted reads for current data.\nresult = " + repr(data)
			)
		)
	return items


def validate_component(key, config, data=None):
	definition = next((item for item in catalog() if item["key"] == key), None)
	if not definition or definition.get("not_implemented"):
		frappe.throw(frappe._("This component is not available: {0}").format(key))
	for field, value, schema in (
		("config", config, definition["options_schema"]),
		("data", data, definition["data_template"]),
	):
		if value is None:
			continue
		errors = sorted(Draft7Validator(schema).iter_errors(value), key=lambda error: str(list(error.path)))
		if errors:
			error = errors[0]
			path = ".".join(map(str, error.path)) or field
			frappe.throw(frappe._("Invalid {0} at {1}: {2}").format(field, path, error.message))
	if data is not None:
		if "series" in data and "labels" in data:
			if any(len(series["values"]) != len(data["labels"]) for series in data["series"]):
				frappe.throw(frappe._("Every series must have one value per label."))
			if key == "scatter_chart" and any(
				isinstance(x, bool) or not isinstance(x, (int, float)) for x in data["labels"]
			):
				frappe.throw(frappe._("Scatter chart labels must be numeric x coordinates."))
		if "values" in data and "labels" in data and len(data["values"]) != len(data["labels"]):
			frappe.throw(frappe._("Provide one value per label."))
		if key == "pivot" and (
			len(data["cells"]) != len(data["rowLabels"])
			or any(len(row) != len(data["colLabels"]) for row in data["cells"])
		):
			frappe.throw(frappe._("Pivot cells must match the row and column labels."))
	return definition


def json_object(value):
	try:
		parsed = json.loads(value) if isinstance(value, str) and value.strip() else value
	except (TypeError, ValueError):
		frappe.throw(frappe._("Enter valid JSON."))
	if parsed is None or parsed == "":
		return {}
	if not isinstance(parsed, dict):
		frappe.throw(frappe._("Enter a JSON object."))
	return parsed
