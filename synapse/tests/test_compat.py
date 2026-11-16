"""Frappe 15 and 16 differences: aggregate columns and version switches."""

import unittest
from unittest import mock

import frappe

from synapse import compat


class TestAggregateField(unittest.TestCase):
	def test_v16_gets_dict_columns(self):
		with mock.patch.object(frappe, "__version__", "16.22.0"):
			self.assertEqual(compat.aggregate_field("count", "*", "__n"), {"COUNT": "*", "as": "__n"})
			self.assertEqual(compat.aggregate_field("COUNT", "name"), {"COUNT": "name"})

	def test_v15_gets_string_columns(self):
		with mock.patch.object(frappe, "__version__", "15.126.1"):
			self.assertEqual(compat.aggregate_field("COUNT", "*", "__n"), "count(*) as `__n`")
			self.assertEqual(
				compat.aggregate_field("sum", "grand_total", "__sum_grand_total", "Sales Invoice"),
				"sum(`tabSales Invoice`.`grand_total`) as `__sum_grand_total`",
			)
			self.assertEqual(compat.aggregate_field("COUNT", "name"), "count(`name`)")

	@unittest.skipIf(compat.frappe_major_version() >= 16, "v16 refuses string aggregates")
	def test_v15_aggregate_runs_against_this_database(self):
		# The CI job on a Frappe 15 bench runs the real query.
		rows = frappe.get_list(
			"User",
			fields=["user_type", compat.aggregate_field("COUNT", "*", "__n")],
			group_by="`tabUser`.`user_type`",
		)
		self.assertTrue(rows and "__n" in rows[0])
