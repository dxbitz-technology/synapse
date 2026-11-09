# Copyright (c) 2026, Dxbitz and contributors
"""Dashboard tools for the Synapse app at /synapse.

Read tools describe, list and preview dashboards. The write tools (save and
publish) have their own switch in Synapse Settings and touch only Synapse Pages.
"""

import json

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from synapse import dashboards as dash
from synapse.mcp import mcp
from synapse.mcp_core import ToolAnnotations
from synapse.mcp_tools import audit, settings
from synapse.mcp_tools.policy import READ, WRITE, Denied, check

PAGE = dash.PAGE
REFRESH = {"Hour": {"hours": 1}, "Day": {"days": 1}, "Week": {"weeks": 1}}
MAX_NOTES = 20000

GUIDE = {
	"what": (
		"A Synapse dashboard is a Synapse Page with a Layout in the Synapse UI format and one data source. "
		"Users open it at /synapse#/<page>. The browser makes one data call per load and per filter change. "
		"The data is ONE dict keyed by widget key. Each widget renders the value under its own key."
	),
	"workflow": [
		"1. Call list_dashboards to see what exists. Reuse or change a dashboard before making a new one.",
		"2. Inspect real DocType fields (describe tools) before writing any query. Never guess field names.",
		"3. Script dashboard: a System Manager saves a Synapse Script (create_doc, needs config writes) that returns the data dict. Then save_dashboard with data_mode Script and data_script.",
		"4. Assistant dashboard: save_dashboard with data_mode Assistant and a brief, gather numbers with the read tools, then publish_dashboard_snapshot with the data dict and short notes.",
		"5. Call preview_dashboard_data (Script) and read the result before telling the user it works.",
		"6. On a schedule, call list_dashboards(only_due=True) and refresh each Assistant dashboard that is due.",
	],
	"layout": {
		"shape": {
			"filters": "list of filter objects, optional",
			"sections": "list of {key, title, description, collapsible, collapsed, widgets: [...], sections: [...]} (dashboard view). A section may hold widgets, child sections, or both. Child sections are indented under their parent and collapse on their own. Up to 4 levels.",
			"table": "report view only: {columns, groupBy, totals, sortBy, sortDir, pageSize, search, export}",
			"autoApply": "true (default) reloads on every filter change, false shows an Apply button",
		},
		"widget": "{key, type, col (1-12), colMd, title, subtitle, format, ...type options}. key is required and unique in the page.",
		"grid": "12 columns. Stats usually col 3, a main chart col 8 beside a donut col 4, tables col 12. Narrow screens restack on their own.",
		"nesting": "Use child sections to drill from a summary into detail, for example Sales > By customer > Overdue. Start detail levels collapsed (collapsed: true) so the page opens short. Keep the top level for the headline numbers.",
		"forbidden": "No functions, method, fetch, render or actions in a layout. The server strips them.",
	},
	"widgets": {
		"stat": {
			"options": "label, format, deltaFormat, inverse (true when a rise is bad), hint",
			"data": "a number, or {value, delta, spark: [numbers], hint}",
		},
		"bar | line | area | dot | pie | donut | split": {
			"options": "format, axisFormat, height, stacked, horizontal (bar, dot), smooth, area (line), values (bar labels), centerLabel (donut), labelKey, valueKeys, seriesNames, series, legend",
			"data": [
				"{label: number, ...} for one series",
				"{labels: [...], values: [...]}",
				"{labels: [...], series: {Name: [...], Other: [...]}}",
				"[{month: 'Jan', sales: 10, cost: 6}, ...] SQL rows: first text column is the label, numeric columns are series",
			],
			"notes": "Keep to 8 series or fewer. pie and split fold the rest into Other.",
		},
		"list": {
			"options": "size sm|lg, format, limit, empty, more: {label, href}, groupBy (a key, or a list of keys for groups inside groups), collapsed",
			"data": "[{title, subtitle, value, format, meta, status, indicator, href}] where status is a word like Paid or Overdue, or {label, color}",
		},
		"table": {
			"options": "columns, groupBy (a key, or a list of up to 4 keys: ['customer', 'status'] groups by customer then status, each level indented with its own subtotals), collapsed (true, false, or a level number: 1 keeps the first level open and closes deeper ones), totals, sortBy, sortDir, pageSize, search, export",
			"data": "rows (list of dicts), or {columns, result}. Columns use Frappe style {fieldname, label, fieldtype, options}. Link columns link to the record.",
		},
		"html": {
			"options": "template with {{field}} or {{field | format}}, css",
			"data": "a dict for the template",
			"notes": "Script dashboards only. The template is sanitised. Prefer the typed widgets.",
		},
		"value overrides": "Any widget value may be {data: ..., title: ..., ...}. The other keys override widget options for that load.",
	},
	"formats": "number, number:0, int, currency (AED), currency:USD, compact, ccompact, percent (value already in %), percent:0, date (DD-MM-YYYY), datetime, text, check",
	"filters": {
		"types": {
			"select": "options: ['A','B'] or [{value,label}]. Sends a string, empty means All.",
			"segment": "same options, drawn as buttons.",
			"daterange": "default a preset (today, last_7, last_30, this_month, last_month, this_quarter, last_quarter, this_year, last_year) or two dates. Sends [from, to] as YYYY-MM-DD.",
			"date": "sends YYYY-MM-DD.",
			"link": "doctype: 'Customer'. Sends the record name.",
			"check": "sends 0 or 1.",
			"text | number": "sends the value.",
		},
		"common": "Every filter has key, label and default. Users can save their own filter values. Saved values become their defaults.",
	},
	"data_script": {
		"receives": "args['filters'] with every filter key resolved (daterange already [from, to]). The same keys are also at the top level of args.",
		"returns": "assign result = {widget_key: value, ...}. Keys that match no widget are refused. A report returns rows or {columns, result}.",
		"helpers": "query(sql, values) for bound read-only SQL (System Manager with SQL access), frappe.get_list and frappe.get_count (keep Synapse grants and Frappe permissions), frappe.session.user.",
		"limits": "No imports, writes or network. Variables made in the script are not visible inside list or dict comprehensions, so build lists with for loops. get_list order_by takes one field.",
		"example": (
			'f = args["filters"]\n'
			'rows = query("""select customer, sum(base_grand_total) as total from `tabSales Order`\n'
			"\twhere docstatus = 1 and transaction_date between %(a)s and %(b)s\n"
			'\tgroup by customer order by total desc limit 10""", {"a": f["period"][0], "b": f["period"][1]})\n'
			"total = 0\n"
			"for r in rows:\n"
			'\ttotal += r["total"]\n'
			'result = {"order_value": {"value": total}, "by_customer": rows}'
		),
	},
	"assistant": {
		"what": "data_mode Assistant stores the data dict in Snapshot. Use it for reasoning heavy views: summaries, risks, picks, things a query cannot decide.",
		"publish": "publish_dashboard_snapshot(page, data, notes). data uses the same keys and shapes as a script would return. Notes are 2 to 5 short plain sentences shown above the widgets: what changed, why it matters, what to do.",
		"layout": "You may change the layout with save_dashboard whenever the story needs a different view. html widgets are not allowed here.",
		"filters": "Filters do nothing on Assistant dashboards. Put the period in the notes or titles instead.",
	},
	"example_layout": {
		"filters": [
			{"key": "period", "label": "Period", "type": "daterange", "default": "this_year"},
			{"key": "customer", "label": "Customer", "type": "link", "doctype": "Customer"},
		],
		"sections": [
			{
				"key": "kpi",
				"collapsible": False,
				"widgets": [
					{
						"key": "order_value",
						"type": "stat",
						"col": 4,
						"label": "Order value",
						"format": "currency",
					},
				],
			},
			{
				"key": "customers",
				"title": "Customers",
				"widgets": [
					{
						"key": "by_customer",
						"type": "bar",
						"col": 12,
						"title": "Top customers",
						"horizontal": True,
						"format": "ccompact",
					},
				],
			},
		],
	},
	"style": "Plain short titles, AED amounts with format currency or ccompact, dates shown DD-MM-YYYY by the kit.",
}


def _gate_write():
	if not settings.dashboard_tools_enabled():
		raise Denied(
			"Dashboard tools are switched off (Synapse Settings), or none of your Synapse profiles grant write on Synapse Page."
		)
	if WRITE in settings.get_policy().blocked_actions(PAGE):
		raise Denied("Synapse Page is blocked for write by this site's Synapse backstop.")


def _due(row) -> bool:
	if row.get("data_mode") != "Assistant":
		return False
	every = REFRESH.get(row.get("llm_refresh") or "Day")
	if not row.get("llm_updated_on"):
		return True
	if not every:
		return False
	return add_to_date(get_datetime(row.llm_updated_on), **every) <= now_datetime()


@mcp.tool(
	annotations=ToolAnnotations(title="Dashboard guide", readOnlyHint=True),
	enabled=settings.read_tools_enabled,
)
@audit.audited(audit.READ)
def get_dashboard_guide():
	"""Read this first before you build, change or refresh any Synapse dashboard.

	Returns the layout format, every widget type with the data shape it takes,
	filter types and what a Data Script receives, the Assistant snapshot rules,
	and a worked example."""

	check(settings.get_policy(), READ, PAGE)
	return GUIDE


@mcp.tool(
	annotations=ToolAnnotations(title="List dashboards", readOnlyHint=True),
	enabled=settings.read_tools_enabled,
)
@audit.audited(audit.READ)
def list_dashboards(only_due: bool = False):
	"""List Synapse app dashboards you can read, with their data source and whether an Assistant refresh is due.

	Args:
	        only_due: Return only Assistant dashboards whose refresh time has passed."""

	check(settings.get_policy(), READ, PAGE)
	audit.current().target(PAGE)
	rows = frappe.get_list(
		PAGE,
		filters={"layout": ["is", "set"]},
		fields=[
			"name",
			"title",
			"enabled",
			"page_group",
			"description",
			"view_type",
			"data_mode",
			"data_script",
			"llm_instructions",
			"llm_refresh",
			"llm_updated_on",
		],
		order_by="page_group asc, title asc",
		limit_page_length=0,
	)
	out = []
	for r in rows:
		due = _due(r)
		if only_due and not due:
			continue
		out.append(
			{
				"page": r.name,
				"title": r.title,
				"enabled": bool(r.enabled),
				"group": r.page_group,
				"description": r.description,
				"view": r.view_type,
				"data_source": r.data_mode,
				"data_script": r.data_script,
				"brief": r.llm_instructions if r.data_mode == "Assistant" else None,
				"refresh_every": r.llm_refresh if r.data_mode == "Assistant" else None,
				"last_updated": str(r.llm_updated_on) if r.llm_updated_on else None,
				"due": due,
				"url": frappe.utils.get_url(f"/synapse#/{r.name}"),
			}
		)
	audit.current().rows(len(out))
	return {"dashboards": out}


@mcp.tool(
	annotations=ToolAnnotations(title="Get a dashboard", readOnlyHint=True),
	enabled=settings.read_tools_enabled,
)
@audit.audited(audit.READ)
def get_dashboard(page: str):
	"""Return one dashboard's full definition: layout, data source, brief and the current snapshot.

	Args:
	        page: The Synapse Page name."""

	check(settings.get_policy(), READ, PAGE)
	audit.current().target(PAGE, page)
	doc = frappe.get_doc(PAGE, page)
	doc.check_permission("read")
	layout = dash.parse(doc.layout) or {}
	return {
		"page": doc.name,
		"title": doc.title,
		"enabled": bool(doc.enabled),
		"view": doc.view_type,
		"data_source": doc.data_mode,
		"group": doc.page_group,
		"subtitle": doc.subtitle,
		"description": doc.description,
		"keywords": doc.keywords,
		"layout": layout,
		"widget_keys": dash.widget_keys(layout) if isinstance(layout, dict) else [],
		"data_script": doc.data_script,
		"brief": doc.llm_instructions,
		"refresh_every": doc.llm_refresh,
		"notes": doc.llm_notes,
		"last_updated": str(doc.llm_updated_on) if doc.llm_updated_on else None,
		"snapshot": dash.parse(doc.snapshot) if doc.data_mode == "Assistant" else None,
		"url": frappe.utils.get_url(f"/synapse#/{doc.name}"),
	}


@mcp.tool(
	annotations=ToolAnnotations(title="Preview dashboard data", readOnlyHint=True),
	enabled=settings.read_tools_enabled,
)
@audit.audited(audit.READ)
def preview_dashboard_data(page: str, filters: dict | None = None):
	"""Run a dashboard's data load exactly as the browser does and report which widgets got data.

	Args:
	        page: The Synapse Page name.
	        filters: Optional filter values by key. Missing keys use the defaults."""

	check(settings.get_policy(), READ, PAGE)
	audit.current().target(PAGE, page)
	doc = frappe.get_doc(PAGE, page)
	doc.check_permission("read")
	if doc.data_script:
		check(settings.get_policy(), READ, "Synapse Script")
	layout = dash.layout_of(doc)
	data = dash.data_for(doc, filters or {})
	keys = dash.widget_keys(layout)
	return {
		"filters_used": {} if dash.is_assistant(doc) else dash.clean_filters(layout, filters or {}),
		"data": data,
		"widgets_without_data": [k for k in keys if not (isinstance(data, dict) and k in data)]
		if doc.view_type != "Report"
		else [],
	}


@mcp.tool(
	annotations=ToolAnnotations(
		title="Create or change a dashboard", readOnlyHint=False, destructiveHint=True
	),
	enabled=settings.dashboard_tools_enabled,
)
@audit.audited(audit.WRITE)
def save_dashboard(
	page: str,
	layout: dict,
	title: str | None = None,
	data_source: str | None = None,
	data_script: str | None = None,
	view: str | None = None,
	group: str | None = None,
	subtitle: str | None = None,
	description: str | None = None,
	keywords: str | None = None,
	brief: str | None = None,
	refresh_every: str | None = None,
	enabled: bool | None = None,
	validate_only: bool = False,
):
	"""Create a dashboard, or replace the definition of an existing one. Read get_dashboard_guide first.

	The layout is checked before anything is saved. On an existing dashboard, any
	argument you leave out keeps its current value. Existing Assistant data is kept
	unless a widget it belongs to is removed, in which case publish a new snapshot.

	Args:
	        page: Lowercase slug, for example sales-overview. Used in /synapse#/<page>.
	        layout: The Synapse UI layout object (filters, sections or table).
	        title: Display title. Required for a new dashboard.
	        data_source: Script or Assistant. New dashboards default to Script.
	        data_script: Synapse Script name, required for Script dashboards.
	        view: Dashboard or Report. New dashboards default to Dashboard.
	        group: Sidebar group, for example Sales.
	        subtitle: One line under the title.
	        description: One line for search and the sidebar tooltip.
	        keywords: Extra search words.
	        brief: Assistant dashboards: what to track and how to judge it.
	        refresh_every: Assistant dashboards: Hour, Day, Week or On Request.
	        enabled: Show it in the app. New dashboards default to enabled.
	        validate_only: Check everything and save nothing."""

	_gate_write()
	audit.current().target(PAGE, page)
	exists = frappe.db.exists(PAGE, page)
	doc = frappe.get_doc(PAGE, page) if exists else frappe.new_doc(PAGE)
	data_source = data_source or doc.get("data_mode") or "Script"
	view = view or doc.get("view_type") or "Dashboard"
	if data_source == "Script" and data_script is None:
		data_script = doc.get("data_script")
	if enabled is None:
		enabled = bool(doc.enabled) if exists else True
	if data_source not in ("Script", "Assistant"):
		frappe.throw("data_source must be Script or Assistant.")
	if view not in ("Dashboard", "Report"):
		frappe.throw("view must be Dashboard or Report.")
	if refresh_every and refresh_every not in ("Hour", "Day", "Week", "On Request"):
		frappe.throw("refresh_every must be Hour, Day, Week or On Request.")

	if exists:
		doc.check_permission("write")
	else:
		if not title:
			frappe.throw("A new dashboard needs a title.")
		doc.page_name = page
		frappe.has_permission(PAGE, "create", throw=True)

	values = {
		"title": title or doc.title,
		"enabled": 1 if enabled else 0,
		"data_mode": data_source,
		"view_type": view,
		"layout": json.dumps(layout),
		"data_script": data_script if data_source == "Script" else None,
		"page_group": group if group is not None else doc.get("page_group"),
		"subtitle": subtitle if subtitle is not None else doc.get("subtitle"),
		"description": description if description is not None else doc.get("description"),
		"keywords": keywords if keywords is not None else doc.get("keywords"),
	}
	if data_source == "Assistant":
		values["llm_instructions"] = brief if brief is not None else doc.get("llm_instructions")
		values["llm_refresh"] = refresh_every or doc.get("llm_refresh") or "Day"
		snapshot = dash.parse(doc.get("snapshot")) or {}
		if isinstance(snapshot, dict) and view == "Dashboard" and isinstance(layout, dict):
			keys = set(dash.widget_keys(layout))
			values["snapshot"] = json.dumps({k: v for k, v in snapshot.items() if k in keys})
	doc.update(values)

	if validate_only:
		doc.run_method("validate")
		return {"valid": True, "page": page, "widget_keys": dash.widget_keys(dash.layout_of(doc))}

	doc.save()
	audit.current().rows(1)
	return {
		"page": doc.name,
		"created": not exists,
		"widget_keys": dash.widget_keys(dash.layout_of(doc)),
		"url": frappe.utils.get_url(f"/synapse#/{doc.name}"),
	}


@mcp.tool(
	annotations=ToolAnnotations(
		title="Publish an Assistant dashboard snapshot",
		readOnlyHint=False,
		destructiveHint=True,
		idempotentHint=True,
	),
	enabled=settings.dashboard_tools_enabled,
)
@audit.audited(audit.WRITE)
def publish_dashboard_snapshot(page: str, data: dict | list, notes: str | None = None):
	"""Store fresh data on an Assistant dashboard. Users see it on their next load.

	Args:
	        page: The Synapse Page name. Its data source must be Assistant.
	        data: Dashboard: a dict keyed by widget key, same shapes as get_dashboard_guide.
	              Report: rows, or {columns, result}.
	        notes: 2 to 5 short plain sentences shown above the widgets."""

	_gate_write()
	audit.current().target(PAGE, page)
	doc = frappe.get_doc(PAGE, page)
	doc.check_permission("write")
	if not dash.is_assistant(doc):
		frappe.throw("This dashboard runs a Data Script. Only Assistant dashboards take snapshots.")
	if not doc.layout:
		frappe.throw("Save a layout with save_dashboard first.")
	dash.check_data(doc, data)
	doc.snapshot = json.dumps(dash.sanitize(data))
	if notes is not None:
		doc.llm_notes = str(notes)[:MAX_NOTES]
	doc.llm_updated_on = now_datetime()
	doc.save()
	audit.current().rows(1)
	return {
		"page": doc.name,
		"updated_on": str(doc.llm_updated_on),
		"url": frappe.utils.get_url(f"/synapse#/{doc.name}"),
	}
