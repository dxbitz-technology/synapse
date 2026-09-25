# Copyright (c) 2026, Dxbitz and contributors
"""The document tools: read and write ERPNext data over MCP."""

import frappe
from frappe.model.base_document import BaseDocument
from frappe.model.document import Document

from synapse.mcp import mcp
from synapse.mcp_core import ToolAnnotations
from synapse.mcp_tools import audit, serialise, settings
from synapse.mcp_tools.policy import (
	ACTIONS,
	CANCEL,
	DELETE,
	OPERATE,
	READ,
	SUBMIT,
	WRITE,
	Denied,
	actions_possible,
	check,
)

PROTECTED_FIELDS = frozenset(
	{
		"doctype",
		"docstatus",
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"idx",
		"parent",
		"parenttype",
		"parentfield",
		"__islocal",
		"__unsaved",
	}
)

LAYOUT_FIELDTYPES = frozenset(
	{"Section Break", "Column Break", "Tab Break", "HTML", "Heading", "Button", "Fold"}
)

STANDARD_FIELDS = ("name", "owner", "creation", "modified", "modified_by", "docstatus", "idx")

_ORDER_DIRECTIONS = ("asc", "desc")


@mcp.tool(
	annotations=ToolAnnotations(title="List reachable DocTypes", readOnlyHint=True),
	enabled=settings.read_tools_enabled,
)
@audit.audited(audit.READ)
def list_available_doctypes():
	"""List the DocTypes this endpoint can reach and what may be done to each."""

	policy = settings.get_policy()

	if policy.full_access:
		return _full_access_summary(policy)

	available = []
	for key in sorted(policy.grants):
		doctype = policy.grant_names.get(key, key)
		actions = []
		for action in ACTIONS:
			try:
				check(policy, action, doctype)
			except Denied:
				continue
			actions.append(action)

		if actions:
			available.append({"doctype": doctype, "actions": actions})

	audit.current().rows(len(available))
	return {"doctypes": available, "count": len(available)}


@mcp.tool(
	annotations=ToolAnnotations(title="Describe a DocType", readOnlyHint=True),
	enabled=settings.read_tools_enabled,
)
@audit.audited(audit.READ)
def describe_doctype(doctype: str):
	"""Return the fields of a DocType, so a document can be read or built correctly.

	Args:
	        doctype: The DocType to describe, for example "Sales Invoice"."""

	doctype = _gate(READ, doctype)
	meta = frappe.get_meta(doctype)

	fields = [_field_info(df) for df in meta.fields if df.fieldtype not in LAYOUT_FIELDTYPES]

	audit.current().rows(len(fields))
	return {
		"doctype": doctype,
		"is_submittable": bool(meta.is_submittable),
		"is_tree": bool(getattr(meta, "is_tree", 0)),
		"title_field": meta.title_field,
		"standard_fields": list(STANDARD_FIELDS),
		"fields": fields,
	}


def _full_access_summary(policy) -> dict:
	"""Discovery for a caller whose profile grants Full Access."""

	possible = list(actions_possible(policy))

	blocked = []
	for name in sorted(policy.denied):
		actions = sorted(policy.denied[name])
		blocked.append({"doctype": name, "blocked": actions})

	audit.current().rows(len(blocked))
	return {
		"mode": "full_access",
		"actions_possible": possible,
		"blocked_doctypes": blocked,
		"note": (
			"Your profile grants full access, so every DocType on this site is reachable "
			"for the actions listed in actions_possible, subject to your own Frappe "
			"permissions, which are applied per record. Token and credential DocTypes are "
			"always blocked, and schema, code and permission DocTypes are always read only. "
			"Use describe_doctype to see a DocType's fields."
		),
	}


def _field_info(df) -> dict:
	info = {
		"fieldname": df.fieldname,
		"label": df.label,
		"fieldtype": df.fieldtype,
	}

	if df.options:
		info["options"] = df.options
	if df.reqd:
		info["required"] = True
	if df.read_only:
		info["read_only"] = True
	if df.default:
		info["default"] = df.default

	return info


@mcp.tool(
	annotations=ToolAnnotations(title="Get a document", readOnlyHint=True),
	enabled=settings.read_tools_enabled,
)
@audit.audited(audit.READ)
def get_doc(doctype: str, name: str):
	"""Fetch one whole document, child tables included.

	Args:
		doctype: The DocType, for example "Sales Invoice".
		name: The document name, for example "ACC-SINV-2026-00001".
	"""

	doctype = _gate(READ, doctype)
	audit.current().target(doctype, name)

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")

	audit.current().rows(1)
	return {"doc": _document_dict(doc)}


@mcp.tool(
	annotations=ToolAnnotations(title="Get one field value", readOnlyHint=True),
	enabled=settings.read_tools_enabled,
)
@audit.audited(audit.READ)
def get_value(doctype: str, fieldname: str, name: str | None = None, filters: dict | None = None):
	"""Read a single field without pulling the whole document.

	Args:
	        doctype: The DocType to read from.
	        fieldname: The field to return.
	        name: The document name, when it is known.
	        filters: Field/value pairs used to find the document instead. An
	                operator may be given as a list, for example
	                {"status": ["!=", "Closed"]}."""

	doctype = _gate(READ, doctype)
	audit.current().target(doctype, name)

	if not name and not filters:
		raise Denied("Give either 'name' or 'filters'.")

	fields = _validate_fields(doctype, [fieldname])
	lookup = {"name": name} if name else _validate_filters(filters)

	rows = frappe.get_list(doctype, filters=lookup, fields=fields, limit_page_length=1)

	if not rows:
		audit.current().rows(0)
		return {"value": None, "found": False}

	audit.current().rows(1)
	return {"value": _out(rows[0].get(fieldname)), "found": True}


@mcp.tool(
	annotations=ToolAnnotations(title="List documents", readOnlyHint=True),
	enabled=settings.read_tools_enabled,
)
@audit.audited(audit.READ)
def get_list(
	doctype: str,
	filters: dict | None = None,
	fields: list | None = None,
	order_by: str | None = None,
	limit: int | None = None,
	start: int = 0,
):
	"""List documents the calling user is allowed to see.

	Args:
	        doctype: The DocType to list.
	        filters: Field/value pairs. An operator may be given as a list, for
	                example {"posting_date": [">", "01-01-2026"]} or
	                {"status": ["in", ["Open", "Overdue"]]}.
	        fields: Field names to return. Defaults to name and the title field.
	        order_by: "fieldname asc" or "fieldname desc".
	        limit: Rows to return. Clamped to the site's Synapse row limit.
	        start: Rows to skip, for paging."""

	doctype = _gate(READ, doctype)

	limit = settings.row_limit(limit)
	fields = _validate_fields(doctype, fields) if fields else _default_fields(doctype)

	rows = frappe.get_list(
		doctype,
		filters=_validate_filters(filters),
		fields=fields,
		order_by=_validate_order_by(doctype, order_by),
		limit_start=max(0, _as_int(start, 0)),
		limit_page_length=limit,
	)

	rows = [_out(dict(row)) for row in rows]

	audit.current().rows(len(rows))
	return {
		"rows": rows,
		"row_count": len(rows),
		"truncated": len(rows) == limit,
		"fields": fields,
	}


@mcp.tool(
	annotations=ToolAnnotations(title="Count documents", readOnlyHint=True),
	enabled=settings.read_tools_enabled,
)
@audit.audited(audit.READ)
def get_count(doctype: str, filters: dict | None = None):
	"""Count the documents the calling user is allowed to see.

	Args:
		doctype: The DocType to count.
		filters: Field/value pairs, same form as get_list.
	"""

	doctype = _gate(READ, doctype)

	rows = frappe.get_list(
		doctype,
		filters=_validate_filters(filters),
		fields=[{"COUNT": "name"}],
		limit_page_length=0,
	)

	total = int(next(iter((rows[0] or {}).values()), 0) or 0) if rows else 0

	audit.current().rows(total)
	return {"count": total}


@mcp.tool(
	annotations=ToolAnnotations(title="Create a document", readOnlyHint=False),
	enabled=settings.write_tools_enabled,
)
@audit.audited(audit.WRITE)
def create_doc(doctype: str, values: dict):
	"""Create and save a new document. It is left as a draft.

	Args:
	        doctype: The DocType to create.
	        values: Field values. Child tables are given as a list of objects, for
	                example {"items": [{"item_code": "X", "qty": 1}]}."""

	doctype = _gate(WRITE, doctype)
	audit.current().sent(values, _secret_fieldnames(doctype))

	doc = frappe.new_doc(doctype)
	doc.update(_prepare(doctype, values))
	doc.insert()

	audit.current().target(doctype, doc.name)
	audit.current().rows(1)
	return {"name": doc.name, "doctype": doctype, "docstatus": doc.docstatus}


@mcp.tool(
	annotations=ToolAnnotations(
		title="Update a document",
		readOnlyHint=False,
		destructiveHint=True,
	),
	enabled=settings.write_tools_enabled,
)
@audit.audited(audit.WRITE)
def update_doc(doctype: str, name: str, values: dict):
	"""Change fields on an existing document and save it.

	Args:
	        doctype: The DocType to update.
	        name: The document name.
	        values: Field values to set. A child table given here replaces the whole
	                table, so send every row you want to keep."""

	doctype = _gate(WRITE, doctype)
	audit.current().target(doctype, name)
	secret_keys = _secret_fieldnames(doctype)
	audit.current().sent(values, secret_keys)

	prepared = _prepare(doctype, values)

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")

	before = {key: _out(doc.get(key)) for key in prepared}
	doc.update(prepared)
	doc.save()

	audit.current().changed(
		{key: {"from": before.get(key), "to": _out(doc.get(key))} for key in prepared},
		secret_keys,
	)
	audit.current().rows(1)
	return {"name": doc.name, "doctype": doctype, "updated_fields": sorted(prepared)}


@mcp.tool(
	annotations=ToolAnnotations(
		title="Set one field",
		readOnlyHint=False,
		destructiveHint=True,
		idempotentHint=True,
	),
	enabled=settings.write_tools_enabled,
)
@audit.audited(audit.WRITE)
def set_value(doctype: str, name: str, fieldname: str, value=None):
	"""Set a single field on a document and save it.

	Args:
	        doctype: The DocType to update.
	        name: The document name.
	        fieldname: The field to set.
	        value: The new value. Dates may be YYYY-MM-DD or DD-MM-YYYY."""

	return update_doc.__wrapped__(doctype=doctype, name=name, values={fieldname: value})


@mcp.tool(
	annotations=ToolAnnotations(title="Submit a document", readOnlyHint=False, idempotentHint=True),
	enabled=settings.write_tools_enabled,
)
@audit.audited(audit.WRITE)
def submit_doc(doctype: str, name: str):
	"""Submit a draft document, moving it to docstatus 1.

	Args:
		doctype: The DocType to submit.
		name: The document name.
	"""

	doctype = _gate(SUBMIT, doctype)
	audit.current().target(doctype, name)

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("submit")
	doc.submit()

	audit.current().rows(1)
	return {"name": doc.name, "doctype": doctype, "docstatus": doc.docstatus}


@mcp.tool(
	annotations=ToolAnnotations(title="Cancel a document", readOnlyHint=False, destructiveHint=True),
	enabled=settings.write_tools_enabled,
)
@audit.audited(audit.WRITE)
def cancel_doc(doctype: str, name: str):
	"""Cancel a submitted document, moving it to docstatus 2.

	Args:
		doctype: The DocType to cancel.
		name: The document name.
	"""

	doctype = _gate(CANCEL, doctype)
	audit.current().target(doctype, name)

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("cancel")
	doc.cancel()

	audit.current().rows(1)
	return {"name": doc.name, "doctype": doctype, "docstatus": doc.docstatus}


@mcp.tool(
	annotations=ToolAnnotations(title="Delete a document", readOnlyHint=False, destructiveHint=True),
	enabled=settings.write_tools_enabled,
)
@audit.audited(audit.WRITE)
def delete_doc(doctype: str, name: str):
	"""Delete a document. Link checks apply, so a referenced document is refused.

	Args:
		doctype: The DocType to delete from.
		name: The document name.
	"""

	doctype = _gate(DELETE, doctype)
	audit.current().target(doctype, name)

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("delete")
	audit.current().sent(_document_dict(doc), _secret_fieldnames(doctype))

	frappe.delete_doc(doctype, name)

	audit.current().rows(1)
	return {"name": name, "doctype": doctype, "deleted": True}


@mcp.tool(
	annotations=ToolAnnotations(title="Add a child row", readOnlyHint=False, destructiveHint=False),
	enabled=settings.write_tools_enabled,
)
@audit.audited(audit.WRITE)
def add_child(parent_doctype: str, parent_name: str, child_field: str, values: dict):
	"""Append one row to a child table and save the parent.

	Args:
	        parent_doctype: The parent DocType, for example "Sales Order".
	        parent_name: The parent document name.
	        child_field: The child-table fieldname on the parent, for example "items".
	        values: Field values for the new row."""

	doctype, doc, child_doctype = _open_parent_for_child(parent_doctype, parent_name, child_field)

	secret_keys = _secret_fieldnames(child_doctype)
	audit.current().sent({"child_field": child_field, "values": values}, secret_keys)

	row = doc.append(child_field, _prepare(child_doctype, values, child=True))
	doc.save()

	audit.current().rows(1)
	return {
		"parent_doctype": doctype,
		"parent_name": doc.name,
		"child_field": child_field,
		"row_name": row.name,
		"idx": row.idx,
	}


@mcp.tool(
	annotations=ToolAnnotations(
		title="Set fields on a child row",
		readOnlyHint=False,
		destructiveHint=True,
		idempotentHint=True,
	),
	enabled=settings.write_tools_enabled,
)
@audit.audited(audit.WRITE)
def set_child_value(
	parent_doctype: str,
	parent_name: str,
	child_field: str,
	row_name: str,
	changes: dict,
	expect: dict | None = None,
):
	"""Set one or more fields on one existing child row and save the parent.

	Args:
	        parent_doctype: The parent DocType, for example "Sales Order".
	        parent_name: The parent document name.
	        child_field: The child-table fieldname on the parent, for example "items".
	        row_name: The row's name, taken from a prior get_doc.
	        changes: Field to value, for example {"rate": 250, "discount_percentage": 0}.
	                Must not be empty. Dates may be YYYY-MM-DD or DD-MM-YYYY.
	        expect: Optional. Field to expected current value, for example {"rate": 200}.
	                The write is refused if the row does not currently hold those values, so
	                an edit cannot land on a row that changed since it was read."""

	doctype, applied = _apply_row_edits(
		parent_doctype,
		parent_name,
		child_field,
		[{"row_name": row_name, "changes": changes, "expect": expect}],
	)
	name_out, fields = applied[0]
	return {
		"parent_doctype": doctype,
		"parent_name": parent_name,
		"child_field": child_field,
		"row_name": name_out,
		"updated_fields": fields,
	}


@mcp.tool(
	annotations=ToolAnnotations(
		title="Set fields on many child rows", readOnlyHint=False, destructiveHint=True
	),
	enabled=settings.write_tools_enabled,
)
@audit.audited(audit.WRITE)
def set_child_rows(parent_doctype: str, parent_name: str, child_field: str, edits: list):
	"""Edit several child rows at once, all or nothing, in one save.

	Args:
	        parent_doctype: The parent DocType.
	        parent_name: The parent document name.
	        child_field: The child-table fieldname on the parent, for example "items".
	        edits: A list of edits, each {"row_name": ..., "changes": {...}} with an
	                optional "expect": {...} of current values to assert before the change."""

	doctype, applied = _apply_row_edits(parent_doctype, parent_name, child_field, edits)
	return {
		"parent_doctype": doctype,
		"parent_name": parent_name,
		"child_field": child_field,
		"row_count": len(applied),
		"rows": [{"row_name": rn, "updated_fields": fields} for rn, fields in applied],
	}


@mcp.tool(
	annotations=ToolAnnotations(title="Delete a child row", readOnlyHint=False, destructiveHint=True),
	enabled=settings.write_tools_enabled,
)
@audit.audited(audit.WRITE)
def delete_child(
	parent_doctype: str, parent_name: str, child_field: str, row_name: str, expect: dict | None = None
):
	"""Remove one row from a child table and save the parent.

	Args:
	        parent_doctype: The parent DocType.
	        parent_name: The parent document name.
	        child_field: The child-table fieldname on the parent.
	        row_name: The row's name, taken from a prior get_doc.
	        expect: Optional. Field to expected current value, asserted before the row
	                is removed, so a delete cannot hit a row that shifted since it was read."""

	doctype, doc, child_doctype = _open_parent_for_child(parent_doctype, parent_name, child_field)

	row = _locate_row(doc, child_field, row_name)
	_check_expect(row, child_field, expect)

	audit.current().sent(
		{"child_field": child_field, "row_name": row.name, "expect": expect, "removed": row.as_dict()},
		_secret_fieldnames(child_doctype),
	)

	doc.remove(row)
	doc.save()

	audit.current().rows(1)
	return {
		"parent_doctype": doctype,
		"parent_name": parent_name,
		"child_field": child_field,
		"deleted_row": row.name,
	}


@mcp.tool(
	annotations=ToolAnnotations(
		title="Replace text in a field",
		readOnlyHint=False,
		destructiveHint=True,
	),
	enabled=settings.write_tools_enabled,
)
@audit.audited(audit.WRITE)
def replace_in_field(doctype: str, name: str, field: str, find: str, replace: str, expect_count: int = 1):
	"""Replace occurrences of a substring inside one text field, carefully.

	Args:
	        doctype: The DocType.
	        name: The document name.
	        field: The text field to edit.
	        find: The exact substring to look for.
	        replace: The text to put in its place.
	        expect_count: The exact number of occurrences expected. Default 1."""

	doctype = _gate(WRITE, doctype)
	audit.current().target(doctype, name)

	if not isinstance(find, str) or find == "":
		raise Denied("'find' must be a non-empty string.")
	if not isinstance(replace, str):
		raise Denied("'replace' must be a string.")
	if find == replace:
		raise Denied("'find' and 'replace' are identical, nothing to do.")

	meta = frappe.get_meta(doctype)
	df = meta.get_field(field)
	if not df or df.fieldtype in LAYOUT_FIELDTYPES or df.fieldtype == "Table":
		raise Denied(f"'{field}' is not an editable field on {doctype}.")
	if field in PROTECTED_FIELDS:
		raise Denied(f"'{field}' is managed by the framework and cannot be edited here.")

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")

	current = doc.get(field)
	if not isinstance(current, str):
		raise Denied(f"'{field}' does not hold text, so it cannot be replaced into.")

	count = current.count(find)
	if count != expect_count:
		raise Denied(
			f"Found {count} occurrence(s) of that text in '{field}', but expect_count is "
			f"{expect_count}. Refusing rather than replacing the wrong amount. Read the "
			"field with get_doc and set expect_count to the real number."
		)

	updated = current.replace(find, replace)
	secret_keys = _secret_fieldnames(doctype)
	doc.set(field, updated)
	doc.save()

	audit.current().changed({field: {"from": _out(current), "to": _out(updated)}}, secret_keys)
	audit.current().rows(count)
	return {"name": doc.name, "doctype": doctype, "field": field, "replaced": count}


BLOCKED_OPERATIONS = frozenset(
	{
		"insert",
		"save",
		"submit",
		"cancel",
		"delete",
		"delete_doc",
		"save_version",
		"db_insert",
		"db_update",
		"db_set",
		"set_value",
		"rename",
		"run_method",
		"validate",
		"before_validate",
		"before_save",
		"after_insert",
		"before_insert",
		"on_update",
		"on_submit",
		"before_submit",
		"on_cancel",
		"before_cancel",
		"on_trash",
		"after_delete",
		"on_change",
		"on_update_after_submit",
		"before_update_after_submit",
	}
) | frozenset(
	name for cls in (BaseDocument, Document) for name in dir(cls) if callable(getattr(cls, name, None))
)


@mcp.tool(
	annotations=ToolAnnotations(title="Run a document operation", readOnlyHint=False, destructiveHint=True),
	enabled=settings.operate_tools_enabled,
)
@audit.audited(audit.OPERATE)
def run_operation(doctype: str, name: str, operation: str, args: dict | None = None, save: bool = False):
	"""Call one of a document's own methods, for actions the field tools cannot do.

	Args:
	        doctype: The DocType, for example "Sales Invoice".
	        name: The document name.
	        operation: The method to call, for example "repost_accounting_entries".
	        args: Optional keyword arguments passed to the method.
	        save: Save the document after the method runs. Default false."""

	doctype = _gate(OPERATE, doctype)
	audit.current().target(doctype, name)

	if not operation or not isinstance(operation, str):
		raise Denied("An operation (method name) is required.")

	operation = operation.strip()
	if operation.startswith("_"):
		raise Denied("Private methods (leading underscore) cannot be run.")
	if (
		operation in BLOCKED_OPERATIONS
		or operation == "onload"
		or operation.startswith(("before_", "after_", "on_"))
	):
		raise Denied(
			f"'{operation}' has its own tool or would bypass a gate, so it cannot be run "
			"through run_operation."
		)

	if args is not None and not isinstance(args, dict):
		raise Denied("'args' must be an object of keyword arguments.")

	audit.current().sent({"operation": operation, "args": args or {}})

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")

	fn = getattr(doc, operation, None)
	if not callable(fn):
		raise Denied(f"'{operation}' is not a method on {doctype}.")

	result = doc.run_method(operation, **(args or {}))

	if save:
		doc.save()

	audit.current().rows(1)
	return {
		"name": doc.name,
		"doctype": doctype,
		"operation": operation,
		"docstatus": doc.docstatus,
		"result": _out(result),
	}


def _child_doctype(doctype: str, table_field: str) -> str:
	"""The child DocType behind a Table field, or Denied if it is not one."""

	meta = frappe.get_meta(doctype)
	df = meta.get_field(table_field)
	if not df or df.fieldtype != "Table":
		raise Denied(f"'{table_field}' is not a child table on {doctype}.")
	return df.options


def _open_parent_for_child(parent_doctype: str, parent_name: str, child_field: str):
	"""Gate and load a parent for a child-table write. Raises Denied."""

	doctype = _gate(WRITE, parent_doctype)
	audit.current().target(doctype, parent_name)

	child_doctype = _child_doctype(doctype, child_field)

	doc = frappe.get_doc(doctype, parent_name)
	doc.check_permission("write")

	if doc.docstatus == 1:
		raise Denied(
			"The parent document is submitted, so its rows cannot be edited. Reopen it "
			"with cancel and amend if the change is intended."
		)
	if doc.docstatus == 2:
		raise Denied("The parent document is cancelled and cannot be edited.")

	return doctype, doc, child_doctype


def _locate_row(doc, child_field: str, row_name: str):
	"""Locate one child row by its name only. Raises Denied if absent."""

	if not row_name or not isinstance(row_name, str):
		raise Denied("A row_name is required.")

	wanted = row_name.strip()
	for r in doc.get(child_field) or []:
		if r.name and str(r.name) == wanted:
			return r

	raise Denied(
		f"No row named '{row_name}' in {child_field}. Read the document with get_doc to "
		"get the row name, rows are addressed by name, not by position or content."
	)


def _check_expect(row, child_field: str, expect) -> None:
	"""Refuse if any expected value does not match the row's current value."""

	if expect is None:
		return
	if not isinstance(expect, dict):
		raise Denied("'expect' must be an object of field name to expected value.")

	for field, expected in expect.items():
		current = _out(row.get(field))
		if not _values_match(current, expected):
			raise Denied(
				f"Stale expect on {child_field} row {row.name}: '{field}' changed. Re-read the document."
			)


def _values_match(current, expected) -> bool:
	"""Compare a serialised current value to an expected one, numbers loosely."""

	numeric = (int, float)
	if (
		isinstance(current, numeric)
		and isinstance(expected, numeric)
		and not isinstance(current, bool)
		and not isinstance(expected, bool)
	):
		return float(current) == float(expected)
	return current == expected


def _prepare_child_changes(child_doctype: str, changes) -> dict:
	"""Validate a changes dict for a child row and convert its dates.

	Non-empty, every key a real field on the child, none of them a framework-owned
	field. Raises Denied naming the first problem.
	"""

	if not isinstance(changes, dict) or not changes:
		raise Denied("'changes' must be a non-empty object of field name to value.")

	meta = frappe.get_meta(child_doctype)
	known = {df.fieldname for df in meta.fields}

	prepared = {}
	for key, value in changes.items():
		if key in PROTECTED_FIELDS:
			raise Denied(f"'{key}' is managed by the framework and cannot be set on a child row.")
		if key not in known:
			raise Denied(
				f"'{key}' is not a field on {child_doctype}. Use describe_doctype on the child "
				"table to see its fields."
			)

		df = meta.get_field(key)
		if df and df.fieldtype in ("Date", "Datetime"):
			value = serialise.to_db_date(value)
		prepared[key] = value

	return prepared


def _apply_row_edits(parent_doctype: str, parent_name: str, child_field: str, edits):
	"""The one code path behind set_child_value and set_child_rows."""

	if not isinstance(edits, list) or not edits:
		raise Denied("Give at least one edit.")

	doctype, doc, child_doctype = _open_parent_for_child(parent_doctype, parent_name, child_field)
	secret_keys = _secret_fieldnames(child_doctype)

	plan = []
	asked = []
	for i, edit in enumerate(edits):
		if not isinstance(edit, dict):
			raise Denied(f"Edit {i} must be an object with 'row_name' and 'changes'.")

		row = _locate_row(doc, child_field, edit.get("row_name"))
		_check_expect(row, child_field, edit.get("expect"))
		prepared = _prepare_child_changes(child_doctype, edit.get("changes"))

		plan.append((row, prepared))
		asked.append({"row_name": row.name, "changes": edit.get("changes"), "expect": edit.get("expect")})

	audit.current().sent({"child_field": child_field, "edits": asked}, secret_keys)

	applied = []
	changed = {}
	for row, prepared in plan:
		for field, value in prepared.items():
			before = _out(row.get(field))
			row.set(field, value)
			changed[f"{child_field}[{row.name}].{field}"] = {"from": before, "to": _out(row.get(field))}
		applied.append((row.name, sorted(prepared)))

	doc.save()

	audit.current().changed(changed, secret_keys)
	audit.current().rows(len(applied))
	return doctype, applied


def _gate(action: str, doctype: str) -> str:
	"""Resolve the DocType, run the access gate, record the target. Raises Denied."""

	meta = _meta(doctype)

	if meta.istable:
		raise Denied(f"'{meta.name}' is a child table. Read or write it through its parent document.")

	resolved = check(settings.get_policy(), action, meta.name)
	audit.current().target(resolved)
	return resolved


def _meta(doctype: str):
	"""Frappe's meta for a DocType, or Denied if there is no such DocType."""

	if not doctype or not isinstance(doctype, str):
		raise Denied("A DocType is required.")

	try:
		return frappe.get_meta(doctype.strip())
	except Exception:
		raise Denied(f"'{doctype}' is not a DocType on this site.")


def _prepare(doctype: str, values, child: bool = False) -> dict:
	"""Reject framework-owned fields, then convert dates for the database."""

	if not isinstance(values, dict) or not values:
		raise Denied("'values' must be a non-empty object of field names to values.")

	if child:
		values = {k: v for k, v in values.items() if k not in PROTECTED_FIELDS}
	elif blocked := sorted(set(values) & PROTECTED_FIELDS):
		raise Denied(
			f"These fields are managed by the framework and cannot be set here: "
			f"{', '.join(blocked)}. Use submit_doc or cancel_doc to change docstatus."
		)

	meta = frappe.get_meta(doctype)
	prepared = {}

	for key, value in values.items():
		df = meta.get_field(key)
		if not isinstance(key, str) or key.startswith("_") or not df:
			raise Denied(f"'{key}' is not a writable field on {doctype}.")
		if df.fieldtype in LAYOUT_FIELDTYPES or df.get("is_virtual"):
			raise Denied(f"'{key}' is not a stored field on {doctype}.")

		if df and df.fieldtype in ("Date", "Datetime"):
			value = serialise.to_db_date(value)
		elif df.fieldtype in ("Table", "Table MultiSelect"):
			if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
				raise Denied(f"'{key}' must be a list of child-row objects.")
			value = [_prepare(df.options, row, child=True) for row in value]

		prepared[key] = value

	return prepared


def _secret_fieldnames(doctype: str, parent_only: bool = False) -> set:
	"""Lowercased names of Password-fieldtype fields on a DocType.

	Used both to strip secrets from get_doc output and to mask them in the audit
	log by field type rather than by how the key happens to be spelled. Includes
	child-table Password fields unless parent_only is set.
	"""

	meta = frappe.get_meta(doctype)
	names = {df.fieldname.lower() for df in meta.fields if df.fieldtype == "Password"}

	if parent_only:
		return {df.fieldname for df in meta.fields if df.fieldtype == "Password"}

	for table in meta.get_table_fields():
		child_meta = frappe.get_meta(table.options)
		names |= {df.fieldname.lower() for df in child_meta.fields if df.fieldtype == "Password"}

	return names


def _document_dict(doc) -> dict:
	"""A document as JSON, with fields the caller may not read left out."""

	doc.apply_fieldlevel_read_permissions()

	data = doc.as_dict(no_nulls=False)
	for fieldname in _secret_fieldnames(doc.doctype, parent_only=True):
		data.pop(fieldname, None)

	return _out(dict(data))


def _out(value):
	"""Convert a value for the client, in the date format this site has chosen."""

	return serialise.to_client(value, settings.output_formats())


def _validate_fields(doctype: str, fields) -> list:
	"""Allow plain field names only.

	frappe.get_list does its own validation, but accepting only names the meta
	knows about removes the whole class of expression-in-a-field-name tricks
	before it reaches the query builder.
	"""

	if not isinstance(fields, (list, tuple)):
		raise Denied("'fields' must be a list of field names.")

	meta = frappe.get_meta(doctype)
	known = {df.fieldname for df in meta.fields} | set(STANDARD_FIELDS)

	clean = []
	for field in fields:
		field = str(field).strip()
		if field not in known:
			raise Denied(f"'{field}' is not a field on {doctype}. Use describe_doctype to see them.")
		clean.append(field)

	if not clean:
		raise Denied("'fields' cannot be empty.")

	return clean


def _default_fields(doctype: str) -> list:
	meta = frappe.get_meta(doctype)
	fields = ["name"]

	if meta.title_field and meta.title_field != "name":
		fields.append(meta.title_field)

	if meta.is_submittable:
		fields.append("docstatus")

	return fields


def _validate_filters(filters):
	if filters is None:
		return {}

	if not isinstance(filters, dict):
		raise Denied("'filters' must be an object of field names to values.")

	return filters


def _validate_order_by(doctype: str, order_by):
	"""Only 'fieldname' or 'fieldname asc|desc'. Anything else is refused.

	order_by reaches the query builder as raw SQL, so it is the one string in
	this module that is checked rather than trusted.
	"""

	if not order_by:
		return "modified desc"

	parts = str(order_by).strip().split()
	if len(parts) > 2:
		raise Denied("'order_by' must be a field name, optionally followed by asc or desc.")

	fieldname = _validate_fields(doctype, [parts[0]])[0]
	direction = parts[1].lower() if len(parts) == 2 else "desc"

	if direction not in _ORDER_DIRECTIONS:
		raise Denied("'order_by' direction must be asc or desc.")

	return f"`tab{doctype}`.`{fieldname}` {direction}"


def _as_int(value, fallback: int) -> int:
	try:
		return int(value)
	except (TypeError, ValueError):
		return fallback
