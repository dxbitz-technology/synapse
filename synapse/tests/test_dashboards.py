"""Dashboard contract, sharing and script compatibility regressions."""

import json
import unittest
from unittest.mock import patch

import frappe

from synapse import api, scripts
from synapse.components.contracts import component_contracts, validate_component
from synapse.mcp_tools import audit, settings
from synapse.mcp_tools.policy import Policy
from synapse.mcp_tools.scripts import get_dashboard_contract, validate_dashboard_component


class TestDashboardContracts(unittest.TestCase):
	def test_every_template_runs_and_matches_its_contract(self):
		for item in component_contracts():
			with self.subTest(component=item["key"]):
				validate_component(item["key"], item["example_config"], item["example_data"])
				if item["script_template"]:
					doc = frappe._dict(name="example", enabled=1, script=item["script_template"])
					doc.check_permission = lambda *_: None
					with (
						patch.object(frappe, "get_doc", return_value=doc),
						patch("frappe.utils.safe_exec.is_safe_exec_enabled", return_value=True),
					):
						result = scripts.execute_script("example")
						self.assertEqual(result, item["example_data"])
						validate_component(item["key"], {}, result)

	def test_mismatched_series_parts_and_pivots_are_rejected(self):
		for key, data in (
			("line_chart", {"labels": ["one"], "series": [{"name": "Total", "values": [1, 2]}]}),
			("pie_chart", {"labels": ["one"], "values": []}),
			("pivot", {"rowLabels": ["one"], "colLabels": ["Total"], "cells": [[]]}),
			("scatter_chart", {"labels": ["text"], "series": [{"name": "Total", "values": [1]}]}),
		):
			with self.subTest(key=key), self.assertRaises(frappe.ValidationError):
				validate_component(key, {}, data)

	def test_examples_are_independent_of_catalog(self):
		first = component_contracts()
		first[0]["example_data"]["labels"].append("changed")
		self.assertNotIn("changed", component_contracts()[0]["example_data"]["labels"])


class TestDashboardSharing(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.key = "dashboard-test-" + frappe.generate_hash(length=8).lower()
		self.user = self.key + "@example.invalid"
		role = frappe.get_doc({"doctype": "Role", "role_name": self.key, "desk_access": 1}).insert()
		frappe.get_doc(
			{
				"doctype": "User",
				"email": self.user,
				"first_name": "Dashboard reader",
				"send_welcome_email": 0,
				"roles": [{"role": role.name}],
			}
		).insert()
		self.script = frappe.get_doc(
			{
				"doctype": "Synapse Script",
				"script_name": self.key,
				"enabled": 1,
				"script": 'result = {"value": frappe.get_count("Synapse Page")}',
			}
		).insert()
		self.page = frappe.get_doc(
			{
				"doctype": "Synapse Page",
				"page_name": self.key,
				"title": "Shared dashboard",
				"enabled": 1,
				"blocks": [
					{
						"component_type": "number_card",
						"columns": 6,
						"config": "{}",
						"data_script": self.script.name,
						"script_parameters": "{}",
					},
					{
						"component_type": "number_card",
						"columns": 6,
						"config": "{}",
						"frozen_data": '{"value": 99}',
					},
				],
			}
		).insert()
		self.patches = [
			patch.object(audit, "_write"),
			# Audited refusals normally roll back the request. Keep test fixtures until tearDown.
			patch.object(frappe.db, "rollback"),
			patch.object(
				settings,
				"get_policy",
				return_value=Policy(
					enabled=True,
					read_enabled=True,
					grants={
						"synapse script": frozenset({"read"}),
						"synapse page": frozenset({"read"}),
						"synapse component": frozenset({"read"}),
					},
				),
			),
			patch("frappe.utils.safe_exec.is_safe_exec_enabled", return_value=True),
		]
		for item in self.patches:
			item.start()

	def tearDown(self):
		for item in reversed(self.patches):
			item.stop()
		frappe.set_user("Administrator")
		frappe.db.rollback()
		frappe.clear_cache(user=self.user)
		settings.clear_cache()

	def share(self, script=False):
		frappe.set_user("Administrator")
		frappe.share.add("Synapse Page", self.page.name, self.user, read=1, notify=0)
		if script:
			frappe.share.add("Synapse Script", self.script.name, self.user, read=1, notify=0)
		frappe.set_user(self.user)

	def test_private_pages_are_not_discovered_or_opened(self):
		frappe.set_user(self.user)
		self.assertTrue(api.has_desk_permission())
		self.assertNotIn(self.page.name, [row.name for row in api.list_dashboard_pages()])
		with self.assertRaises(frappe.PermissionError):
			api.get_page_layout(self.page.name)
		with self.assertRaises(frappe.PermissionError):
			api.get_page_block_data(self.page.name, self.page.blocks[0].name)

	def test_shared_page_is_discovered_without_admin_or_write_access(self):
		self.share()
		self.assertIn(self.page.name, [row.name for row in api.list_dashboard_pages()])
		model = api.get_page_layout(self.page.name, include_data=0)
		self.assertFalse(model["can_edit"])
		self.assertTrue(model["blocks"][0]["pending"])
		self.assertEqual(model["blocks"][1]["frozen_data"], {"value": 99})
		failed = api.get_page_block_data(self.page.name, self.page.blocks[0].name)
		self.assertTrue(failed["data_error"])
		self.assertEqual(failed["frozen_data"], {})

	def test_shared_script_retains_source_permissions_and_mcp_contract(self):
		self.share(script=True)
		data = api.get_page_block_data(self.page.name, self.page.blocks[0].name)
		self.assertFalse(data["data_error"])
		self.assertEqual(data["frozen_data"]["value"], len(api.list_dashboard_pages()))
		contract = get_dashboard_contract(component_type="number_card")
		self.assertTrue(contract["success"])
		self.assertEqual(len(contract["components"]), 1)
		result = validate_dashboard_component(
			component_type="number_card", config={}, data_script=self.script.name
		)
		self.assertTrue(result["success"], result)
		self.assertTrue(result["valid"])

	def test_profile_denial_still_blocks_shared_script(self):
		self.share(script=True)
		with patch.object(settings, "get_policy", return_value=Policy()):
			result = api.get_page_block_data(self.page.name, self.page.blocks[0].name)
			self.assertTrue(result["data_error"])
			self.assertEqual(result["frozen_data"], {})

	def test_block_cannot_be_fetched_through_another_page(self):
		self.share(script=True)
		with self.assertRaises(frappe.DoesNotExistError):
			api.get_page_block_data(self.page.name, "different-page-block")

	def test_disabled_pages_are_hidden_and_denied(self):
		self.page.enabled = 0
		self.page.save()
		self.share(script=True)
		self.assertNotIn(self.page.name, [row.name for row in api.list_dashboard_pages()])
		with self.assertRaises(frappe.PermissionError):
			api.get_page_layout(self.page.name)

	def test_save_and_preview_validate_the_same_data(self):
		self.page.blocks[1].frozen_data = json.dumps({"value": "invalid"})
		with self.assertRaises(frappe.ValidationError):
			self.page.save()
		with self.assertRaises(frappe.ValidationError):
			api.preview_component("number_card", "{}", self.page.blocks[1].frozen_data)

	def test_applying_script_configuration_does_not_execute_it(self):
		with patch.object(scripts, "run_script") as run:
			result = api.preview_component(
				"number_card",
				"{}",
				data_script=self.script.name,
				script_parameters='{"status":"Open"}',
				validate_only=1,
			)
			self.assertTrue(result["validated"])
			run.assert_not_called()
		with self.assertRaises(frappe.ValidationError):
			api.preview_component(
				"number_card", "{}", data_script=self.script.name, script_parameters="[]", validate_only=1
			)
