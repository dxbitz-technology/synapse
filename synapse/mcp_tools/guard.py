# Copyright (c) 2026, Dxbitz and contributors
"""Read-only validation for SQL submitted through the MCP endpoint."""

import re

from synapse.mcp_tools.policy import ALWAYS_DENIED

__all__ = ["BLOCKED_KEYWORDS", "BLOCKED_TABLES", "MAX_QUERY_LENGTH", "UnsafeQuery", "validate_read_only"]


MAX_QUERY_LENGTH = 5000

BLOCKED_KEYWORDS = (
	"insert",
	"update",
	"delete",
	"drop",
	"alter",
	"create",
	"truncate",
	"rename",
	"grant",
	"revoke",
	"replace",
	"call",
	"do",
	"handler",
	"load",
	"lock",
	"unlock",
	"set",
	"commit",
	"rollback",
	"savepoint",
	"start",
	"begin",
	"prepare",
	"execute",
	"deallocate",
	"analyze",
	"optimize",
	"repair",
	"flush",
	"kill",
	"shutdown",
	"sleep",
	"benchmark",
	"get_lock",
	"release_lock",
	"release_all_locks",
	"is_free_lock",
	"is_used_lock",
	"outfile",
	"dumpfile",
	"load_file",
	"into",
)

BLOCKED_TABLES = ("__auth", *(f"tab{name}" for name in sorted(ALWAYS_DENIED)))

_COMMENT_MARKERS = ("--", "#", "/*", "*/")

_KEYWORD_RE = re.compile(r"\b(?:" + "|".join(BLOCKED_KEYWORDS) + r")\b", re.IGNORECASE)

_LEADING_NOISE_RE = re.compile(r"^[\s(]+")

_ALLOWED_STATEMENTS = ("select", "with")


class UnsafeQuery(Exception):
	"""Raised when a submitted query fails one of the read-only rules.

	The message names the rule that fired, the caller hands it straight back to
	the model, which needs enough to correct itself on the next attempt.
	"""


def validate_read_only(query: str, extra_blocked_tables: tuple | list | None = None) -> str:
	"""Return the normalised query, or raise UnsafeQuery naming the rule that fired.

	Normalising means: outer whitespace trimmed and a single trailing semicolon
	removed. Nothing inside the statement is rewritten.
	"""

	if not isinstance(query, str):
		raise UnsafeQuery("Rule 'type': query must be a string.")

	stripped = query.strip()

	if not stripped:
		raise UnsafeQuery("Rule 'empty': query is empty.")

	if len(stripped) > MAX_QUERY_LENGTH:
		raise UnsafeQuery(
			f"Rule 'length': query is {len(stripped)} characters, the limit is {MAX_QUERY_LENGTH}."
		)

	for marker in _COMMENT_MARKERS:
		if marker in stripped:
			raise UnsafeQuery(
				f"Rule 'comment': query contains '{marker}'. Comments are not allowed, resubmit without them."
			)

	body = stripped[:-1].rstrip() if stripped.endswith(";") else stripped
	if ";" in body:
		raise UnsafeQuery(
			"Rule 'single statement': ';' may only appear as the final character. "
			"Submit one statement per call."
		)

	if not body:
		raise UnsafeQuery("Rule 'empty': query is empty.")

	head = _LEADING_NOISE_RE.sub("", body).lower()
	if not head.startswith(_ALLOWED_STATEMENTS):
		first_word = (head.split(None, 1) or [""])[0] or "?"
		raise UnsafeQuery(
			f"Rule 'statement type': query starts with '{first_word}'. Only SELECT and WITH are permitted."
		)

	if match := _KEYWORD_RE.search(body):
		raise UnsafeQuery(
			f"Rule 'keyword': query contains the blocked keyword '{match.group(0)}'. "
			"Note this also fires on identifiers containing the word."
		)

	lowered = body.lower()
	for table in _blocked_tables(extra_blocked_tables):
		if table in lowered:
			raise UnsafeQuery(f"Rule 'table': '{table}' is not readable through this tool.")

	return body


def _blocked_tables(extra: tuple | list | None) -> tuple:
	if not extra:
		return BLOCKED_TABLES

	extra_lowered = tuple(str(t).strip().lower() for t in extra if str(t).strip())
	return BLOCKED_TABLES + extra_lowered
