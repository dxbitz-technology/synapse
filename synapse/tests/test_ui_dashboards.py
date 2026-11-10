"""Rules for Synapse app dashboards: layout checks, filters and payload cleaning. No site needed."""

import unittest
from datetime import date, datetime
from unittest.mock import patch

import frappe

from synapse import dashboards as dash


def _throw(msg, *args, **kwargs):
	raise frappe.ValidationError(msg)


class Base(unittest.TestCase):
	def setUp(self):
		for patcher in (
			patch.object(frappe, "throw", side_effect=_throw),
			patch.object(dash, "_", side_effect=lambda s: s),
			patch.object(dash, "nowdate", return_value="2026-11-09"),
		):
			patcher.start()
			self.addCleanup(patcher.stop)


def layout(**extra):
	base = {
		"sections": [
			{
				"key": "kpi",
				"widgets": [
					{"key": "total", "type": "stat", "col": 3},
					{"key": "trend", "type": "line", "col": 30},
				],
			}
		]
	}
	base.update(extra)
	return base


class TestLinksAndPayloads(Base):
	def test_only_site_paths_anchors_and_http_links_pass(self):
		self.assertEqual(dash.safe_href("/app/sales-order/SO-1"), "/app/sales-order/SO-1")
		self.assertEqual(dash.safe_href("#/x"), "#/x")
		self.assertEqual(dash.safe_href("https://example.com/a"), "https://example.com/a")
		for bad in (
			"javascript:alert(1)",
			" JavaScript:alert(1)",
			"//evil.example",
			"data:text/html,x",
			None,
			5,
		):
			self.assertIsNone(dash.safe_href(bad), bad)

	def test_payload_cannot_carry_draw_options_or_script_links(self):
		dirty = {
			"w": {"data": [1, 2], "template": "<img src=x onerror=alert(1)>", "css": "*{}", "title": "ok"},
			"list": [{"title": "a", "href": "javascript:alert(1)", "render": "x"}],
		}
		clean = dash.sanitize(dirty)
		self.assertEqual(clean["w"], {"data": [1, 2], "title": "ok"})
		self.assertEqual(clean["list"], [{"title": "a", "href": None}])


class TestLayout(Base):
	def test_code_hooks_are_stripped_and_columns_clamped(self):
		out = dash.validate_layout(layout(method="frappe.client.delete", fetch="x", title="t"))
		self.assertNotIn("method", out)
		self.assertNotIn("fetch", out)
		self.assertEqual(out["sections"][0]["widgets"][1]["col"], 12)

	def test_bad_layouts_are_refused(self):
		cases = {
			"duplicate key": layout(
				sections=[{"widgets": [{"key": "a", "type": "stat"}, {"key": "a", "type": "bar"}]}]
			),
			"unknown type": layout(sections=[{"widgets": [{"key": "a", "type": "gauge"}]}]),
			"missing key": layout(sections=[{"widgets": [{"type": "stat"}]}]),
			"no sections": {"filters": []},
			"bad filter type": layout(filters=[{"key": "x", "type": "slider"}]),
			"select without options": layout(filters=[{"key": "x", "type": "select"}]),
			"duplicate filter": layout(filters=[{"key": "x", "type": "text"}, {"key": "x", "type": "date"}]),
		}
		for name, value in cases.items():
			with self.subTest(name), self.assertRaises(frappe.ValidationError):
				dash.validate_layout(value)

	def test_html_widgets_are_refused_on_assistant_dashboards(self):
		value = layout(sections=[{"widgets": [{"key": "h", "type": "html", "template": "<b>{{x}}</b>"}]}])
		with self.assertRaises(frappe.ValidationError):
			dash.validate_layout(value, assistant=True)

	def test_more_links_are_cleaned(self):
		value = layout(
			sections=[{"widgets": [{"key": "l", "type": "list", "more": {"href": "javascript:x"}}]}]
		)
		out = dash.validate_layout(value)
		self.assertIsNone(out["sections"][0]["widgets"][0]["more"]["href"])

	def test_report_layout_needs_no_sections(self):
		out = dash.validate_layout({"table": {"groupBy": "customer"}}, view_type="Report")
		self.assertEqual(out["table"], {"groupBy": "customer"})


class TestNesting(Base):
	def nested(self, depth, **leaf):
		section = {"key": f"s{depth}", "widgets": [{"key": f"w{depth}", "type": "stat"}], **leaf}
		for d in range(depth - 1, 0, -1):
			section = {"key": f"s{d}", "widgets": [{"key": f"w{d}", "type": "stat"}], "sections": [section]}
		return {"sections": [section]}

	def test_child_sections_are_checked_and_keys_found_at_every_depth(self):
		out = dash.validate_layout(self.nested(4))
		self.assertEqual(dash.widget_keys(out), ["w1", "w2", "w3", "w4"])

	def test_too_deep_or_duplicate_or_empty_child_is_refused(self):
		deep = self.nested(5)
		dup = {
			"sections": [
				{
					"widgets": [{"key": "a", "type": "stat"}],
					"sections": [{"widgets": [{"key": "a", "type": "bar"}]}],
				}
			]
		}
		empty_child = {
			"sections": [{"widgets": [{"key": "a", "type": "stat"}], "sections": [{"title": "x"}]}]
		}
		bad_child_widget = {"sections": [{"sections": [{"widgets": [{"key": "b", "type": "gauge"}]}]}]}
		for name, value in (("deep", deep), ("dup", dup), ("empty", empty_child), ("bad", bad_child_widget)):
			with self.subTest(name), self.assertRaises(frappe.ValidationError):
				dash.validate_layout(value)

	def test_section_may_hold_only_child_sections(self):
		value = {"sections": [{"title": "Sales", "sections": [{"widgets": [{"key": "a", "type": "stat"}]}]}]}
		self.assertEqual(dash.widget_keys(dash.validate_layout(value)), ["a"])

	def test_child_html_is_still_refused_on_assistant_pages(self):
		value = {"sections": [{"sections": [{"widgets": [{"key": "h", "type": "html", "template": "x"}]}]}]}
		with self.assertRaises(frappe.ValidationError):
			dash.validate_layout(value, assistant=True)

	def test_group_by_takes_a_key_or_a_short_list(self):
		ok = {"sections": [{"widgets": [{"key": "t", "type": "table", "groupBy": ["customer", "status"]}]}]}
		dash.validate_layout(ok)
		dash.validate_layout({"table": {"groupBy": ["customer", "status"]}}, view_type="Report")
		for bad in (["a", "b", "c", "d", "e"], [1], [""], {"x": 1}):
			with self.subTest(bad), self.assertRaises(frappe.ValidationError):
				dash.validate_layout({"table": {"groupBy": bad}}, view_type="Report")
		widget = {"sections": [{"widgets": [{"key": "t", "type": "list", "groupBy": [1, 2]}]}]}
		with self.assertRaises(frappe.ValidationError):
			dash.validate_layout(widget)


class TestDataSourceRules(Base):
	def test_assistant_pages_refuse_filters_and_queries(self):
		with_filter = layout(filters=[{"key": "p", "type": "daterange"}])
		with self.assertRaises(frappe.ValidationError):
			dash.validate_layout(with_filter, assistant=True)
		with_query = {"sections": [{"widgets": [{"key": "s", "type": "stat", "query": {"doctype": "X"}}]}]}
		with self.assertRaises(frappe.ValidationError):
			dash.validate_layout(with_query, assistant=True)

	def test_query_and_bind_must_be_objects(self):
		for w in ({"query": "Sales Invoice"}, {"query": {"doctype": "X"}, "bind": ["period"]}):
			value = {"sections": [{"widgets": [{"key": "s", "type": "stat", **w}]}]}
			with self.subTest(w), self.assertRaises(frappe.ValidationError):
				dash.validate_layout(value)

	def test_bound_filters_turn_into_field_conditions(self):
		lay = {
			"filters": [
				{"key": "period", "type": "daterange"},
				{"key": "c", "type": "link"},
				{"key": "x", "type": "text"},
			]
		}
		out = dash._bound_filters(
			lay,
			{"period": "posting_date", "c": "customer", "x": "remarks"},
			{"period": ["2026-01-01", "2026-01-31"], "c": "A", "x": ""},
		)
		self.assertEqual(out, {"posting_date": ["between", ["2026-01-01", "2026-01-31"]], "customer": "A"})

	def test_text_filters_bound_to_erp_fields_become_pickers(self):
		lay = {
			"filters": [
				{"key": "sp", "type": "text"},
				{"key": "st", "type": "text"},
				{"key": "keep", "type": "date"},
			]
		}
		dash._upgrade_filter(lay, "sp", ("Link", "Sales Person", "Sales Team"))
		dash._upgrade_filter(lay, "st", ("Select", "Draft\nPaid\n\nOverdue", None))
		dash._upgrade_filter(lay, "keep", ("Link", "Customer", None))
		self.assertEqual(lay["filters"][0], {"key": "sp", "type": "link", "doctype": "Sales Person"})
		self.assertEqual(
			lay["filters"][1], {"key": "st", "type": "select", "options": ["Draft", "Paid", "Overdue"]}
		)
		self.assertEqual(lay["filters"][2], {"key": "keep", "type": "date"})

	def test_refresh_is_due_by_interval(self):
		with patch("frappe.utils.now_datetime", return_value=datetime(2026, 11, 9, 12, 0)):
			page = {"data_mode": "Assistant", "llm_refresh": "Week"}
			self.assertTrue(dash.refresh_due(page))  # never published
			self.assertTrue(dash.refresh_due({**page, "llm_updated_on": "2026-11-01 12:00:00"}))
			self.assertFalse(dash.refresh_due({**page, "llm_updated_on": "2026-11-05 12:00:00"}))
			self.assertFalse(
				dash.refresh_due({**page, "llm_refresh": "On Request", "llm_updated_on": "2020-01-01"})
			)
			self.assertFalse(dash.refresh_due({"data_mode": "Query"}))

	def test_queries_never_reach_the_browser(self):
		lay = {
			"query": {"doctype": "X"},
			"sections": [
				{"widgets": [{"key": "s", "type": "stat", "query": {"doctype": "X"}, "bind": {"a": "b"}}]}
			],
		}
		dash._strip_queries(lay)
		self.assertNotIn("query", lay)
		self.assertEqual(lay["sections"][0]["widgets"][0], {"key": "s", "type": "stat"})


class TestFilters(Base):
	def test_presets_resolve_like_the_browser(self):
		today = date(2026, 11, 9)
		self.assertEqual(dash.preset_range("this_month", today), ["2026-11-01", "2026-11-30"])
		self.assertEqual(dash.preset_range("last_quarter", today), ["2026-07-01", "2026-09-30"])
		self.assertEqual(dash.preset_range("this_quarter", today), ["2026-10-01", "2026-12-31"])
		self.assertEqual(dash.preset_range("last_month", date(2026, 1, 15)), ["2025-12-01", "2025-12-31"])
		self.assertEqual(dash.preset_range("last_quarter", date(2026, 2, 1)), ["2025-10-01", "2025-12-31"])
		self.assertEqual(dash.preset_range("last_7", today), ["2026-11-03", "2026-11-09"])

	def test_scripts_get_only_defined_keys_with_clean_values(self):
		lay = {
			"filters": [
				{"key": "period", "type": "daterange", "default": "this_year"},
				{
					"key": "status",
					"type": "select",
					"options": ["Open", {"value": "Closed", "label": "Done"}],
				},
				{"key": "mine", "type": "check"},
				{"key": "n", "type": "number"},
			]
		}
		out = dash.clean_filters(lay, {"status": "Closed", "mine": "1", "n": "4.5", "extra": "drop me"})
		self.assertEqual(
			out, {"period": ["2026-01-01", "2026-12-31"], "status": "Closed", "mine": 1, "n": 4.5}
		)
		self.assertEqual(
			dash.clean_filters(lay, {"period": "2026-02-01,2026-02-28"})["period"],
			["2026-02-01", "2026-02-28"],
		)

	def test_bad_filter_values_are_refused(self):
		lay = {
			"filters": [
				{"key": "period", "type": "daterange"},
				{"key": "status", "type": "select", "options": ["Open"]},
			]
		}
		for value in ({"status": "Nope"}, {"period": ["x", "y"]}, {"period": ["2026-01-01"]}):
			with self.subTest(value), self.assertRaises(frappe.ValidationError):
				dash.clean_filters(lay, value)


if __name__ == "__main__":
	unittest.main()


class TestSandboxHints(unittest.TestCase):
	def test_underscore_keys_get_a_plain_fix(self):
		from synapse import scripts

		hint = scripts._sandbox_hint(SyntaxError("Key starts with _"))
		self.assertIn("start with _", hint)
		self.assertIsNone(scripts._sandbox_hint(SyntaxError("invalid syntax")))
