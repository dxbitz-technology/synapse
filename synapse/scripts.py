# Copyright (c) 2026, Dxbitz and contributors
"""Run saved dashboard functions without exposing write APIs to scripts."""

import json
import math

import frappe
from frappe.utils.safe_exec import NamespaceDict, safe_exec

from synapse.mcp_tools import audit, connection, documents, serialise, settings
from synapse.mcp_tools.guard import validate_read_only
from synapse.run_budget import Budget, BudgetExceeded
from synapse.sandbox_hints import sandbox_hint


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


def _budget():
	return getattr(frappe.local, "synapse_budget", None)


def _charged(call):
	"""Wrap a script helper so every call counts against the run's budget."""

	def run(*args, **kwargs):
		budget = _budget()
		if budget:
			budget.before_call()
		rows = call(*args, **kwargs)
		if budget and isinstance(rows, list):
			budget.after_call(rows)
		return rows

	return run


def _new_budget():
	conf = frappe.conf
	return Budget(
		queries=conf.get("synapse_script_max_queries"),
		rows=conf.get("synapse_script_max_rows"),
		seconds=conf.get("synapse_script_max_seconds"),
	)


def query(sql, values=None):
	"""Bound, capped SELECT queries. SQL never promises row-level permissions."""
	frappe.only_for("System Manager")
	budget = _budget()
	seconds = 15
	if budget:
		seconds = max(1, min(seconds, math.ceil(budget.before_call())))
	if not settings.sql_tool_enabled():
		frappe.throw("Synapse SQL access is disabled for this user.", frappe.PermissionError)
	sql = validate_read_only(sql, frappe.conf.get("mcp_sql_blocked_tables"))
	if audit.current():
		audit.current().sql(sql)
	limit = settings.row_limit(None)
	sql = f"SELECT * FROM ({sql}) AS synapse_script_result LIMIT {limit}"
	if connection.is_configured():
		with connection.read_only_cursor(seconds) as cursor:
			cursor.execute(sql, values)
			rows = list(cursor.fetchmany(limit))
	else:
		# A statement-local timeout avoids changing the request's session or transaction.
		statement = f"SET STATEMENT max_statement_time={seconds} FOR " + sql
		rows = (
			frappe.db.sql(statement, as_dict=True)
			if values is None
			else frappe.db.sql(statement, values, as_dict=True)
		)
	if budget:
		budget.after_call(rows)
	return serialise.to_client(rows)


def _aggregate(doctype, metrics=None, group_by=None, period=None, filters=None, order_by=None, limit=None):
	"""frappe.aggregate in scripts: the same engine as the aggregate MCP tool, rows only."""
	from synapse import aggregate as engine
	from synapse.mcp_tools.policy import READ, check

	check(settings.get_policy(), READ, doctype)
	spec = {
		"doctype": doctype,
		"metrics": metrics,
		"group_by": group_by,
		"period": period,
		"filters": filters,
		"order_by": order_by,
		"limit": limit,
	}
	try:
		return engine.run(engine.compile_spec(spec))["rows"]
	except engine.SpecError as error:
		frappe.throw(str(error))


def _script_line(error, name) -> str:
	"""', line N' for the deepest frame inside the script, when there is one.

	Frappe compiles scripts under a filename that ends with the scrubbed script name.
	"""
	marker = frappe.scrub(name)
	line = None
	tb = error.__traceback__
	while tb is not None:
		if tb.tb_frame.f_code.co_filename.endswith(marker):
			line = tb.tb_lineno
		tb = tb.tb_next
	return f", line {line}" if line else ""


def execute_script(name, args=None):
	doc = frappe.get_doc("Synapse Script", name)
	doc.check_permission("read")
	if not doc.enabled:
		frappe.throw("This Synapse Script is disabled.", frappe.PermissionError)

	# Document helpers retain Synapse grants, field checks and Frappe permissions.
	namespace = NamespaceDict(
		get_list=_charged(
			lambda doctype, **kw: documents.get_list.__wrapped__(doctype=doctype, **kw)["rows"]
		),
		get_count=_charged(
			lambda doctype, **kw: documents.get_count.__wrapped__(doctype=doctype, **kw)["count"]
		),
		aggregate=_charged(lambda doctype, **kw: _aggregate(doctype, **kw)),
		db=NamespaceDict(sql=query),
		session=NamespaceDict(user=frappe.session.user),
	)
	context = {"args": parameters(args)}
	outer = _budget()
	budget = frappe.local.synapse_budget = outer or _new_budget()
	try:
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
	except BudgetExceeded:
		pass
	except SyntaxError as error:
		hint = sandbox_hint(error)
		if not hint:
			raise
		frappe.throw(f"Synapse Script {doc.name}{_script_line(error, doc.name)}: {hint}")
	finally:
		frappe.local.synapse_budget = outer
	if budget.stopped:
		# Checked after the run too, in case the script caught the stop with a bare except.
		frappe.throw(f"Synapse Script {doc.name} was stopped to protect the server: {budget.stopped}")
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
