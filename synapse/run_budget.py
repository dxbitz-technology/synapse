"""A spending limit for one Synapse Script run. No Frappe import, so it tests without a site.

A script may call query, get_list, get_count and aggregate as often as it likes, but
every call is charged here. When the run goes over its queries, rows or seconds, it
stops with a plain message instead of holding a web worker and the database.
"""

import time

DEFAULTS = {"queries": 200, "rows": 50000, "seconds": 30}
# A queued run does not hold a web worker, so it may take longer.
QUEUED_SECONDS = 120


class BudgetExceeded(BaseException):
	"""BaseException, so a script's `except Exception` cannot swallow it."""


class Budget:
	def __init__(self, queries=None, rows=None, seconds=None, clock=time.monotonic):
		self.max_queries = int(queries or DEFAULTS["queries"])
		self.max_rows = int(rows or DEFAULTS["rows"])
		self.max_seconds = float(seconds or DEFAULTS["seconds"])
		self.clock = clock
		self.started = clock()
		self.queries = 0
		self.rows = 0
		self.stopped = None
		self.statement_seconds = 15

	def stop(self, message):
		self.stopped = self.stopped or message
		raise BudgetExceeded(self.stopped)

	def rows_left(self) -> int:
		"""Rows one call may fetch: what is left, plus one so going over is noticed."""
		return max(1, self.max_rows - self.rows + 1)

	def cost(self) -> dict:
		seconds = round(min(self.clock() - self.started, 10**6), 2)
		return {
			"data_calls": self.queries,
			"rows_read": self.rows,
			"seconds": seconds,
			"limits": {
				"data_calls": self.max_queries,
				"rows_read": self.max_rows,
				"seconds": self.max_seconds,
			},
		}

	def advice(self) -> list[str]:
		"""Plain warnings once a run uses half of any limit, so it gets fixed before it fails."""
		out = []
		if self.queries > self.max_queries / 2:
			out.append(
				f"{self.queries} data calls. Combine queries: one GROUP BY query can return every month or company at once."
			)
		if self.rows > self.max_rows / 2:
			out.append(
				f"{self.rows} rows read. Group and sum in SQL so the script receives summary rows, not raw records."
			)
		if self.clock() - self.started > self.max_seconds / 2:
			out.append(
				"Slow run. Filter on indexed fields (company, posting_date, docstatus), avoid functions on columns in WHERE, and drop ORDER BY you do not need."
			)
		return out

	def remaining(self) -> float:
		return self.max_seconds - (self.clock() - self.started)

	def before_call(self) -> float:
		"""Charge one call. Returns the seconds left, for the statement timeout."""
		if self.stopped:
			raise BudgetExceeded(self.stopped)
		self.queries += 1
		if self.queries > self.max_queries:
			self.stop(
				f"it made more than {self.max_queries} data calls. Paging through rows with "
				"LIMIT and OFFSET is the usual cause. Group and sum in SQL instead, so each "
				"call returns a few summary rows."
			)
		left = self.remaining()
		if left <= 0:
			self.stop(
				f"it ran longer than {int(self.max_seconds)} seconds. Group and sum in SQL, "
				"and narrow the date range."
			)
		return left

	def after_call(self, rows) -> None:
		self.rows += len(rows or ())
		if self.rows > self.max_rows:
			self.stop(
				f"it read more than {self.max_rows} rows in total. Group and sum in SQL "
				"instead of reading raw rows into the script."
			)
