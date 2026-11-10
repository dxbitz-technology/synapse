"""Plain messages for safe exec errors. No Frappe needed."""

import unittest

from synapse.sandbox_hints import sandbox_hint


class TestSandboxHints(unittest.TestCase):
	def test_underscore_keys_get_a_plain_fix(self):
		self.assertIn("start with _", sandbox_hint(SyntaxError("Key starts with _")))

	def test_other_errors_are_left_alone(self):
		self.assertIsNone(sandbox_hint(SyntaxError("invalid syntax")))


if __name__ == "__main__":
	unittest.main()
