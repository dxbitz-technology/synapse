# Copyright (c) 2026, Dxbitz and contributors
"""Synapse UI dashboards: layout checks, filters, data loading and saved filters.

A dashboard is a Synapse Page with a Layout in the Synapse UI format. Its data is
one dict keyed by widget key. Script dashboards build that dict with one Data
Script per page. Assistant dashboards store it in Snapshot, written by the LLM.
"""

import json
import re
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

PAGE = "Synapse Page"
USER_FILTER = "Synapse User Filter"

CHART_TYPES = ("bar", "line", "area", "dot", "pie", "donut", "split")
WIDGET_TYPES = (*CHART_TYPES, "stat", "table", "list", "html")
FILTER_TYPES = ("select", "segment", "daterange", "date", "link", "check", "text", "number")
PRESETS = (
	"today",
	"last_7",
	"last_30",
	"this_month",
	"last_month",
	"this_quarter",
	"last_quarter",
	"this_year",
	"last_year",
)
REPORT_KEYS = (
	"columns",
	"groupBy",
	"collapsed",
	"totals",
	"sortBy",
	"sortDir",
	"pageSize",
	"search",
	"export",
	"empty",
)

KEY_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,59}")
MAX_LAYOUT = 200_000
MAX_DATA = 2_000_000
MAX_TEXT = 140
MAX_DEPTH = 4

# Keys that would let stored data change how a widget draws itself. The kit
# merges a payload's extra keys into widget options, so these are stripped
# from every payload before it leaves the server.
UNSAFE_OPTION_KEYS = {"template", "css", "isolate", "render", "html", "method", "fetch", "load"}


# ---------------------------------------------------------------- small helpers


def parse(value, what="value"):
	if value is None or value == "":
		return None
	if isinstance(value, (dict, list)):
		return value
	try:
		return json.loads(value)
	except ValueError:
		frappe.throw(_("{0} is not valid JSON.").format(what))


def safe_href(value):
	"""Allow site paths, anchors and http(s) links only."""
	if not isinstance(value, str):
		return None
	v = value.strip()
	if v.startswith("#") or (v.startswith("/") and not v.startswith("//")):
		return v
	if re.match(r"https?://", v, re.I):
		return v
	return None


def sanitize(value, depth=0):
	"""Strip draw-time options and unsafe links from data that reaches the browser."""
	if depth > 40:
		return None
	if isinstance(value, dict):
		out = {}
		for k, v in value.items():
			key = str(k)
			if key in UNSAFE_OPTION_KEYS:
				continue
			if key == "href":
				out[key] = safe_href(v)
				continue
			out[key] = sanitize(v, depth + 1)
		return out
	if isinstance(value, (list, tuple)):
		return [sanitize(v, depth + 1) for v in value]
	if isinstance(value, (str, int, float, bool)) or value is None:
		return value
	return str(value)


# ---------------------------------------------------------------- layout


def _clean_html_widget(w, assistant):
	if assistant:
		frappe.throw(_("Widget {0}: html widgets are not allowed on Assistant dashboards.").format(w["key"]))
	from frappe.utils.html_utils import sanitize_html

	w.pop("render", None)
	if w.get("template"):
		w["template"] = sanitize_html(str(w["template"]))
	if w.get("css"):
		w["isolate"] = "shadow" if w.get("isolate") == "shadow" else "scoped"


def _clean_filter(f, i):
	if not isinstance(f, dict):
		frappe.throw(_("Filter {0} must be an object.").format(i))
	key = str(f.get("key") or "")
	if not KEY_RE.fullmatch(key):
		frappe.throw(
			_("Filter {0}: key must start with a letter and use letters, numbers, _ or -.").format(i)
		)
	kind = f.get("type") or "text"
	if kind not in FILTER_TYPES:
		frappe.throw(_("Filter {0}: type must be one of {1}.").format(key, ", ".join(FILTER_TYPES)))
	f["type"] = kind
	if kind in ("select", "segment") and not f.get("options"):
		frappe.throw(_("Filter {0}: {1} needs options.").format(key, kind))
	if kind == "link" and not (f.get("doctype") and frappe.db.exists("DocType", f["doctype"])):
		frappe.throw(_("Filter {0}: link needs a doctype that exists on this site.").format(key))
	if kind == "daterange" and f.get("presets"):
		bad = [p for p in f["presets"] if p not in (*PRESETS, "custom")]
		if bad:
			frappe.throw(_("Filter {0}: unknown presets {1}.").format(key, ", ".join(map(str, bad))))
	return f


def validate_layout(layout, view_type="Dashboard", assistant=False) -> dict:
	"""Check a layout and return it cleaned. Raises with a plain message on error."""
	layout = parse(layout, _("Layout")) or {}
	if not isinstance(layout, dict):
		frappe.throw(_("Layout must be a JSON object."))
	if len(json.dumps(layout)) > MAX_LAYOUT:
		frappe.throw(_("Layout is too large."))

	# Code cannot travel in JSON, and these would point the browser at another method.
	for key in (
		"method",
		"fetch",
		"report",
		"mapFilters",
		"render",
		"load",
		"actions",
		"id",
		"title",
		"type",
	):
		layout.pop(key, None)

	filters = layout.get("filters") or []
	if not isinstance(filters, list):
		frappe.throw(_("Layout filters must be a list."))
	seen = set()
	for i, f in enumerate(filters, start=1):
		_clean_filter(f, i)
		if f["key"] in seen:
			frappe.throw(_("Filter key {0} is used twice.").format(f["key"]))
		seen.add(f["key"])

	if view_type == "Report":
		layout.pop("sections", None)
		table = layout.get("table") or {}
		if not isinstance(table, dict):
			frappe.throw(_("Report table options must be an object."))
		_clean_group_by(_("Report"), table.get("groupBy", layout.get("groupBy")))
		return layout

	sections = layout.get("sections") or []
	if not isinstance(sections, list) or not sections:
		frappe.throw(_("A dashboard layout needs at least one section."))
	keys = set()
	for si, s in enumerate(sections, start=1):
		_clean_section(s, str(si), 0, keys, assistant)
	return layout


def _clean_group_by(where, value):
	"""groupBy is a key or a list of keys, outermost first."""
	if value is None or value == "":
		return
	names = value if isinstance(value, list) else [value]
	if not names or len(names) > MAX_DEPTH or not all(isinstance(n, str) and n for n in names):
		frappe.throw(_("{0}: groupBy must be a key or a list of up to {1} keys.").format(where, MAX_DEPTH))


def _clean_section(s, label, level, keys, assistant):
	"""Check one section and, recursively, the sections inside it."""
	if level >= MAX_DEPTH:
		frappe.throw(_("Section {0}: sections nest at most {1} levels deep.").format(label, MAX_DEPTH))
	if not isinstance(s, dict):
		frappe.throw(_("Section {0} must be an object.").format(label))
	widgets, children = s.get("widgets") or [], s.get("sections") or []
	if not isinstance(widgets, list) or not isinstance(children, list):
		frappe.throw(_("Section {0}: widgets and sections must be lists.").format(label))
	if not widgets and not children:
		frappe.throw(_("Section {0} has no widgets or sections.").format(label))
	for wi, w in enumerate(widgets, start=1):
		_clean_widget(w, f"{label}, widget {wi}", keys, assistant)
	for ci, child in enumerate(children, start=1):
		_clean_section(child, f"{label}.{ci}", level + 1, keys, assistant)


def _clean_widget(w, label, keys, assistant):
	if not isinstance(w, dict):
		frappe.throw(_("Section {0} must be an object.").format(label))
	key = str(w.get("key") or "")
	if not KEY_RE.fullmatch(key):
		frappe.throw(_("Section {0}: key is required, letters, numbers, _ or -.").format(label))
	if key in keys:
		frappe.throw(_("Widget key {0} is used twice.").format(key))
	keys.add(key)
	if w.get("type") not in WIDGET_TYPES:
		frappe.throw(_("Widget {0}: type must be one of {1}.").format(key, ", ".join(WIDGET_TYPES)))
	for k in ("render", "actions", "onClick"):
		w.pop(k, None)
	if w.get("col") is not None:
		w["col"] = max(1, min(cint(w["col"]), 12))
	if isinstance(w.get("more"), dict):
		w["more"]["href"] = safe_href(w["more"].get("href"))
	_clean_group_by(f"Widget {key}", w.get("groupBy"))
	if w["type"] == "html":
		_clean_html_widget(w, assistant)
	elif "data" in w:
		w["data"] = sanitize(w["data"])


def widget_keys(layout) -> list[str]:
	"""Every widget key, in order, at every depth."""
	out = []

	def walk(sections):
		for s in sections or []:
			out.extend(w["key"] for w in (s.get("widgets") or []) if isinstance(w, dict) and w.get("key"))
			walk(s.get("sections"))

	walk(layout.get("sections"))
	return out


# ---------------------------------------------------------------- filters


def preset_range(name: str, today: date | None = None) -> list[str]:
	t = today or getdate(nowdate())

	def month_end(y, m):
		return (date(y + (m == 12), m % 12 + 1, 1)) - timedelta(days=1)

	q = (t.month - 1) // 3 * 3 + 1
	pq_y, pq = (t.year, q - 3) if q > 1 else (t.year - 1, 10)
	pm_y, pm = (t.year, t.month - 1) if t.month > 1 else (t.year - 1, 12)
	ranges = {
		"today": (t, t),
		"last_7": (t - timedelta(days=6), t),
		"last_30": (t - timedelta(days=29), t),
		"this_month": (t.replace(day=1), month_end(t.year, t.month)),
		"last_month": (date(pm_y, pm, 1), month_end(pm_y, pm)),
		"this_quarter": (date(t.year, q, 1), month_end(t.year, q + 2)),
		"last_quarter": (date(pq_y, pq, 1), month_end(pq_y, pq + 2)),
		"this_year": (date(t.year, 1, 1), date(t.year, 12, 31)),
		"last_year": (date(t.year - 1, 1, 1), date(t.year - 1, 12, 31)),
	}
	a, b = ranges[name]
	return [str(a), str(b)]


def _options(f):
	return [str(o.get("value") if isinstance(o, dict) else o) for o in f.get("options") or []]


def _default(f):
	if f.get("default") is not None:
		return f["default"]
	return 0 if f["type"] == "check" else "this_month" if f["type"] == "daterange" else ""


def _coerce(f, value):
	kind, label = f["type"], f.get("label") or f["key"]
	if kind == "check":
		return 1 if cint(value) else 0
	if value is None or value == "" or value == []:
		return "" if kind != "daterange" else preset_range("this_month")
	if kind == "daterange":
		if isinstance(value, str) and value in PRESETS:
			return preset_range(value)
		if isinstance(value, str) and "," in value:
			value = value.split(",")
		if not (isinstance(value, list) and len(value) == 2):
			frappe.throw(_("{0} must be a preset or two dates.").format(label))
		try:
			return [str(getdate(value[0])), str(getdate(value[1]))]
		except Exception:
			frappe.throw(_("{0} must be two dates.").format(label))
	if kind == "date":
		try:
			return str(getdate(value))
		except Exception:
			frappe.throw(_("{0} must be a date.").format(label))
	if kind == "number":
		return flt(value)
	value = str(value).strip()[:MAX_TEXT]
	if kind in ("select", "segment") and value not in _options(f):
		frappe.throw(_("{0} is not a choice for {1}.").format(value, label))
	return value


def clean_filters(layout, values) -> dict:
	"""Resolve the values a Data Script receives. Unknown keys are dropped."""
	values = parse(values, _("Filters")) or {}
	if not isinstance(values, dict):
		values = {}
	out = {}
	for f in layout.get("filters") or []:
		out[f["key"]] = _coerce(f, values.get(f["key"], _default(f)))
	return out


def saved_filters(page: str, user: str | None = None) -> dict | None:
	raw = frappe.db.get_value(USER_FILTER, {"user": user or frappe.session.user, "page": page}, "filters")
	value = parse(raw) if raw else None
	return value if isinstance(value, dict) else None


def save_filters(page_doc, values) -> dict:
	"""Store raw values (a preset stays a preset) after checking each one."""
	layout = layout_of(page_doc)
	values = parse(values, _("Filters")) or {}
	keep = {}
	for f in layout.get("filters") or []:
		if f["key"] in values:
			_coerce(f, values[f["key"]])
			v = values[f["key"]]
			keep[f["key"]] = v if isinstance(v, (list, int, float)) else str(v)[:MAX_TEXT]
	user = frappe.session.user
	name = frappe.db.get_value(USER_FILTER, {"user": user, "page": page_doc.name})
	payload = json.dumps(keep, sort_keys=True)
	if name:
		frappe.db.set_value(USER_FILTER, name, "filters", payload)
	else:
		frappe.get_doc(
			{"doctype": USER_FILTER, "user": user, "page": page_doc.name, "filters": payload}
		).insert(ignore_permissions=True)
	return keep


def forget_filters(page: str) -> None:
	for name in frappe.get_all(
		USER_FILTER, filters={"user": frappe.session.user, "page": page}, pluck="name"
	):
		frappe.delete_doc(USER_FILTER, name, ignore_permissions=True, force=True)


# ---------------------------------------------------------------- pages and data


def readable_page(name):
	doc = frappe.get_doc(PAGE, name)
	doc.check_permission("read")
	if not doc.enabled:
		frappe.throw(_("This dashboard is disabled."), frappe.PermissionError)
	if not doc.get("layout"):
		frappe.throw(_("This page has no Synapse UI layout."), frappe.DoesNotExistError)
	return doc


def layout_of(doc) -> dict:
	return validate_layout(
		doc.layout, doc.get("view_type") or "Dashboard", doc.get("data_mode") == "Assistant"
	)


def is_assistant(doc) -> bool:
	return doc.get("data_mode") == "Assistant"


def config_for(doc) -> dict:
	"""The config the browser hands to SynapseUI, with the user's saved filters as defaults."""
	layout = layout_of(doc)
	saved = saved_filters(doc.name) or {}
	for f in layout.get("filters") or []:
		if f["key"] in saved:
			f["default"] = saved[f["key"]]
	config = {
		"id": doc.name,
		"title": doc.title,
		"subtitle": doc.get("subtitle"),
		"description": doc.get("description"),
		"group": doc.get("page_group"),
		"keywords": doc.get("keywords"),
		"type": "report" if doc.get("view_type") == "Report" else "dashboard",
		"data_mode": doc.get("data_mode") or "Script",
		"can_edit": bool(frappe.has_permission(PAGE, "write", doc=doc)),
		"has_saved_filters": bool(saved),
		**layout,
	}
	if config["type"] == "report":
		table = config.pop("table", {}) or {}
		for key in REPORT_KEYS:
			if key in table:
				config[key] = table[key]
	if is_assistant(doc):
		config["assistant"] = {
			"notes": doc.get("llm_notes"),
			"updated_on": str(doc.llm_updated_on) if doc.get("llm_updated_on") else None,
			"refresh": doc.get("llm_refresh"),
		}
	return config


def check_data(doc, data):
	"""A dashboard's data is a dict keyed by widget key. A report's is a table payload."""
	if doc.get("view_type") == "Report":
		if not isinstance(data, (list, dict)):
			frappe.throw(_("A report returns rows, or a dict with columns and result."))
		return
	if not isinstance(data, dict):
		frappe.throw(_("A dashboard returns a dict keyed by widget key."))
	unknown = sorted(set(data) - set(widget_keys(layout_of(doc))))
	if unknown:
		frappe.throw(
			_("These keys match no widget: {0}. Widget keys are: {1}.").format(
				", ".join(unknown), ", ".join(widget_keys(layout_of(doc)))
			)
		)


def data_for(doc, filters=None) -> dict | list:
	if is_assistant(doc):
		return sanitize(parse(doc.get("snapshot")) or {})
	if not doc.get("data_script"):
		frappe.throw(_("This dashboard has no Data Script."))
	from synapse.scripts import run_script

	values = clean_filters(layout_of(doc), filters)
	data = run_script(doc.data_script, {"filters": values, **values})
	if len(json.dumps(data, default=str)) > MAX_DATA:
		frappe.throw(_("The Data Script returned too much data."))
	check_data(doc, data)
	return sanitize(data)


def validate_page(doc) -> None:
	"""Called from Synapse Page.validate when the page has a layout."""
	if not doc.get("layout"):
		return
	assistant = is_assistant(doc)
	layout = validate_layout(doc.layout, doc.get("view_type") or "Dashboard", assistant)
	doc.layout = json.dumps(layout, indent=1)
	if assistant:
		if doc.get("data_script"):
			frappe.throw(_("Assistant dashboards keep their data in Snapshot. Remove the Data Script."))
		if doc.get("snapshot"):
			data = parse(doc.snapshot, _("Snapshot"))
			check_data(doc, data)
	elif doc.get("data_script"):
		script = frappe.get_doc("Synapse Script", doc.data_script)
		script.check_permission("read")
		if not script.enabled:
			frappe.throw(_("The Data Script is disabled."))
