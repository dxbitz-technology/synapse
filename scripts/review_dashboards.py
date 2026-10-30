"""Export four local aggregate dashboard snapshots. No site records/config are changed.

Run from bench/sites with the bench Python, --site NAME and --output PATH.
Script records and the scripting switch are mocked only for this QA execution.
"""

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import frappe
from jsonschema import Draft7Validator

from synapse import scripts
from synapse.components.catalog import catalog
from synapse.mcp_tools import settings


def block(kind, title, data, columns=6, **config):
	return {
		"component_type": kind,
		"columns": columns,
		"config": {"title": title, **config},
		"frozen_data": data,
	}


def build():
	def run(sql, values=None):
		doc = frappe._dict(
			name="visual-review-query",
			enabled=1,
			script="result = {'rows': query(args['sql'], args.get('values'))}",
		)
		doc.check_permission = lambda *args: None
		with patch.object(frappe, "get_doc", return_value=doc):
			return scripts.execute_script(doc.name, {"sql": sql, "values": values})["rows"]

	assert run("SELECT %(value)s AS value", {"value": 5})[0]["value"] == 5

	company_scope = "company IN (SELECT name FROM tabCompany WHERE default_currency='AED')"
	financial_doctypes = {
		"Sales Invoice",
		"Sales Order",
		"Purchase Invoice",
		"Purchase Order",
		"Stock Ledger Entry",
	}

	def scope(doctype):
		return company_scope if doctype in financial_doctypes else "1=1"

	def count(doctype, condition="1=1"):
		return run(
			f"SELECT COUNT(name) AS value FROM `tab{doctype}` WHERE ({condition}) AND {scope(doctype)}"
		)[0]["value"]

	def total(doctype, field):
		return run(
			f"SELECT COALESCE(SUM({field}),0) AS value FROM `tab{doctype}` WHERE docstatus=1 AND {scope(doctype)}"
		)[0]["value"]

	def statuses(doctype):
		rows = run(
			f"SELECT status AS label,COUNT(name) AS value FROM `tab{doctype}` WHERE {scope(doctype)} GROUP BY status ORDER BY value DESC LIMIT 8"
		)
		return {"labels": [r["label"] or "Unspecified" for r in rows], "values": [r["value"] for r in rows]}

	def monthly(doctype, field):
		rows = run(
			f"SELECT DATE_FORMAT(posting_date,'%Y-%m') AS label, SUM({field}) AS value FROM `tab{doctype}` WHERE docstatus=1 AND {scope(doctype)} GROUP BY label ORDER BY label DESC LIMIT 6"
		)
		rows.reverse()
		return {
			"labels": [r["label"] for r in rows],
			"series": [{"name": "Amount", "values": [r["value"] for r in rows]}],
		}

	def card(title, value, currency=False):
		return block(
			"number_card",
			title,
			{"value": value},
			4,
			value_type="currency" if currency else "int",
			currency="AED",
			precision=0,
		)

	def summary(data):
		return {
			"columns": [
				{"key": "label", "label": "Status", "type": "text"},
				{"key": "value", "label": "Count", "type": "int"},
			],
			"rows": [
				{"label": label, "value": value}
				for label, value in zip(data["labels"], data["values"], strict=True)
			],
		}

	result = {}
	for key, title, invoice, order in (
		("sales", "Sales", "Sales Invoice", "Sales Order"),
		("buying", "Buying", "Purchase Invoice", "Purchase Order"),
	):
		status = statuses(order)
		result[key] = {
			"title": title,
			"blocks": [
				card("Submitted invoices · all dates", count(invoice, "docstatus=1")),
				card("Submitted invoice value · AED", total(invoice, "base_grand_total"), True),
				card("Orders · all statuses", count(order)),
				block(
					"bar_chart",
					"Invoice value · latest six active months · AED",
					monthly(invoice, "base_grand_total"),
					8,
				),
				block("donut_chart", "Orders by status", status, 4),
				block(
					"bar_horizontal",
					"Order counts by status",
					{"labels": status["labels"], "series": [{"name": "Orders", "values": status["values"]}]},
				),
				block("table", "Order status summary", summary(status)),
			],
		}
	stock = run(
		"SELECT warehouse AS label, SUM(stock_value) AS value FROM tabBin WHERE warehouse IN (SELECT name FROM tabWarehouse WHERE "
		+ company_scope
		+ ") GROUP BY warehouse ORDER BY value DESC LIMIT 8"
	)
	movements = run(
		"SELECT UNIX_TIMESTAMP(posting_date) AS day, COUNT(name) AS value FROM `tabStock Ledger Entry` WHERE is_cancelled=0 AND "
		+ company_scope
		+ " GROUP BY posting_date ORDER BY posting_date DESC LIMIT 90"
	)
	result["stock"] = {
		"title": "Stock",
		"blocks": [
			card("Enabled stock items", count("Item", "disabled=0 AND is_stock_item=1")),
			card("Stock ledger entries", count("Stock Ledger Entry", "is_cancelled=0")),
			card(
				"Stock value · AED",
				run(
					"SELECT COALESCE(SUM(stock_value),0) AS value FROM tabBin WHERE warehouse IN (SELECT name FROM tabWarehouse WHERE "
					+ company_scope
					+ ")"
				)[0]["value"],
				True,
			),
			block(
				"bar_horizontal",
				"Stock value by warehouse · AED",
				{
					"labels": [r["label"] for r in stock],
					"series": [{"name": "Stock value", "values": [r["value"] for r in stock]}],
				},
			),
			block(
				"heatmap",
				"Daily stock movements · latest active days",
				{"dataPoints": {str(int(r["day"])): r["value"] for r in movements}},
			),
			block(
				"table",
				"Warehouse stock value",
				{
					"columns": [
						{"key": "label", "label": "Warehouse", "type": "text"},
						{"key": "value", "label": "Stock value", "type": "currency"},
					],
					"rows": stock,
				},
				12,
				currency="AED",
			),
		],
	}
	project_status, task_status = statuses("Project"), statuses("Task")
	progress = run(
		"SELECT status AS label,AVG(percent_complete) AS value FROM tabProject GROUP BY status ORDER BY value DESC LIMIT 8"
	)
	result["projects"] = {
		"title": "Projects",
		"blocks": [
			card("Projects · all statuses", count("Project")),
			card("Tasks · all statuses", count("Task")),
			card("Completed tasks", count("Task", "status='Completed'")),
			block("donut_chart", "Projects by status", project_status),
			block(
				"bar_horizontal",
				"Tasks by status",
				{
					"labels": task_status["labels"],
					"series": [{"name": "Tasks", "values": task_status["values"]}],
				},
			),
			block(
				"table",
				"Average project completion",
				{
					"columns": [
						{"key": "label", "label": "Status", "type": "text"},
						{"key": "value", "label": "Completion", "type": "percent"},
					],
					"rows": progress,
				},
				12,
			),
		],
	}
	components = {c["key"]: c for c in catalog()}
	for model in result.values():
		model["subtitle"] = f"Local {frappe.local.site} snapshot · All dates unless stated"
		if model["title"] in {"Sales", "Buying", "Stock"}:
			model["subtitle"] += " · AED companies"
		for item in model["blocks"]:
			definition = components[item["component_type"]]
			Draft7Validator(definition["data_template"]).validate(item["frozen_data"])
			Draft7Validator(definition["options_schema"]).validate(item["config"])
	return result


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--site", required=True)
	parser.add_argument("--output", required=True)
	args = parser.parse_args()
	frappe.init(site=args.site)
	frappe.connect()
	frappe.set_user("Administrator")
	try:
		from frappe.utils.safe_exec import get_safe_globals

		get_safe_globals()
		with (
			patch("frappe.utils.safe_exec.is_safe_exec_enabled", return_value=True),
			patch.object(settings, "sql_tool_enabled", return_value=True),
		):
			models = build()
		Path(args.output).write_text(json.dumps(models, indent=2))
		print({key: len(value["blocks"]) for key, value in models.items()})
	finally:
		frappe.db.rollback()
		frappe.destroy()
