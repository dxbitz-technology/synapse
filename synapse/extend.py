# Copyright (c) 2026, Dxbitz and contributors
"""Load custom tools from the current site's installed apps."""

import functools
import importlib
from collections.abc import Callable
from dataclasses import dataclass

__all__ = ["load_external_tools", "registered_tools", "tool"]


@dataclass
class ExternalTool:
	fn: Callable
	name: str
	app: str | None = None
	description: str | None = None
	read_only: bool = False
	destructive: bool = False


def tool(_fn=None, *, name=None, description=None, read_only=False, destructive=False):
	"""Attach tool metadata to a function listed in an app's synapse_tools hook."""

	def register(fn):
		fn._synapse_tool = ExternalTool(
			fn,
			name or fn.__name__,
			fn.__module__.split(".", 1)[0],
			description,
			read_only,
			destructive,
		)
		return fn

	return register(_fn) if callable(_fn) else register


def registered_tools() -> dict[str, ExternalTool]:
	"""Resolve declarations afresh; never retain another site's registrations."""
	import frappe

	installed = set(frappe.get_installed_apps())
	result = {}
	conflicts = set()
	for entry in frappe.get_hooks("synapse_tools") or []:
		try:
			declarations = []
			if isinstance(entry, dict):
				method = entry.get("method") or entry.get("tool")
				if not isinstance(method, str) or method.split(".", 1)[0] not in installed:
					continue
				fn = frappe.get_attr(method)
				if not callable(fn):
					continue
				declarations.append(
					ExternalTool(
						fn,
						entry.get("name") or fn.__name__,
						method.split(".", 1)[0],
						entry.get("description"),
						bool(entry.get("read_only")),
						bool(entry.get("destructive")),
					)
				)
			elif isinstance(entry, str) and entry.split(".", 1)[0] in installed:
				module = importlib.import_module(entry)
				declarations = [
					fn._synapse_tool
					for fn in vars(module).values()
					if callable(fn) and hasattr(fn, "_synapse_tool") and fn.__module__ == entry
				]
			for ext in declarations:
				if ext.name in result and result[ext.name] != ext:
					conflicts.add(ext.name)
				else:
					result[ext.name] = ext
		except Exception:
			frappe.log_error(
				title="Synapse custom tool", message="Could not load a synapse_tools declaration."
			)
	for name in conflicts:
		result.pop(name, None)
		frappe.log_error(title="Synapse custom tool", message=f"Duplicate tool name '{name}' was disabled.")
	return result


def load_external_tools():
	"""Build a request-local dispatch table without changing the built-in registry."""
	import frappe

	from synapse.mcp import mcp
	from synapse.mcp_core import MCP, ToolAnnotations
	from synapse.mcp_tools import audit, settings

	cached = getattr(frappe.local, "_synapse_external_tools", None)
	if cached is not None:
		return cached
	server = MCP("synapse-custom")
	for ext in registered_tools().values():
		if ext.name in mcp._tools:
			frappe.log_error(
				title="Synapse custom tool", message=f"Tool '{ext.name}' conflicts with a built-in."
			)
			continue
		runner = audit.audited(audit.CUSTOM, tool=ext.name)(_make_runner(audit, ext))
		server.tool(
			name=ext.name,
			description=ext.description,
			annotations=ToolAnnotations(
				title=ext.name, readOnlyHint=ext.read_only, destructiveHint=ext.destructive
			),
			enabled=lambda ext=ext: settings.custom_tool_enabled(ext.name, ext.read_only),
		)(runner)
	frappe.local._synapse_external_tools = server._tools
	return server._tools


def _make_runner(audit, ext):
	@functools.wraps(ext.fn)
	def runner(**kwargs):
		audit.current().sent(kwargs)
		result = ext.fn(**kwargs)
		return result if isinstance(result, dict) else {"result": result}

	return runner
