# Copyright (c) 2026, Dxbitz and contributors
"""The Synapse Log, one row for every call, read or write, allowed or not."""

import contextlib
import functools
import json
import re
import time

import frappe

from synapse.mcp_tools.policy import Denied

LOG_DOCTYPE = "Synapse Log"

READ = "Read"
WRITE = "Write"
OPERATE = "Operate"
CUSTOM = "Custom"
SQL = "SQL"
OTHER = "Other"

MAX_QUERY_CHARS = 10000
MAX_JSON_CHARS = 4000
MAX_REASON_CHARS = 500

_ENTRY_KEY = "_synapse_mcp_entry"


class AuditError(RuntimeError):
	"""The call could not be recorded and its transaction was rolled back."""


_SECRET_RE = re.compile(r"password|passwd|pwd|secret|token|api_key|apikey|private_key", re.I)
_REDACTED = "***"

_TAG_RE = re.compile(r"<[^>]+>")


class Entry:
	"""The row being built for the current tool call."""

	def __init__(self, tool: str, kind: str):
		self.tool = tool
		self.kind = kind
		self.status = "Success"
		self.reason = None
		self.reference_doctype = None
		self.reference_name = None
		self.row_count = 0
		self.query = None
		self.payload = None
		self.changes = None
		self.started = time.monotonic()

	def target(self, doctype=None, name=None):
		if doctype:
			self.reference_doctype = doctype
		if name:
			self.reference_name = str(name)[:140]

	def rows(self, count: int):
		self.row_count = int(count or 0)

	def sql(self, query: str):
		"""The SQL text. Gated by log_payloads like every other field value."""
		from synapse.mcp_tools import settings

		try:
			if not settings.log_payloads():
				return
		except Exception:
			pass

		self.query = str(query)[:MAX_QUERY_CHARS]

	def sent(self, values, secret_keys=None):
		"""What the caller asked for. Redacted, truncated, stored as JSON.

		secret_keys names the Password-fieldtype fields of the target DocType, so
		a secret is masked by field type even when its key does not look like one
		(the regex alone misses a Password field named, say, `pin` or `access`).
		"""
		self.payload = _json(values, secret_keys)

	def changed(self, before_after, secret_keys=None):
		"""Field-level before/after for a write. Same treatment as sent()."""
		self.changes = _json(before_after, secret_keys)


def current() -> Entry | None:
	"""The Entry for the call in progress, or None outside a tool."""
	return getattr(frappe.local, _ENTRY_KEY, None)


def audited(kind: str, tool: str | None = None):
	"""Wrap a tool: log it, shape its result, own its transaction."""

	def decorator(fn):
		name = tool or fn.__name__

		@functools.wraps(fn)
		def wrapper(**kwargs):
			entry = Entry(name, kind)
			setattr(frappe.local, _ENTRY_KEY, entry)

			try:
				result = fn(**kwargs)
			except Denied as e:
				return _fail(entry, "Rejected", str(e))
			except frappe.PermissionError as e:
				detail = str(e) or getattr(frappe.flags, "error_message", None)
				return _fail(entry, "Rejected", _clean(detail) or "Not permitted.")
			except Exception as e:
				_log_traceback(name)
				return _fail(entry, "Error", _one_line(e))
			else:
				_write(entry)
				return {"success": True, **(result or {})}
			finally:
				_clear()

		wrapper._mcp_kind = kind
		return wrapper

	return decorator


def refused(tool, reason: str, kind: str | None = None) -> None:
	"""Log a call the server turned away before the tool body ran."""

	entry = Entry(str(tool or "unknown")[:140], kind or OTHER)
	entry.status = "Rejected"
	entry.reason = str(reason)[:MAX_REASON_CHARS]
	_write(entry)


def _fail(entry: Entry, status: str, reason: str) -> dict:
	with contextlib.suppress(Exception):
		frappe.db.rollback()

	entry.status = status
	entry.reason = reason[:MAX_REASON_CHARS]
	_write(entry)

	return {"success": False, "error": reason}


def _write(entry: Entry):
	"""Commit the tool's changes and log together, or roll both back."""

	try:
		doc = frappe.new_doc(LOG_DOCTYPE)
		doc.update(
			{
				"user": getattr(frappe.session, "user", None) or "Guest",
				"tool": entry.tool,
				"kind": entry.kind,
				"status": entry.status,
				"reason": entry.reason,
				"reference_doctype": entry.reference_doctype,
				"reference_name": entry.reference_name,
				"row_count": entry.row_count,
				"execution_time": round(time.monotonic() - entry.started, 4),
				"query": entry.query,
				"payload": entry.payload,
				"changes": entry.changes,
				"ip_address": getattr(frappe.local, "request_ip", None),
				"credential": _credential(),
			}
		)
		doc.db_insert()
		frappe.db.commit()  # nosemgrep: tool changes and their audit record share this transaction
	except Exception:
		frappe.db.rollback()
		_log_traceback("access log write")
		raise AuditError("The audit record could not be saved. The call was rolled back.") from None


def _clear():
	if hasattr(frappe.local, _ENTRY_KEY):
		delattr(frappe.local, _ENTRY_KEY)


def _credential() -> str:
	"""How this request authenticated. Useful when an OAuth grant has to be traced."""

	try:
		header = frappe.get_request_header("Authorization") or ""
	except Exception:
		return "Unknown"

	if header.lower().startswith("bearer "):
		return "OAuth"
	if header.lower().startswith("token "):
		return "API Key"

	return "Session"


def _json(value, secret_keys=None) -> str | None:
	from synapse.mcp_tools import settings

	if value is None:
		return None

	try:
		if not settings.log_payloads():
			return None
	except Exception:
		pass

	secrets = frozenset(k.lower() for k in (secret_keys or ()))

	try:
		text = json.dumps(redact(value, secrets), default=str, indent=1)
	except Exception:
		text = str(value)

	if len(text) > MAX_JSON_CHARS:
		text = text[:MAX_JSON_CHARS] + "\n... truncated"

	return text


def redact(value, secret_keys=frozenset()):
	"""Recursively blank anything whose key looks like, or is, a credential.

	A key is masked if it matches the credential-name pattern, or if it is one of
	`secret_keys` (the caller's Password-fieldtype field names). The second path
	is what catches a Password field whose name the pattern would miss.
	"""

	if isinstance(value, dict):
		return {
			k: (_REDACTED if _is_secret(k, secret_keys) else redact(v, secret_keys)) for k, v in value.items()
		}

	if isinstance(value, (list, tuple)):
		return [redact(v, secret_keys) for v in value]

	return value


def _is_secret(key, secret_keys) -> bool:
	key = str(key).lower()
	return bool(_SECRET_RE.search(key)) or key in secret_keys or key.rsplit(".", 1)[-1] in secret_keys


def _one_line(e: Exception) -> str:
	message = _clean(str(e)).splitlines()
	message = message[0] if message else e.__class__.__name__
	return f"{type(e).__name__}: {message}"[:MAX_REASON_CHARS]


def _clean(text) -> str:
	"""One line of plain text. Frappe messages carry markup and links.

	Both the log and the model get this string, and neither is helped by
	`<strong>` or a desk URL in the middle of a sentence.
	"""

	if not text:
		return ""

	text = _TAG_RE.sub("", str(text))
	return " ".join(text.split())[:MAX_REASON_CHARS]


def _log_traceback(label: str):
	with contextlib.suppress(Exception):
		frappe.log_error(title=f"MCP: {label}"[:140], message=frappe.get_traceback())
