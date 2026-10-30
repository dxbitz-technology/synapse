# Copyright (c) 2026, Dxbitz and contributors
"""Run saved dashboard functions without exposing write APIs to scripts."""

import json

import frappe
from frappe.utils.safe_exec import NamespaceDict, safe_exec

from synapse.mcp_tools import audit, connection, documents, serialise, settings
from synapse.mcp_tools.guard import validate_read_only


def parameters(value):
	if isinstance(value, str):
		value = json.loads(value)
		if not isinstance(value, dict):
			frappe.throw("Script parameters must be a JSON object.")
	if value is None:
		value = {}
	if not isinstance(value, dict):
		frappe.throw("Script parameters must be a JSON object.")
	return value


def query(sql, values=None):
	"""Bound, capped SELECT queries. SQL never promises row-level permissions."""
	frappe.only_for("System Manager")
	if not settings.sql_tool_enabled():
		frappe.throw("Synapse SQL access is disabled for this user.", frappe.PermissionError)
	sql = validate_read_only(sql, frappe.conf.get("mcp_sql_blocked_tables"))
	if audit.current():
		audit.current().sql(sql)
	limit = settings.row_limit(None)
	sql = f"SELECT * FROM ({sql}) AS synapse_script_result LIMIT {limit}"
	if connection.is_configured():
		with connection.read_only_cursor(15) as cursor:
			cursor.execute(sql, values)
			rows = list(cursor.fetchmany(limit))
	else:
		# A statement-local timeout avoids changing the request's session or transaction.
		statement = "SET STATEMENT max_statement_time=15 FOR " + sql
		rows = (
			frappe.db.sql(statement, as_dict=True)
			if values is None
			else frappe.db.sql(statement, values, as_dict=True)
		)
	return serialise.to_client(rows)


def execute_script(name, args=None):
	doc = frappe.get_doc("Synapse Script", name)
	doc.check_permission("read")
	if not doc.enabled:
		frappe.throw("This Synapse Script is disabled.", frappe.PermissionError)

	# Document helpers retain Synapse grants, field checks and Frappe permissions.
	namespace = NamespaceDict(
		get_list=lambda doctype, **kw: documents.get_list.__wrapped__(doctype=doctype, **kw)["rows"],
		get_count=lambda doctype, **kw: documents.get_count.__wrapped__(doctype=doctype, **kw)["count"],
		db=NamespaceDict(sql=query),
		session=NamespaceDict(user=frappe.session.user),
	)
	context = {"args": parameters(args)}
	safe_exec(
		doc.script,
		_globals={
			"frappe": namespace,
			"args": context["args"],
			"query": query,
			"run_script": None,
			"FrappeClient": None,
			"get_visible_columns": None,
		},
		_locals=context,
		restrict_commit_rollback=True,
		script_filename=doc.name,
	)
	result = serialise.to_client(context.get("result"))
	if not isinstance(result, dict):
		frappe.throw("Synapse Script must assign an object to result.")
	return result


@frappe.whitelist()
def run_script(name: str, args=None):
	"""Call a saved Synapse Script with an optional JSON parameter object."""
	from synapse.mcp_tools.scripts import execute_synapse_script

	response = execute_synapse_script(name=name, args=parameters(args))
	if not response.get("success"):
		frappe.throw(response.get("error") or "Could not execute Synapse Script.")
	return response["data"]
