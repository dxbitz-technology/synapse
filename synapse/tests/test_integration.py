"""Database regressions for endpoint permissions, writes, auditing and pages."""

import json
import unittest
from unittest.mock import patch

import frappe
from frappe.model.document import Document
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request, Response

from synapse import api, extend
from synapse.components.catalog import catalog, seed
from synapse.mcp import handle_mcp, mcp
from synapse.mcp_tools import audit, documents, settings
from synapse.mcp_tools.policy import Policy
from synapse.synapse.doctype.synapse_log.synapse_log import SynapseLog

RECORD = "Synapse Test Record"
CHILD = "Synapse Test Row"
ROLE = "Synapse Test Operator"
USER = "synapse-test@example.invalid"


def sample_custom_tool(value: str = "ok"):
	return {"value": value}


class TestSynapseIntegration(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		frappe.set_user("Administrator")
		if not frappe.db.exists("Role", ROLE):
			frappe.get_doc({"doctype": "Role", "role_name": ROLE}).insert()
		if not frappe.db.exists("DocType", CHILD):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": CHILD,
					"module": "Synapse",
					"custom": 1,
					"istable": 1,
					"fields": [
						{"fieldname": "label", "label": "Label", "fieldtype": "Data"},
						{"fieldname": "pin", "label": "PIN", "fieldtype": "Password"},
					],
				}
			).insert()
		if not frappe.db.exists("DocType", RECORD):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": RECORD,
					"module": "Synapse",
					"custom": 1,
					"is_submittable": 1,
					"autoname": "hash",
					"fields": [
						{"fieldname": "title", "label": "Title", "fieldtype": "Data", "reqd": 1},
						{
							"fieldname": "private_note",
							"label": "Private Note",
							"fieldtype": "Data",
							"permlevel": 1,
						},
						{"fieldname": "items", "label": "Items", "fieldtype": "Table", "options": CHILD},
					],
					"permissions": [
						{
							"role": ROLE,
							"read": 1,
							"write": 1,
							"create": 1,
							"submit": 1,
							"cancel": 1,
							"delete": 1,
						},
						{"role": "System Manager", "read": 1, "write": 1, "create": 1},
					],
				}
			).insert()
		if not frappe.db.exists("User", USER):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": USER,
					"first_name": "Synapse Test",
					"send_welcome_email": 0,
					"roles": [{"role": ROLE}],
				}
			).insert()
		if not frappe.db.exists("Synapse Profile", "Synapse Test Profile"):
			frappe.get_doc(
				{
					"doctype": "Synapse Profile",
					"profile_name": "Synapse Test Profile",
					"enabled": 1,
					"roles": [{"role": ROLE}],
					"doctype_access": [
						{
							"document_type": RECORD,
							"allow_read": 1,
							"allow_write": 1,
							"allow_submit": 1,
							"allow_cancel": 1,
							"allow_delete": 1,
							"allow_operate": 1,
						}
					],
				}
			).insert()
		frappe.db.commit()

	def setUp(self):
		frappe.set_user("Administrator")
		config = frappe.get_single("Synapse Settings")
		config.update(
			{
				"enabled": 1,
				"enable_read_tools": 1,
				"enable_write_tools": 1,
				"enable_custom_tools": 1,
				"log_payloads": 1,
			}
		)
		config.save()
		frappe.db.commit()
		frappe.set_user(USER)
		settings.clear_cache()
		if hasattr(frappe.local, "_synapse_external_tools"):
			del frappe.local._synapse_external_tools

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")
		settings.clear_cache()

	def create_record(self, **values):
		result = documents.create_doc(doctype=RECORD, values={"title": "Original", **values})
		self.assertTrue(result["success"], result)
		return result["name"]

	def test_fresh_install_has_catalog_and_seed_is_repeatable(self):
		self.assertEqual(frappe.db.count("Synapse Component"), len(catalog()))
		seed()
		self.assertEqual(frappe.db.count("Synapse Component"), len(catalog()))

	def test_real_document_lifecycle_and_audit(self):
		name = self.create_record()
		self.assertTrue(
			documents.update_doc(doctype=RECORD, name=name, values={"title": "Changed"})["success"]
		)
		self.assertEqual(documents.get_doc(doctype=RECORD, name=name)["doc"]["title"], "Changed")
		self.assertTrue(documents.submit_doc(doctype=RECORD, name=name)["success"])
		self.assertTrue(documents.cancel_doc(doctype=RECORD, name=name)["success"])
		self.assertTrue(documents.delete_doc(doctype=RECORD, name=name)["success"])
		self.assertGreaterEqual(frappe.db.count("Synapse Log", {"reference_name": name}), 6)

	def test_internal_and_unknown_fields_rejected_without_changes(self):
		name = self.create_record()
		for field in ("_action", "flags", "unknown_field", "docstatus"):
			result = documents.update_doc(
				doctype=RECORD, name=name, values={field: "discard", "title": "Bad"}
			)
			self.assertFalse(result["success"], field)
			self.assertEqual(frappe.db.get_value(RECORD, name, "title"), "Original")
		self.assertFalse(
			documents.create_doc(doctype=RECORD, values={"title": "Bad", "items": ["bad row"]})["success"]
		)

	def test_validations_still_run(self):
		original = Document.run_method
		calls = []

		def observed(doc, method, *args, **kwargs):
			if doc.doctype == RECORD and method == "validate":
				calls.append(method)
			return original(doc, method, *args, **kwargs)

		with patch.object(Document, "run_method", observed):
			self.create_record()
		self.assertIn("validate", calls)
		self.assertFalse(documents.create_doc(doctype=RECORD, values={"title": ""})["success"])

	def test_frappe_permissions_and_profile_backstop(self):
		self.assertFalse(documents.get_list(doctype="User")["success"])
		self.assertFalse(documents.get_doc(doctype="OAuth Bearer Token", name="missing")["success"])
		name = self.create_record()
		with patch.object(
			settings, "get_policy", return_value=Policy(enabled=True, read_enabled=True, full_access=True)
		):
			self.assertFalse(documents.get_list(doctype="DocType")["success"])
		frappe.set_user("Guest")
		settings.clear_cache()
		self.assertFalse(documents.get_doc(doctype=RECORD, name=name)["success"])

	def test_framework_operations_are_denied(self):
		name = self.create_record()
		for operation in (
			"get_password",
			"queue_action",
			"db_update_all",
			"run_trigger",
			"as_dict",
			"get",
			"validate",
			"onload",
			"before_print",
			"after_rename",
			"submit",
		):
			result = documents.run_operation(doctype=RECORD, name=name, operation=operation)
			self.assertFalse(result["success"], operation)

	def test_controller_operation_still_works(self):
		name = self.create_record()
		controller = type(frappe.get_doc(RECORD, name))
		with patch.object(
			controller, "synapse_test_operation", lambda doc: {"title": doc.title}, create=True
		):
			result = documents.run_operation(doctype=RECORD, name=name, operation="synapse_test_operation")
		self.assertTrue(result["success"], result)
		self.assertEqual(result["result"]["title"], "Original")

	def test_child_edits_are_atomic_and_secrets_are_masked(self):
		name = self.create_record(items=[{"label": "One", "pin": "old-example"}, {"label": "Two"}])
		rows = frappe.get_doc(RECORD, name).items
		result = documents.set_child_rows(
			parent_doctype=RECORD,
			parent_name=name,
			child_field="items",
			edits=[
				{"row_name": rows[0].name, "changes": {"label": "Changed"}},
				{"row_name": rows[1].name, "changes": {"label": "Changed"}, "expect": {"label": "Stale"}},
			],
		)
		self.assertFalse(result["success"])
		self.assertEqual(frappe.get_doc(RECORD, name).items[0].label, "One")
		result = documents.set_child_value(
			parent_doctype=RECORD,
			parent_name=name,
			child_field="items",
			row_name=rows[0].name,
			changes={"pin": "new-example"},
		)
		self.assertTrue(result["success"], result)
		logs = frappe.get_all(
			"Synapse Log", filters={"reference_name": name}, fields=["payload", "changes", "reason"]
		)
		serialized = json.dumps(logs)
		self.assertNotIn("new-example", serialized)
		self.assertNotIn("old-example", serialized)
		self.assertIn("***", serialized)

	def test_audit_failure_rolls_back_write(self):
		name = self.create_record()
		with patch.object(SynapseLog, "db_insert", side_effect=RuntimeError("injected audit failure")):
			result = mcp._call_tool(
				{
					"name": "update_doc",
					"arguments": {"doctype": RECORD, "name": name, "values": {"title": "Unlogged"}},
				}
			)
		self.assertTrue(result["isError"], result)
		self.assertEqual(frappe.db.get_value(RECORD, name, "title"), "Original")

	def test_refusal_sets_mcp_error_flag(self):
		result = mcp._call_tool({"name": "get_doc", "arguments": {"doctype": "User", "name": USER}})
		self.assertTrue(result["isError"])
		self.assertFalse(result["structuredContent"]["success"])
		self.assertTrue(mcp._call_tool({"name": [], "arguments": {}})["isError"])

	def test_guest_discovery_and_initialize(self):
		frappe.set_user("Guest")
		response = handle_mcp()
		self.assertEqual(response.status_code, 401)
		self.assertIn("resource_metadata", response.headers["WWW-Authenticate"])
		request = Request(
			EnvironBuilder(
				method="POST",
				json={
					"jsonrpc": "2.0",
					"id": 1,
					"method": "initialize",
					"params": {"protocolVersion": "2025-06-18"},
				},
			).get_environ()
		)
		response = mcp.handle(request, Response())
		self.assertEqual(response.json["result"]["serverInfo"]["version"], "16.0.1")

	def test_custom_registrations_do_not_leak_between_requests(self):
		hook = [
			{
				"method": "synapse.tests.test_integration.sample_custom_tool",
				"name": "site_tool",
				"read_only": True,
			}
		]
		with patch.object(frappe, "get_hooks", return_value=hook):
			self.assertIn("site_tool", extend.load_external_tools())
		del frappe.local._synapse_external_tools
		with patch.object(frappe, "get_hooks", return_value=[]):
			self.assertNotIn("site_tool", extend.load_external_tools())
		self.assertNotIn("site_tool", mcp._tools)

	def test_custom_tool_collision_is_rejected(self):
		declarations = [
			{
				"method": "synapse.tests.test_integration.sample_custom_tool",
				"name": "collision",
				"read_only": True,
			},
			{
				"method": "synapse.tests.test_integration.sample_custom_tool",
				"name": "collision",
				"read_only": False,
			},
		]
		with patch.object(frappe, "get_hooks", return_value=declarations), patch.object(frappe, "log_error"):
			self.assertNotIn("collision", extend.registered_tools())

	def test_custom_tools_obey_read_and_write_switches(self):
		policy = Policy(
			enabled=True,
			read_enabled=True,
			write_enabled=False,
			custom_enabled=True,
			custom_tools=frozenset({"test"}),
		)
		with patch.object(settings, "get_policy", return_value=policy):
			self.assertFalse(settings.custom_tool_enabled("test", read_only=False))
			self.assertTrue(settings.custom_tool_enabled("test", read_only=True))

	def test_page_schema_and_disabled_state(self):
		frappe.set_user("Administrator")
		page = frappe.get_doc(
			{
				"doctype": "Synapse Page",
				"title": "Test",
				"page_name": frappe.generate_hash(length=10),
				"blocks": [
					{
						"component_type": "number_card",
						"columns": 12,
						"config": "{}",
						"frozen_data": '{"value": 12}',
					}
				],
			}
		)
		page.insert()
		self.assertEqual(api.get_page_layout(page.name)["blocks"][0]["frozen_data"]["value"], 12)
		page.enabled = 0
		page.save()
		with self.assertRaises(frappe.PermissionError):
			api.get_page_layout(page.name)
		for bad in ('"scalar"', '{"wrong": 12}', '{"value": "not a number"}'):
			page.blocks[0].frozen_data = bad
			with self.assertRaises(frappe.ValidationError):
				page.save()

	def test_sql_database_result_is_capped(self):
		policy = Policy(enabled=True, sql_enabled=True)
		queries = [
			"SELECT 1 AS value UNION ALL SELECT 2 UNION ALL SELECT 3 LIMIT 99999",
			"WITH values_cte AS (SELECT 1 AS value UNION ALL SELECT 2) SELECT * FROM values_cte",
		]
		with (
			patch.dict(frappe.conf, {"mcp_sql_allow_guard_only": True}),
			patch.object(settings, "get_policy", return_value=policy),
		):
			for query in queries:
				result = mcp._call_tool({"name": "run_sql_query", "arguments": {"query": query, "limit": 1}})
				self.assertFalse(result["isError"], result)
				self.assertEqual(result["structuredContent"]["row_count"], 1)
				self.assertTrue(result["structuredContent"]["truncated"])
