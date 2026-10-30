"""Script runtime regressions; run with a Frappe site context."""

import unittest
from unittest.mock import Mock, patch

import frappe
from frappe.utils.safe_exec import ServerScriptNotEnabled, get_safe_globals

from synapse import api, scripts
from synapse.mcp_tools import audit, settings
from synapse.mcp_tools.guard import UnsafeQuery
from synapse.mcp_tools.policy import Policy


class TestSynapseScripts(unittest.TestCase):
	def setUp(self):
		get_safe_globals()
		self.doc = frappe._dict(
			name="test-data", enabled=1, script='result = {"value": args.get("value", 1)}'
		)
		self.doc.check_permission = Mock()
		self.doc_patcher = patch.object(frappe, "get_doc", return_value=self.doc)
		self.doc_patcher.start()
		self.addCleanup(self.doc_patcher.stop)

	def test_parameters_reject_non_objects(self):
		for value in ("[]", "null", 12):
			with self.subTest(value=value), self.assertRaises(frappe.ValidationError):
				scripts.parameters(value)

	def test_disabled_script_never_runs(self):
		self.doc.enabled = 0
		with self.assertRaises(frappe.PermissionError):
			scripts.execute_script("test-data")

	def test_read_permission_is_checked(self):
		self.doc.check_permission.side_effect = frappe.PermissionError
		with self.assertRaises(frappe.PermissionError):
			scripts.execute_script("test-data")

	def test_server_script_switch_is_respected(self):
		with patch("frappe.utils.safe_exec.is_safe_exec_enabled", return_value=False):
			with self.assertRaises(ServerScriptNotEnabled):
				scripts.execute_script("test-data")

	def test_fresh_parameters_and_result(self):
		with patch("frappe.utils.safe_exec.is_safe_exec_enabled", return_value=True):
			self.assertEqual(scripts.execute_script("test-data", {"value": 2}), {"value": 2})
			self.assertEqual(scripts.execute_script("test-data", {"value": 3}), {"value": 3})

	def test_scripts_cannot_use_write_or_unrestricted_read_apis(self):
		for code in (
			'frappe.db.set_value("Task", "one", "status", "Closed")',
			'frappe.get_all("User")',
			'frappe.call("frappe.client.delete", doctype="Task", name="one")',
			"import os",
			'run_script("another-script")',
		):
			self.doc.script = code
			with (
				self.subTest(code=code),
				patch("frappe.utils.safe_exec.is_safe_exec_enabled", return_value=True),
			):
				with self.assertRaises(Exception):
					scripts.execute_script("test-data")

	def test_sql_requires_access_and_preserves_bound_values(self):
		with patch.object(frappe, "only_for"), patch.object(settings, "sql_tool_enabled", return_value=False):
			with self.assertRaises(frappe.PermissionError):
				scripts.query("SELECT 1")
		with (
			patch.object(frappe, "only_for"),
			patch.object(settings, "sql_tool_enabled", return_value=True),
			patch.object(settings, "row_limit", return_value=10),
			patch.object(scripts.connection, "is_configured", return_value=False),
			patch.object(frappe.db, "sql", return_value=[{"value": 5}]) as sql,
		):
			self.assertEqual(scripts.query("SELECT %(value)s AS value", {"value": 5}), [{"value": 5}])
			self.assertEqual(sql.call_args.args[1], {"value": 5})
			self.assertIn("LIMIT 10", sql.call_args.args[0])
			scripts.query("SELECT 1 AS value")
			self.assertEqual(len(sql.call_args.args), 1)
			with self.assertRaises(UnsafeQuery):
				scripts.query("DELETE FROM tabTask")

	def test_live_page_returns_data_and_isolates_failures(self):
		block = frappe._dict(
			component_type="number_card",
			columns=12,
			config="{}",
			frozen_data='{"value":99}',
			data_script="test-data",
			script_parameters='{"value":2}',
		)
		self.doc.update(title="Live", blocks=[block])
		with patch.object(
			scripts, "run_script", side_effect=[{"value": 2}, RuntimeError("bad SQL"), {"value": "invalid"}]
		):
			first = api.get_page_layout("page")["blocks"][0]
			self.assertEqual(first["frozen_data"], {"value": 2})
			for _ in range(2):
				failed = api.get_page_layout("page")["blocks"][0]
				self.assertTrue(failed["data_error"])
				self.assertEqual(failed["frozen_data"], {})

	def test_callable_tool_requires_profile_and_returns_data(self):
		with (
			patch.object(
				settings, "get_policy", return_value=Policy(enabled=True, read_enabled=True, full_access=True)
			),
			patch.object(audit, "_write"),
			patch("frappe.utils.safe_exec.is_safe_exec_enabled", return_value=True),
		):
			self.assertEqual(scripts.run_script("test-data", '{"value":4}'), {"value": 4})
		with patch.object(settings, "get_policy", return_value=Policy()), patch.object(audit, "_write"):
			with self.assertRaises(frappe.ValidationError):
				scripts.run_script("test-data")

	def test_record_helper_keeps_one_audit_entry(self):
		self.doc.script = 'result = {"value": frappe.get_count("Task")}'
		with (
			patch.object(
				settings, "get_policy", return_value=Policy(enabled=True, read_enabled=True, full_access=True)
			),
			patch.object(scripts.documents, "_gate", return_value="Task"),
			patch.object(frappe, "get_list", return_value=[{"count": 8}]),
			patch.object(audit, "_write") as write,
			patch("frappe.utils.safe_exec.is_safe_exec_enabled", return_value=True),
		):
			self.assertEqual(scripts.run_script("test-data"), {"value": 8})
			self.assertEqual(write.call_count, 1)

	def test_functions_can_read_parameters(self):
		self.doc.script = 'def data():\n    return {"value": args.get("value")}\nresult = data()'
		with patch("frappe.utils.safe_exec.is_safe_exec_enabled", return_value=True):
			self.assertEqual(scripts.execute_script("test-data", {"value": 9}), {"value": 9})
