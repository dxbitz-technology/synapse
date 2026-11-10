"""The script run budget. No Frappe needed."""

import unittest

from synapse.run_budget import Budget, BudgetExceeded


class Clock:
	def __init__(self):
		self.now = 0.0

	def __call__(self):
		return self.now


class TestBudget(unittest.TestCase):
	def test_paging_with_offset_is_stopped_by_call_count(self):
		budget = Budget(queries=3)
		for _ in range(3):
			budget.before_call()
		with self.assertRaises(BudgetExceeded) as caught:
			budget.before_call()
		self.assertIn("OFFSET", str(caught.exception))

	def test_rows_add_up_across_calls(self):
		budget = Budget(rows=150)
		budget.after_call([{}] * 100)
		with self.assertRaises(BudgetExceeded):
			budget.after_call([{}] * 100)

	def test_time_runs_out_and_returns_seconds_left(self):
		clock = Clock()
		budget = Budget(seconds=10, clock=clock)
		clock.now = 4
		self.assertEqual(budget.before_call(), 6)
		clock.now = 11
		with self.assertRaises(BudgetExceeded):
			budget.before_call()

	def test_a_caught_stop_keeps_stopping(self):
		budget = Budget(queries=1)
		budget.before_call()
		try:
			budget.before_call()
		except BudgetExceeded:
			pass
		self.assertTrue(budget.stopped)
		with self.assertRaises(BudgetExceeded):
			budget.before_call()

	def test_scripts_cannot_swallow_it_with_except_exception(self):
		self.assertFalse(issubclass(BudgetExceeded, Exception))


if __name__ == "__main__":
	unittest.main()
