# Copyright (c) 2026, Dxbitz and contributors
"""The Synapse access model: which DocTypes may be touched, and how."""

from dataclasses import dataclass, field

__all__ = [
	"ACTIONS",
	"ALWAYS_DENIED",
	"ALWAYS_READ_ONLY",
	"CANCEL",
	"DELETE",
	"OPERATE",
	"READ",
	"SUBMIT",
	"WRITE",
	"WRITE_ACTIONS",
	"Denied",
	"Policy",
	"actions_possible",
	"check",
]

READ = "read"
WRITE = "write"
SUBMIT = "submit"
CANCEL = "cancel"
DELETE = "delete"
OPERATE = "operate"

ACTIONS = (READ, WRITE, SUBMIT, CANCEL, DELETE, OPERATE)

WRITE_ACTIONS = (WRITE, SUBMIT, CANCEL, DELETE, OPERATE)

ALWAYS_DENIED = frozenset(
	{
		"oauth bearer token",
		"oauth authorization code",
		"oauth client",
		"token cache",
		"social login key",
		"connected app",
		"webhook",
		"email account",
		"integration request",
		"user social login",
		"access log",
		"synapse settings",
		"synapse profile",
		"synapse profile role",
		"synapse profile tool",
		"synapse doctype access",
		"synapse denied doctype",
		"synapse log",
	}
)

ALWAYS_READ_ONLY = frozenset(
	{
		"doctype",
		"docfield",
		"docperm",
		"custom docperm",
		"custom field",
		"property setter",
		"server script",
		"client script",
		"print format",
		"report",
		"role",
		"has role",
		"user",
		"user permission",
		"system settings",
		"workflow",
		"scheduled job type",
		"synapse component",
	}
)


class Denied(Exception):
	"""Raised when the access gate refuses an operation.

	The message names the gate that closed. It goes straight back to the model,
	which needs to know whether to give up or try a different DocType.
	"""


@dataclass(frozen=True)
class Policy:
	"""A snapshot of the caller's resolved access, in a form that needs no database."""

	enabled: bool = False
	read_enabled: bool = False
	write_enabled: bool = False
	sql_enabled: bool = False
	custom_enabled: bool = False
	full_access: bool = False
	config_writer: bool = False
	grants: dict[str, frozenset] = field(default_factory=dict)
	grant_names: dict[str, str] = field(default_factory=dict)
	denied: dict[str, frozenset] = field(default_factory=dict)
	custom_tools: frozenset = field(default_factory=frozenset)

	def granted_actions(self, doctype: str) -> frozenset:
		"""Actions the caller's profiles grant on a DocType, before the backstop."""

		if self.full_access:
			return frozenset(ACTIONS)

		return self.grants.get(_norm(doctype), frozenset())

	def blocked_actions(self, doctype: str) -> frozenset:
		"""Every action the backstop blocks on a DocType, built-ins included."""

		wanted = _norm(doctype)
		blocked = set(self.denied.get(wanted, frozenset()))

		if wanted in ALWAYS_DENIED:
			blocked |= set(ACTIONS)

		if wanted in ALWAYS_READ_ONLY:
			if self.config_writer:
				blocked |= set(WRITE_ACTIONS) - {WRITE}
			else:
				blocked |= set(WRITE_ACTIONS)

		return frozenset(blocked)


def check(policy: Policy, action: str, doctype: str) -> str:
	"""Return the DocType name, or raise Denied naming the gate that closed.

	Args:
	        policy: The caller's resolved access for this request.
	        action: One of ACTIONS.
	        doctype: The target DocType. Callers pass the name Frappe resolved, so
	                capitalisation is already canonical; matching here is still case
	                insensitive rather than trusting that."""

	if action not in ACTIONS:
		raise Denied(f"Unknown action '{action}'.")

	if not policy.enabled:
		raise Denied("Synapse access is switched off for this site (Synapse Settings).")

	if action == READ and not policy.read_enabled:
		raise Denied("Synapse read tools are switched off for this site (Synapse Settings).")

	if action != READ and not policy.write_enabled:
		raise Denied("Synapse write tools are switched off for this site (Synapse Settings).")

	if not doctype or not isinstance(doctype, str):
		raise Denied("A DocType is required.")

	if action in policy.blocked_actions(doctype):
		raise Denied(f"'{doctype}' is blocked for '{action}' by this site's Synapse backstop.")

	if action not in policy.granted_actions(doctype):
		raise Denied(
			f"None of your Synapse profiles grant '{action}' on '{doctype}'. "
			"A System Manager grants this in a Synapse Profile."
		)

	return doctype


def actions_possible(policy: Policy) -> tuple:
	"""The actions the switches allow at all, ignoring any DocType.

	Used by list_available_doctypes in full-access mode, where enumerating every
	reachable DocType would mean returning the site's whole schema.
	"""

	possible = []

	for action in ACTIONS:
		if not policy.enabled:
			break

		if action == READ and not policy.read_enabled:
			continue

		if action != READ and not policy.write_enabled:
			continue

		possible.append(action)

	return tuple(possible)


def _norm(value) -> str:
	return str(value or "").strip().lower()
