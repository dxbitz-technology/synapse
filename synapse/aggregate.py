# Copyright (c) 2026, Dxbitz and contributors
"""Totals and counts over any DocType, through Frappe's permission-checked get_list.

No SQL and no Python from the caller. A spec names a DocType, metrics, optional
group fields and an optional time bucket. Frappe applies the user's permissions;
callers apply the Synapse access gate before calling run().
"""

from datetime import date, datetime

METRICS = ("count", "sum", "avg", "min", "max")
PERIODS = ("day", "week", "month", "quarter", "year")
NUMERIC = {"Currency", "Float", "Int", "Percent", "Duration"}
DATES = {"Date", "Datetime"}
MAX_GROUPS = 3
SOURCE_CAP = 20000
DEFAULT_LIMIT = 50


class SpecError(ValueError):
	"""A spec the engine cannot run. The message says what to change."""


# ---------------------------------------------------------------- pure parts (no Frappe)


def parse_metric(text):
	"""'count' or 'sum:base_grand_total' -> (fn, field or None, alias)."""
	text = str(text or "").strip()
	fn, _, field = text.partition(":")
	fn = fn.lower().strip()
	field = field.strip() or None
	if fn not in METRICS:
		raise SpecError(
			f"Metric '{text}' must start with one of {', '.join(METRICS)}, for example sum:grand_total."
		)
	if fn == "count":
		return fn, None, "count"
	if not field:
		raise SpecError(f"Metric '{text}' needs a field, for example {fn}:grand_total.")
	return fn, field, f"{fn}_{field}"


def bucket(value, by):
	"""A date or datetime to its bucket label: 2026-08-05, 2026-W32, 2026-08, 2026-Q3, 2026."""
	if value is None or value == "":
		return "(Not set)"
	if isinstance(value, str):
		value = date.fromisoformat(value[:10])
	if isinstance(value, datetime):
		value = value.date()
	if by == "day":
		return value.isoformat()
	if by == "week":
		y, w, _ = value.isocalendar()
		return f"{y}-W{w:02d}"
	if by == "month":
		return f"{value.year}-{value.month:02d}"
	if by == "quarter":
		return f"{value.year}-Q{(value.month - 1) // 3 + 1}"
	return str(value.year)


def fold(rows, group_fields, period_field, by, metrics):
	"""Combine database groups into final groups, re-bucketing dates by period.

	rows carry count and, per summed field, sum, min and max. avg is computed
	from sum and count at the end, so it stays exact after folding.
	"""
	out = {}
	for r in rows:
		key = tuple(r.get(g) for g in group_fields)
		if period_field:
			key += (bucket(r.get(period_field), by),)
		acc = out.get(key)
		if acc is None:
			acc = out[key] = {"__n": 0}
		acc["__n"] += r.get("__n") or 0
		# Each source column is combined once, however many metrics read it.
		for kind, field in _sources(metrics):
			col = f"__{kind}_{field}"
			v = r.get(col)
			if v is None:
				continue
			if kind == "sum":
				acc[col] = (acc.get(col) or 0) + v
			elif acc.get(col) is None:
				acc[col] = v
			else:
				acc[col] = min(acc[col], v) if kind == "min" else max(acc[col], v)

	final = []
	for key, acc in out.items():
		row = {}
		for i, g in enumerate(group_fields):
			row[g] = key[i]
		if period_field:
			row["period"] = key[len(group_fields)]
		for fn, field, alias in metrics:
			if fn == "count":
				row[alias] = acc["__n"]
			elif fn == "sum":
				row[alias] = round(acc.get(f"__sum_{field}") or 0, 6)
			elif fn == "avg":
				row[alias] = round((acc.get(f"__sum_{field}") or 0) / acc["__n"], 6) if acc["__n"] else None
			else:
				row[alias] = acc.get(f"__{fn}_{field}")
		final.append(row)
	return final


def _sources(metrics):
	"""The distinct database columns the metrics need: (sum|min|max, field)."""
	out = []
	for fn, field, _alias in metrics:
		if field is None:
			continue
		kind = "sum" if fn in ("sum", "avg") else fn
		if (kind, field) not in out:
			out.append((kind, field))
	return out


def sort_rows(rows, order_by, default_key, default_desc):
	key, desc = default_key, default_desc
	if order_by:
		parts = str(order_by).split()
		key = parts[0]
		desc = len(parts) > 1 and parts[1].lower() == "desc"
		if rows and key not in rows[0]:
			raise SpecError(f"order_by '{key}' is not a column. Columns are: {', '.join(rows[0])}.")
	if key is None:
		return rows
	# Empty values always go last, whichever way the rest is sorted.
	present = [r for r in rows if r.get(key) is not None]
	empty = [r for r in rows if r.get(key) is None]
	return sorted(present, key=lambda r: r.get(key), reverse=desc) + empty


def shape(widget_type, rows, spec):
	"""Turn result rows into the data shape a widget draws.

	stat  -> {value, spark?}       first metric, summed over rows; spark when a period is set
	list  -> [{title, value, ...}]  first group (or period) as title, first metric as value
	table -> {columns, result}
	charts -> rows as they are: label column first, metric columns as series
	"""
	metrics = spec["_metrics"]
	first = metrics[0][2]
	label = spec["_label"]
	if widget_type == "stat":
		total = 0
		for r in rows:
			total += r.get(first) or 0
		out = {"value": total}
		if spec.get("_period_field") and len(rows) > 1:
			spark = []
			for r in sorted(rows, key=lambda x: x.get("period") or ""):
				spark.append(r.get(first) or 0)
			out["spark"] = spark
		return out
	if widget_type == "list":
		items = []
		for r in rows:
			item = {"title": str(r.get(label)) if label else "", "value": r.get(first)}
			sub = [str(r.get(g)) for g in spec["_group_by"][1:] if r.get(g) is not None]
			if sub:
				item["subtitle"] = ", ".join(sub)
			items.append(item)
		return items
	if widget_type == "table":
		cols = []
		for g in spec["_group_by"]:
			cols.append({"fieldname": g, "label": spec["_labels"].get(g, g), "fieldtype": "Data"})
		if spec.get("_period_field"):
			cols.append({"fieldname": "period", "label": spec["_period_by"].title(), "fieldtype": "Data"})
		for fn, field, alias in metrics:
			cols.append(
				{
					"fieldname": alias,
					"label": "Count"
					if fn == "count"
					else f"{fn.title()} of {spec['_labels'].get(field, field)}",
					"fieldtype": "Int" if fn == "count" else "Float",
				}
			)
		return {"columns": cols, "result": rows}
	return rows


# ---------------------------------------------------------------- Frappe parts


def compile_spec(spec):
	"""Check a spec against the DocType's real fields. Returns it with private keys added."""
	import frappe

	from synapse.mcp_tools.documents import STANDARD_FIELDS

	if not isinstance(spec, dict):
		raise SpecError("A query must be an object with at least a doctype.")
	doctype = str(spec.get("doctype") or "").strip()
	if not doctype or not frappe.db.exists("DocType", doctype):
		raise SpecError(f"'{doctype}' is not a DocType on this site.")
	meta = frappe.get_meta(doctype)
	if meta.istable:
		raise SpecError(f"'{doctype}' is a child table. Aggregate its parent DocType instead.")
	fields = {df.fieldname: df for df in meta.fields}
	known = set(fields) | set(STANDARD_FIELDS)
	labels = {f: (fields[f].label if f in fields else f.replace("_", " ").title()) for f in known}

	def field_type(name):
		if name in ("creation", "modified"):
			return "Datetime"
		if name in ("docstatus", "idx"):
			return "Int"
		return fields[name].fieldtype if name in fields else "Data"

	group_by = spec.get("group_by") or []
	if isinstance(group_by, str):
		group_by = [group_by]
	if len(group_by) > MAX_GROUPS:
		raise SpecError(f"group_by takes at most {MAX_GROUPS} fields.")
	for g in group_by:
		if g not in known:
			raise SpecError(f"group_by '{g}' is not a field on {doctype}. Use describe_doctype to see them.")

	metrics = []
	for m in spec.get("metrics") or ["count"]:
		fn, field, alias = parse_metric(m)
		if field is not None:
			if field not in known:
				raise SpecError(f"Metric field '{field}' is not a field on {doctype}.")
			kind = field_type(field)
			if fn in ("sum", "avg") and kind not in NUMERIC:
				raise SpecError(f"{fn} needs a number field. '{field}' is {kind}.")
			if fn in ("min", "max") and kind not in NUMERIC | DATES:
				raise SpecError(f"{fn} needs a number or date field. '{field}' is {kind}.")
		metrics.append((fn, field, alias))

	period = spec.get("period")
	period_field, period_by = None, None
	if period:
		if not isinstance(period, dict):
			raise SpecError('period must be {"field": "posting_date", "by": "month"}.')
		period_field = period.get("field")
		period_by = period.get("by") or "month"
		if period_field not in known or field_type(period_field) not in DATES:
			raise SpecError(f"period field '{period_field}' must be a Date or Datetime field on {doctype}.")
		if period_by not in PERIODS:
			raise SpecError(f"period by must be one of {', '.join(PERIODS)}.")

	filters = spec.get("filters") or {}
	if not isinstance(filters, dict):
		raise SpecError("filters must be an object of field names to values.")
	for f in filters:
		if f not in known:
			raise SpecError(f"Filter field '{f}' is not a field on {doctype}.")

	out = dict(spec)
	out.update(
		{
			"doctype": doctype,
			"_group_by": list(group_by),
			"_metrics": metrics,
			"_period_field": period_field,
			"_period_by": period_by,
			"_label": group_by[0] if group_by else ("period" if period_field else None),
			"_labels": labels,
			"_known": known,
		}
	)
	return out


def run(spec, extra_filters=None, limit=None):
	"""Run a compiled or raw spec. Returns {rows, row_count, truncated, columns}."""
	import frappe

	if "_metrics" not in spec:
		spec = compile_spec(spec)
	doctype = spec["doctype"]
	group_fields = spec["_group_by"]
	period_field = spec["_period_field"]
	db_groups = list(group_fields) + ([period_field] if period_field else [])

	select = [*db_groups, {"COUNT": "*", "as": "__n"}]
	for kind, field in _sources(spec["_metrics"]):
		select.append({kind.upper(): field, "as": f"__{kind}_{field}"})

	filters = dict(spec.get("filters") or {})
	for k, v in (extra_filters or {}).items():
		if k not in spec["_known"]:
			raise SpecError(f"Filter field '{k}' is not a field on {doctype}.")
		filters[k] = v

	raw = frappe.get_list(
		doctype,
		fields=select,
		filters=filters,
		group_by=", ".join(f"`tab{doctype}`.`{g}`" for g in db_groups) or None,
		order_by=None,
		limit_page_length=SOURCE_CAP + 1,
	)
	if len(raw) > SOURCE_CAP:
		raise SpecError(
			"Too many groups. Group by fewer fields or use a longer period, such as month instead of day."
		)
	rows = fold([dict(r) for r in raw], group_fields, period_field, spec["_period_by"], spec["_metrics"])

	first_metric = spec["_metrics"][0][2]
	if period_field and not group_fields:
		rows = sort_rows(rows, spec.get("order_by"), "period", False)
	else:
		rows = sort_rows(rows, spec.get("order_by"), first_metric, True)

	cap = limit or spec.get("limit") or DEFAULT_LIMIT
	try:
		cap = max(1, min(int(cap), 500))
	except (TypeError, ValueError):
		cap = DEFAULT_LIMIT
	truncated = len(rows) > cap
	rows = rows[:cap]
	columns = list(rows[0]) if rows else []
	return {"rows": _plain(rows), "row_count": len(rows), "truncated": truncated, "columns": columns}


def _plain(rows):
	from synapse.mcp_tools.serialise import to_client

	return to_client(rows)
