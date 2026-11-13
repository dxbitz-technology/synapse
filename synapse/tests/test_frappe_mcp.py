"""Synapse dashboard methods as Frappe's own MCP server calls them."""

import unittest
from unittest.mock import patch

import frappe

from synapse import api, frappe_mcp
from synapse.mcp_tools import settings


class TestFrappeMcp(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		settings.clear_cache()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_guide_works_without_any_synapse_profile(self):
		with patch.object(frappe, "get_all", wraps=frappe.get_all) as get_all:
			result = frappe_mcp.get_dashboard_guide()
		self.assertTrue(result["success"])
		self.assertTrue(result["your_access"]["save_dashboards"])
		self.assertIn("on_frappe_mcp", result)
		self.assertEqual(
			result["on_frappe_mcp"]["tools"]["save_dashboard"],
			"call_method synapse.frappe_mcp.save_dashboard",
		)
		# Profiles are never read on this path.
		self.assertFalse(any(c.args[:1] == ("Synapse Profile",) for c in get_all.call_args_list))

	def test_policy_is_put_back_after_a_call(self):
		frappe_mcp.list_dashboards()
		self.assertFalse(hasattr(frappe.local, settings.CACHE_KEY))

	def test_aggregate_reads_through_frappe_permissions(self):
		result = frappe_mcp.aggregate("User", metrics='["count"]')
		self.assertTrue(result["success"])
		self.assertGreaterEqual(result["rows"][0]["count"], 1)

	def test_control_plane_stays_blocked(self):
		result = frappe_mcp.aggregate("Synapse Settings")
		self.assertFalse(result["success"])

	def test_guests_are_turned_away(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			frappe_mcp.list_dashboards()

	def test_save_needs_write_on_synapse_page(self):
		frappe.set_user("Guest")
		with patch.object(frappe, "only_for"):
			result = frappe_mcp.get_dashboard_guide()
		self.assertFalse(result.get("your_access", {}).get("save_dashboards", False))

	def test_copy_link_is_frappes_endpoint(self):
		with patch.object(frappe_mcp, "available", return_value=True):
			self.assertEqual(api.endpoint_url(), frappe.utils.get_url("/api/v2/mcp"))
			context = api.connect_context()
		self.assertTrue(context["covered"])
		self.assertTrue(context["endpoint"].endswith("/api/v2/mcp"))

	def test_no_link_when_frappe_mcp_is_off(self):
		with (
			patch.object(frappe_mcp, "available", return_value=False),
			patch.object(api, "user_is_covered", return_value=False),
		):
			self.assertIsNone(api.endpoint_url())

	def test_agent_note_is_added_once(self):
		if not frappe.get_meta("System Settings").has_field("agent_instructions"):
			self.skipTest("This Frappe has no Agent Instructions field.")
		with patch("importlib.util.find_spec", return_value=object()):
			frappe_mcp.add_agent_note()
			frappe_mcp.add_agent_note()
		value = frappe.db.get_single_value("System Settings", "agent_instructions")
		self.assertEqual(value.count(frappe_mcp.AGENT_NOTE_MARKER), 1)
