"""The aggregate engine's pure parts: metrics, buckets, folding and widget shapes. No Frappe needed."""

import unittest
from datetime import date, datetime

from synapse import aggregate as agg


class TestMetrics(unittest.TestCase):
	def test_metric_text_becomes_function_field_and_column(self):
		self.assertEqual(agg.parse_metric("count"), ("count", None, "count"))
		self.assertEqual(
			agg.parse_metric("SUM: base_grand_total"), ("sum", "base_grand_total", "sum_base_grand_total")
		)
		self.assertEqual(agg.parse_metric("avg:qty"), ("avg", "qty", "avg_qty"))

	def test_bad_metrics_say_what_to_write(self):
		for bad in ("total:qty", "sum", "", "median:qty"):
			with self.subTest(bad), self.assertRaises(agg.SpecError):
				agg.parse_metric(bad)


class TestBuckets(unittest.TestCase):
	def test_every_period(self):
		d = date(2026, 8, 5)
		self.assertEqual(agg.bucket(d, "day"), "2026-08-05")
		self.assertEqual(agg.bucket(d, "week"), "2026-W32")
		self.assertEqual(agg.bucket(d, "month"), "2026-08")
		self.assertEqual(agg.bucket(d, "quarter"), "2026-Q3")
		self.assertEqual(agg.bucket(d, "year"), "2026")

	def test_datetimes_strings_and_blanks(self):
		self.assertEqual(agg.bucket(datetime(2026, 12, 31, 23, 59), "month"), "2026-12")
		self.assertEqual(agg.bucket("2026-01-01 10:00:00", "quarter"), "2026-Q1")
		self.assertEqual(agg.bucket(None, "month"), "(Not set)")

	def test_iso_week_crosses_the_year(self):
		self.assertEqual(agg.bucket(date(2027, 1, 1), "week"), "2026-W53")


class TestFold(unittest.TestCase):
	METRICS = (
		("count", None, "count"),
		("sum", "amt", "sum_amt"),
		("avg", "amt", "avg_amt"),
		("max", "amt", "max_amt"),
	)

	def rows(self):
		# what the database returns when grouped by customer and day
		return [
			{"customer": "A", "d": date(2026, 8, 1), "__n": 2, "__sum_amt": 100, "__max_amt": 70},
			{"customer": "A", "d": date(2026, 8, 20), "__n": 1, "__sum_amt": 50, "__max_amt": 50},
			{"customer": "A", "d": date(2026, 9, 2), "__n": 1, "__sum_amt": 10, "__max_amt": 10},
			{"customer": "B", "d": date(2026, 8, 3), "__n": 3, "__sum_amt": 30, "__max_amt": 20},
		]

	def test_days_fold_into_months_with_exact_average(self):
		out = {
			(r["customer"], r["period"]): r
			for r in agg.fold(self.rows(), ["customer"], "d", "month", self.METRICS)
		}
		a_aug = out[("A", "2026-08")]
		self.assertEqual((a_aug["count"], a_aug["sum_amt"], a_aug["max_amt"]), (3, 150, 70))
		self.assertEqual(a_aug["avg_amt"], 50)
		self.assertEqual(out[("A", "2026-09")]["count"], 1)
		self.assertEqual(len(out), 3)

	def test_no_groups_gives_one_total(self):
		out = agg.fold(self.rows(), [], None, None, self.METRICS)
		self.assertEqual(out, [{"count": 7, "sum_amt": 190, "avg_amt": round(190 / 7, 6), "max_amt": 70}])

	def test_sorting_by_column_and_bad_column(self):
		rows = [{"c": "A", "s": 1}, {"c": "B", "s": 3}, {"c": "C", "s": None}]
		self.assertEqual([r["c"] for r in agg.sort_rows(rows, "s desc", None, False)], ["B", "A", "C"])
		with self.assertRaises(agg.SpecError):
			agg.sort_rows(rows, "nope desc", None, False)


class TestShape(unittest.TestCase):
	def spec(self, group_by=(), period=None):
		return {
			"_metrics": [("sum", "amt", "sum_amt"), ("count", None, "count")],
			"_group_by": list(group_by),
			"_period_field": "d" if period else None,
			"_period_by": period,
			"_label": group_by[0] if group_by else ("period" if period else None),
			"_labels": {"customer": "Customer", "amt": "Amount"},
		}

	def test_stat_sums_first_metric_and_adds_spark_by_period(self):
		rows = [
			{"period": "2026-09", "sum_amt": 5, "count": 1},
			{"period": "2026-08", "sum_amt": 10, "count": 2},
		]
		self.assertEqual(agg.shape("stat", rows, self.spec(period="month")), {"value": 15, "spark": [10, 5]})
		self.assertEqual(agg.shape("stat", rows[:1], self.spec()), {"value": 5})

	def test_list_uses_first_group_and_first_metric(self):
		rows = [{"customer": "A", "status": "Paid", "sum_amt": 9, "count": 1}]
		out = agg.shape("list", rows, self.spec(group_by=("customer", "status")))
		self.assertEqual(out, [{"title": "A", "value": 9, "subtitle": "Paid"}])

	def test_table_has_labelled_columns(self):
		out = agg.shape(
			"table", [{"customer": "A", "sum_amt": 9, "count": 1}], self.spec(group_by=("customer",))
		)
		self.assertEqual([c["label"] for c in out["columns"]], ["Customer", "Sum of Amount", "Count"])

	def test_charts_get_rows_unchanged(self):
		rows = [{"customer": "A", "sum_amt": 9, "count": 1}]
		self.assertIs(agg.shape("bar", rows, self.spec(group_by=("customer",))), rows)


if __name__ == "__main__":
	unittest.main()
