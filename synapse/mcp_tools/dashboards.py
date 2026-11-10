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
	"rules": [
		"Never write Python files, server code or patches for a dashboard, and never ask the user to install anything. Everything is saved through these tools.",
		"Build with data_source Query unless you have a reason not to. It needs no code, runs live, and filters work.",
		"Do not guess. Check fields with describe_doctype and numbers with aggregate before you save.",
		"Filters on ERP records (customer, item, sales person and so on) are always link filters with a doctype, never free text.",
		"save_dashboard checks the data before saving. If it fails, fix what the error names and call it again. Do not try other routes.",
		"Answer the user in plain words: what the page shows, its link, and its limits. No JSON, no field names unless asked.",
	],
	"choose_data_source": {
		"Query": "Default. Each widget has a query (DocType, metrics, grouping, time buckets). Live on every load, works with filters. Covers totals, counts, averages, trends, rankings and lists of top items.",
		"Assistant": "For judgement a query cannot make: summaries, risks, picks, commentary. You store the data with publish_dashboard_snapshot and refresh it later. No filters, so build one page per period or company if the user needs several.",
		"Script": "Only when Query cannot express it, for example ratios across two DocTypes in one figure. Needs a System Manager to save a Synapse Script and bench server scripts on. Prefer two Query widgets over one Script.",
	},
	"tell_the_user": {
		"Query": "Live data, filters work, no upkeep.",
		"Assistant": "Kept up to date by the assistant on a schedule, no filters, carries notes. Suggest separate pages for separate periods or companies.",
		"Script": "Live data from a saved script, filters work.",
	},
	"steps_build": [
		"1. list_dashboards: reuse or extend a page that already covers the request.",
		"2. describe_doctype on the main DocType. Use real fieldnames.",
		"3. aggregate to check the numbers look right (for example sum:base_grand_total by month).",
		"4. save_dashboard once with the full layout. Read check in the reply. Every widget should have data.",
		"5. Assistant only: before saving, ask how often to refresh and recommend one. After saving, publish_dashboard_snapshot with the data and 2 to 5 short notes, then offer a scheduled refresh.",
		"6. Reply with the link and a one line description of each section.",
		"Script pages: follow script.write_it_fast and script.test_and_fix before saving.",
	],
	"steps_study_my_data": [
		"1. list_available_doctypes, then get_count on the main transaction DocTypes of the module (Sales: Sales Invoice, Sales Order, Quotation, Customer).",
		"2. aggregate by month and by the main party or item to see volume, trend and concentration.",
		"3. Suggest 2 to 4 pages in plain words: what each shows, Query or Assistant, and why.",
		"4. Build the ones the user picks. One page per topic is easier to read than one large page.",
	],
	"query": {
		"shape": '{"doctype": "Sales Invoice", "metrics": ["sum:base_grand_total", "count"], "group_by": ["customer"], "period": {"field": "posting_date", "by": "month"}, "filters": {"docstatus": 1}, "order_by": "sum_base_grand_total desc", "limit": 10}',
		"metrics": "count, sum:<field>, avg:<field>, min:<field>, max:<field>. Result columns are named count, sum_<field>, avg_<field> and so on.",
		"group_by": "Up to 3 fields. The first one labels the chart or list.",
		"period": "Buckets a Date or Datetime field by day, week, month, quarter or year. Result column is period.",
		"filters": "Fixed conditions, same form as get_list. Add docstatus 1 for submitted documents. Use base_ amount fields for company currency. Invoice totals net out returns and credit notes. Add is_return 0 when the user means gross sales, and say which one the widget shows.",
		"bind": 'On the widget, maps page filters to fields: {"period": "posting_date", "customer": "customer"}. A daterange becomes a between filter. Empty filters are skipped. For a field in a child table use "Child DocType.field", for example {"sales_person": "Sales Team.sales_person"} on Sales Invoice.',
		"what_each_widget_gets": "stat: the first metric summed, plus a sparkline when period is set. bar, line, area, donut, pie: the result rows, label column first. list: first group as title, first metric as value. table: all columns.",
	},
	"layout": {
		"shape": '{"filters": [...], "sections": [{"key", "title", "collapsed", "widgets": [...], "sections": [...]}]}. Sections nest up to 4 levels. A report uses {"filters", "query", "bind", "table": {"groupBy", "totals"}} with view Report.',
		"widget": "{key, type, col (1-12), title, format, query, bind, ...options}. key is unique in the page.",
		"types": "stat, bar, line, area, dot, pie, donut, split, list, table. html is for Script pages only.",
		"good_page": "A row of 3 or 4 stats (col 3 or 4), a trend line (col 8) beside a donut or ranked bar (col 4), then a list or table. Put detail in a collapsed child section.",
		"options": "stat: label, format, inverse (a rise is bad). bar: horizontal, stacked, values. line: area, smooth. donut: centerLabel. chart rows: labelKey, valueKeys, seriesNames {column: label}. list: limit, more {label, href}, groupBy. table: groupBy (list allowed), totals, sortBy.",
		"formats": "currency (AED), currency:USD, ccompact (AED 1.2M), compact, int, number:0, percent (value already in %), date, text.",
	},
	"filters": {
		"types": "daterange (default a preset: this_month, last_month, this_quarter, this_year, last_30 ...), select (options), link (doctype), date, check, text, number, segment.",
		"rules": "Every filter has key, label, default. Bind each one on the widgets it should affect. Users can save their own values.",
		"erp_records": "A filter on ERP records (customer, item, sales person, territory, company, project...) must be type link with its doctype, so users pick from a searchable list. Never use text for these. Choices from a Select field use type select. Synapse also turns a text filter into a link or select when it is bound to a Link or Select field, or named after a DocType.",
	},
	"assistant": {
		"publish": "publish_dashboard_snapshot(page, data, notes). data is a dict keyed by widget key in the shapes listed under what_each_widget_gets. Build it from aggregate results.",
		"notes": "2 to 5 short plain sentences: what changed, why it matters, what to do.",
		"interval": "Before saving, ask the user how often the page should refresh (Hour, Day, Week, On Request) and recommend one: Day for most pages, Week for briefs and summaries, Hour for live operations. save_dashboard refuses a new Assistant page without refresh_every.",
		"schedule": "Synapse cannot start you by itself. After publishing, tell the user so, and offer to create a scheduled task in their assistant with the prompt from the reply, at the chosen interval. If you cannot schedule tasks, give them the prompt to schedule themselves.",
		"refresh": "When the task runs, call list_dashboards(only_due=True), read each brief, gather fresh numbers with aggregate, and publish again. The page shows an overdue warning when a refresh is missed.",
	},
	"script": {
		"receives": "args['filters'] with resolved values (daterange is [from, to]).",
		"returns": "result = {widget_key: value}. Same shapes as Query widgets get.",
		"helpers": "frappe.aggregate(doctype, metrics=..., group_by=..., period=..., filters=...) returns rows. frappe.get_list and frappe.get_count. query(sql, values) only when SQL access is on.",
		"limits": 'Frappe safe exec: no imports, no writes, no network, no other scripts. No names or dict keys that start with _ (row["_x"] fails), use plain names. get_list order_by takes one field. One run may make 200 data calls, read 50,000 rows in total and run 30 seconds (120 when the app runs it in the background), or it is stopped. One query() may return all the rows the run has left, so never page with LIMIT and OFFSET.',
		"how_it_runs": "The Synapse app runs Script pages in a background job and keeps each user's result for 5 minutes, so the page shows a loader on the first open and is instant after. A fast script still matters: every filter change is a new run.",
		"write_it_fast": [
			"Let the database do the work: SUM, COUNT and GROUP BY in SQL, so each query returns summary rows. Never read raw ledger rows (GL Entry, Stock Ledger Entry, Payment Ledger Entry) into Python to add them up.",
			"One query per topic: group by month, company or party in a single query rather than one query per month or per company in a loop.",
			"Never query inside a loop over rows. Collect the names, then one query with IN %(names)s.",
			"Filter on indexed fields first: company, posting_date or transaction_date ranges, docstatus, is_cancelled. Keep functions off columns in WHERE (write posting_date between %(from)s and %(to)s, not year(posting_date) = 2026).",
			"No ORDER BY unless the order is shown. No SELECT *; name the columns.",
			"Stock ageing and similar FIFO work: bucket in SQL with datediff and SUM per item and age band, or give it its own page.",
			"Only compute what the page shows. Split a large page into one page per topic (finance, sales, operations, stock), so each load runs only its own queries.",
		],
		"test_and_fix": [
			'1. After writing or changing a Synapse Script, run execute_synapse_script with args shaped like the page sends: {"filters": {...}} plus the same keys at the top level. Try the default filters and the widest likely ones (all companies, a full year).',
			"2. Read cost in the reply. If advice is not empty, or a run was stopped, change the script following write_it_fast and run it again. Repeat until it loads with empty advice.",
			"3. If it fails, read the error and the line it names, fix the script, and run it again. Do not save the page until the script runs cleanly.",
			"4. Then preview_dashboard_data on the page: every widget should be listed with data and widgets_without_data should be empty.",
			"5. Tell the user how long the run took and anything you changed to make it faster.",
		],
	},
	"example": {
		"call": "save_dashboard",
		"page": "sales-overview",
		"title": "Sales Overview",
		"data_source": "Query",
		"layout": {
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
							"key": "sales",
							"type": "stat",
							"col": 4,
							"label": "Sales",
							"format": "currency",
							"query": {
								"doctype": "Sales Invoice",
								"metrics": ["sum:base_grand_total"],
								"period": {"field": "posting_date", "by": "month"},
								"filters": {"docstatus": 1},
							},
							"bind": {"period": "posting_date", "customer": "customer"},
						},
						{
							"key": "due",
							"type": "stat",
							"col": 4,
							"label": "Outstanding",
							"format": "currency",
							"inverse": True,
							"query": {
								"doctype": "Sales Invoice",
								"metrics": ["sum:outstanding_amount"],
								"filters": {"docstatus": 1},
							},
							"bind": {"customer": "customer"},
						},
						{
							"key": "invoices",
							"type": "stat",
							"col": 4,
							"label": "Invoices",
							"format": "int",
							"query": {
								"doctype": "Sales Invoice",
								"metrics": ["count"],
								"filters": {"docstatus": 1},
							},
							"bind": {"period": "posting_date", "customer": "customer"},
						},
					],
				},
				{
					"key": "trend",
					"title": "Trend",
					"widgets": [
						{
							"key": "monthly",
							"type": "line",
							"col": 8,
							"title": "Sales by month",
							"format": "ccompact",
							"area": True,
							"seriesNames": {"sum_base_grand_total": "Sales"},
							"query": {
								"doctype": "Sales Invoice",
								"metrics": ["sum:base_grand_total"],
								"period": {"field": "posting_date", "by": "month"},
								"filters": {"docstatus": 1},
							},
							"bind": {"period": "posting_date", "customer": "customer"},
						},
						{
							"key": "top",
							"type": "bar",
							"col": 4,
							"title": "Top customers",
							"horizontal": True,
							"format": "ccompact",
							"seriesNames": {"sum_base_grand_total": "Sales"},
							"query": {
								"doctype": "Sales Invoice",
								"metrics": ["sum:base_grand_total"],
								"group_by": ["customer"],
								"filters": {"docstatus": 1},
								"limit": 8,
							},
							"bind": {"period": "posting_date"},
						},
					],
				},
			],
		},
	},
}


def _gate_write():
	if not settings.dashboard_tools_enabled():
		raise Denied(
			"Dashboard tools are switched off (Synapse Settings), or none of your Synapse profiles grant write on Synapse Page."
		)
	if WRITE in settings.get_policy().blocked_actions(PAGE):
		raise Denied("Synapse Page is blocked for write by this site's Synapse backstop.")


def _due(row) -> bool:
	return dash.refresh_due(row)


REFRESH_ADVICE = (
	"Day suits most pages (sales, receivables, stock). Week suits briefs, trends and management summaries. "
	"Hour suits live operations such as open orders or today's collections. On Request suits one-off analyses."
)


def _refresh_prompt() -> str:
	import frappe

	return f"Refresh my due Synapse dashboards on {frappe.local.site}."


def _schedule_note(doc) -> dict:
	"""What the user must know about keeping an Assistant page fresh."""
	every = doc.get("llm_refresh") or "Day"
	if every == "On Request":
		tell = 'This page refreshes only when you ask me to. Say "refresh my Synapse dashboards" any time.'
	else:
		tell = (
			f"This page should refresh every {every.lower()}, but Synapse cannot start me by itself. "
			f"I can set up a scheduled task in your assistant that runs every {every.lower()}, or you can ask me to refresh it any time. "
			"Until a refresh runs, the page keeps its last snapshot and shows when it is overdue."
		)
	return {
		"refresh_every": every,
		"tell_the_user": tell,
		"scheduled_task_prompt": _refresh_prompt(),
		"offer": "Offer to create that scheduled task if your client can schedule tasks. Otherwise give the user the prompt to schedule.",
	}


@mcp.tool(
	annotations=ToolAnnotations(title="Dashboard guide", readOnlyHint=True),
	enabled=settings.read_tools_enabled,
)
@audit.audited(audit.READ)
def get_dashboard_guide():
	"""Read this first, before building, changing or refreshing any Synapse dashboard, and before suggesting one.

	Returns the rules, how to choose between Query, Assistant and Script, the steps
	for "build me a dashboard" and "study my data", the query and layout formats,
	a complete example, and what you can do on this site right now."""

	check(settings.get_policy(), READ, PAGE)
	return {"your_access": _access(), **GUIDE}


def _access() -> dict:
	"""What this user can do now, and what to tell them when something is missing."""
	import frappe
	from frappe.utils.safe_exec import is_safe_exec_enabled

	policy = settings.get_policy()
	can_save = settings.dashboard_tools_enabled()
	scripts_on = is_safe_exec_enabled()
	can_write_scripts = (
		policy.write_enabled
		and "System Manager" in frappe.get_roles()
		and "write" in policy.granted_actions("Synapse Script")
		and "write" not in policy.blocked_actions("Synapse Script")
	)
	out = {
		"save_dashboards": can_save,
		"query_dashboards": can_save,
		"assistant_dashboards": can_save,
		"script_dashboards": can_save and scripts_on and can_write_scripts,
		"sql": settings.sql_tool_enabled(),
	}
	if not can_save:
		out["tell_the_user"] = (
			"I can read your data but cannot save dashboards yet. A System Manager needs to turn on "
			"Dashboard tools in Synapse Settings and give your Synapse Profile write access to Synapse Page."
		)
		out["do_not"] = "Do not create the Synapse Page with create_doc instead. Wait for the switch."
	elif not out["script_dashboards"]:
		out["note"] = (
			"Use Query or Assistant. Script dashboards are not available to you here, and you do not need them."
		)
	return out


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
	cost = frappe.local.synapse_last_cost if dash.is_script(doc) else None
	return {
		"filters_used": {} if dash.is_assistant(doc) else dash.clean_filters(layout, filters or {}),
		"cost": cost,
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
	"""Create a dashboard, or replace one, in a single call. Read get_dashboard_guide first.

	Query and Script dashboards load their data once before saving. If any widget
	fails, nothing is saved and the error names the widget. On success the reply
	shows what each widget got, so you can report back without another call.
	On an existing dashboard, any argument you leave out keeps its current value.

	Args:
	        page: Lowercase slug, for example sales-overview. Used in /synapse#/<page>.
	        layout: The Synapse UI layout object (filters, sections or table).
	        title: Display title. Required for a new dashboard.
	        data_source: Query (widgets carry their own query, live, filters work, no code),
	                Script (one Synapse Script returns all data) or Assistant (you store the
	                data with publish_dashboard_snapshot, no filters). New dashboards default
	                to Query when a widget has a query, else Script when data_script is set.
	        data_script: Synapse Script name, required for Script dashboards.
	        view: Dashboard or Report. New dashboards default to Dashboard.
	        group: Sidebar group, for example Sales.
	        subtitle: One line under the title.
	        description: One line for search and the sidebar tooltip.
	        keywords: Extra search words.
	        brief: Assistant dashboards: what to track and how to judge it.
	        refresh_every: Assistant dashboards, required when creating one: Hour, Day, Week or
	                On Request. Ask the user first and recommend one: Day for most pages, Week
	                for briefs and summaries, Hour for live operations.
	        enabled: Show it in the app. New dashboards default to enabled.
	        validate_only: Check everything and save nothing."""

	_gate_write()
	audit.current().target(PAGE, page)
	exists = frappe.db.exists(PAGE, page)
	doc = frappe.get_doc(PAGE, page) if exists else frappe.new_doc(PAGE)
	if not data_source:
		has_query = isinstance(layout, dict) and (
			layout.get("query") or any(w.get("query") for w in dash._widgets(layout))
		)
		data_source = doc.get("data_mode") if exists else ("Query" if has_query else "Script")
	view = view or doc.get("view_type") or "Dashboard"
	if data_source == "Script" and data_script is None:
		data_script = doc.get("data_script")
	if enabled is None:
		enabled = bool(doc.enabled) if exists else True
	if data_source not in ("Query", "Script", "Assistant"):
		frappe.throw("data_source must be Query, Script or Assistant.")
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
		if not refresh_every and (not exists or not doc.get("llm_refresh")):
			frappe.throw(
				"Not saved. Ask the user how often this page should refresh: Hour, Day, Week or On Request, "
				f"and recommend one. {REFRESH_ADVICE} Then call save_dashboard again with refresh_every."
			)
		if not (brief or doc.get("llm_instructions")):
			frappe.throw("Not saved. An Assistant page needs a brief: what to track and how to judge it.")
		values["llm_instructions"] = brief if brief is not None else doc.get("llm_instructions")
		values["llm_refresh"] = refresh_every or doc.get("llm_refresh")
		snapshot = dash.parse(doc.get("snapshot")) or {}
		if isinstance(snapshot, dict) and view == "Dashboard" and isinstance(layout, dict):
			keys = set(dash.widget_keys(layout))
			values["snapshot"] = json.dumps({k: v for k, v in snapshot.items() if k in keys})
	doc.update(values)

	doc.run_method("validate")
	loaded = _first_load(doc)
	if validate_only:
		return {"valid": True, "page": page, "saved": False, "check": loaded}

	doc.save()
	audit.current().rows(1)
	return {
		"page": doc.name,
		"created": not exists,
		"data_source": doc.data_mode,
		"url": frappe.utils.get_url(f"/synapse#/{doc.name}"),
		"check": loaded,
		"next": (
			"Publish data with publish_dashboard_snapshot, then tell the user the link and the schedule note."
			if dash.is_assistant(doc)
			else "Tell the user the link. Filters work in the app."
		),
		**({"schedule": _schedule_note(doc)} if dash.is_assistant(doc) else {}),
	}


def _first_load(doc):
	"""Load the data the way the browser will. A failure stops the save."""
	if dash.is_assistant(doc):
		return {"note": "Assistant dashboard. It shows nothing until you publish a snapshot."}
	try:
		data = dash.data_for(doc, {})
	except Exception as error:
		hint = ""
		if not dash.is_query(doc) and "server script" in str(error).lower():
			hint = " Server scripts are off on this bench. Use data_source Query instead, it needs no script."
		frappe.throw(f"Not saved. The first data load failed: {error}.{hint}")
	if doc.view_type == "Report":
		rows = (data.get("result") if isinstance(data, dict) else data) or []
		return {"rows": len(rows)}
	summary = {}
	for key in dash.widget_keys(dash.layout_of(doc)):
		value = data.get(key) if isinstance(data, dict) else None
		if value is None:
			summary[key] = "no data"
		elif isinstance(value, dict) and "value" in value:
			summary[key] = value["value"]
		elif isinstance(value, dict) and "result" in value:
			summary[key] = f"{len(value['result'])} rows"
		elif isinstance(value, (list, dict)):
			summary[key] = f"{len(value)} rows"
		else:
			summary[key] = value
	return {"widgets": summary}


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
		"schedule": _schedule_note(doc),
	}
