# Synapse

An MCP server for Frappe 16 and ERPNext, with access profiles, an audit log and
a dashboard app.

- [Documentation](https://github.com/dxbitz-technology/synapse/wiki/Documentation)
- [Endpoints](https://github.com/dxbitz-technology/synapse/wiki/Endpoints)
- [Privacy policy](https://github.com/dxbitz-technology/synapse/wiki/Privacy-Policy)
- [Terms of Service](https://github.com/dxbitz-technology/synapse/wiki/Terms-of-Service)
- [Issues](https://github.com/dxbitz-technology/synapse/issues)

For security reports, email info@dxbitz.com.

Licensed under AGPL-3.0-or-later. The adapted MCP core includes its original
[MIT notice](synapse/mcp_core/LICENSE).

## Setup

```sh
bench get-app https://github.com/dxbitz-technology/synapse
bench --site your.site install-app synapse
bench build --app synapse
```

Query and Assistant dashboards need nothing more. Script dashboards run through
Frappe's safe exec, which is a bench setting that enables Server Scripts on every
site of the bench. Turn it on only if you need Script dashboards:

```sh
bench set-config -g server_script_enabled 1
```

Then open **Synapse Settings** in Desk, enable the endpoint, and create a
**Synapse Profile** for the roles that may connect. A user with no matching
profile reaches nothing.

## Connect an MCP client

Open the Synapse app and click **Copy MCP link** at the bottom of the sidebar.
Add that link to your MCP client as a remote server. The client signs in with
OAuth, so OAuth Settings must allow dynamic client registration.

Every call runs as the signed-in user. Profiles decide which DocTypes and actions
are reachable, and Frappe permissions still apply. Every call is written to the
Synapse Log.

When a client connects, Synapse sends a few lines of instructions: describe a
DocType before using it, prefer filtered reads over SQL, confirm writes with the
user, and read `get_dashboard_guide` before working on dashboards.

## The Synapse app

The Synapse icon on the Apps screen opens the dashboard app at `/synapse`.

- The sidebar lists every dashboard and report you can read, by group, with search
  (press `/`).
- Each dashboard loads its data in one call and reloads when a filter changes.
- **Save filters** keeps your filter values. They open as your defaults next time.
  **Clear saved filters** goes back to the page defaults.
- The sidebar footer has an app switcher, your account menu and the MCP link.
- Light, dark and system themes follow your Desk theme.

The app draws everything with the Synapse UI kit in `synapse/public/synapse-ui`.
Its README documents every widget, chart data shape and option.

## Building a dashboard

The quickest way: connect an MCP client and ask, for example "build a sales
dashboard by customer for this year" or "study my sales data and suggest
dashboards". The assistant reads `get_dashboard_guide` and saves the page in one
call. No code is written.

A dashboard is a **Synapse Page** with a **Layout** and one **Data Source**:

| Data Source | Data | Filters | Use it for |
|---|---|---|---|
| Query (default) | Each widget names its data. Synapse runs it live with the viewer's permissions | Yes | Totals, counts, trends, rankings, top lists |
| Assistant | Stored JSON, written by the connected LLM and refreshed on a schedule | No | Summaries, risks, picks, commentary |
| Script | One Synapse Script returns all widget data | Yes | Logic a query cannot express |

The app tags each page **Live** (Query or Script) or **Assistant**. Assistant
pages cannot have filters, so build one page per period or company when needed.

**Layout** is JSON in the Synapse UI format: `filters` plus `sections` of
`widgets` (a dashboard), or `filters` plus `table` options (a report). On a Query
dashboard each widget carries a `query` and a `bind` that maps page filters to
its fields:

```json
{
  "filters": [{"key": "period", "label": "Period", "type": "daterange", "default": "this_year"}],
  "sections": [{"key": "kpi", "collapsible": false, "widgets": [
    {"key": "sales", "type": "stat", "col": 4, "label": "Sales", "format": "currency",
     "query": {"doctype": "Sales Invoice", "metrics": ["sum:base_grand_total"], "filters": {"docstatus": 1}},
     "bind": {"period": "posting_date"}},
    {"key": "top", "type": "bar", "col": 8, "title": "Top customers", "horizontal": true,
     "query": {"doctype": "Sales Invoice", "metrics": ["sum:base_grand_total"], "group_by": ["customer"],
               "filters": {"docstatus": 1}, "limit": 8},
     "bind": {"period": "posting_date"}}
  ]}]
}
```

A query takes `metrics` (`count`, `sum:<field>`, `avg:`, `min:`, `max:`), up to 3
`group_by` fields, an optional `period` (`{"field": "posting_date", "by": "month"}`,
by day, week, month, quarter or year), fixed `filters`, `order_by` and `limit`.
It reads through Frappe's permission-checked `get_list`, so no SQL is involved.

Sections can hold child `sections`, up to 4 levels. Tables and lists take
`groupBy` as one key or a list of keys, for groups inside groups.

**Script** dashboards pick one Synapse Script. It receives `args["filters"]` and
assigns `result = {widget_key: value}`. Scripts can call
`frappe.aggregate(doctype, metrics=..., group_by=..., period=..., filters=...)`,
`frappe.get_list`, `frappe.get_count`, and `query(sql, values)` when SQL access is
on. Frappe's safe exec applies: no imports, writes or network, and no names or dict
keys that start with `_`.

Every script run has a budget: 200 data calls, 20,000 rows read and 30 seconds.
A run that goes over is stopped with a plain message, and the same page with the
same filters will not run again for five minutes, so reloading a broken page
cannot overload the server. At most two Script dashboards load at once on a site.
Group and sum in SQL rather than paging through raw rows. Change the limits in
site config with `synapse_script_max_queries`, `synapse_script_max_rows`,
`synapse_script_max_seconds` and `synapse_script_max_parallel`.

**Assistant** dashboards store the data dict on the page through
`publish_dashboard_snapshot`. Fill in **Brief for the Assistant** and **Refresh
Every**. The assistant's notes show above the widgets.

Data never changes how a widget draws itself. Template, style and script keys in
data are removed, and links must be site paths or http(s).

## MCP tools for dashboards

| Tool | What it does |
|---|---|
| `get_dashboard_guide` | Rules, which data source to pick, steps for "build" and "study my data", formats, an example, and what this user can do now |
| `aggregate` | Count, sum, average, min or max over any DocType, grouped or by period. No SQL |
| `list_dashboards` | Dashboards you can read, their data source, and which Assistant ones are due |
| `get_dashboard` | One dashboard's layout, source, brief and current snapshot |
| `preview_dashboard_data` | Runs a load as the browser does and lists widgets that got no data |
| `save_dashboard` | Creates or changes a dashboard in one call. Loads the data first and refuses to save if a widget fails |
| `publish_dashboard_snapshot` | Stores new data and notes on an Assistant dashboard |

The two write tools need the **Dashboard tools** switch in Synapse Settings and a
profile with write on Synapse Page. They write only Synapse Pages, so the general
write tools can stay off. Query dashboards need nothing else. Data Scripts are
still created by a System Manager.

## Sharing

Pages are private by default. Use **Share** on a Synapse Page to give a Desk user
read access. For Script dashboards, also share the Synapse Script and grant the
reader's profile reads on Synapse Script and the source DocTypes. Assistant
snapshots are visible to anyone who can read the page, without rechecking the
records they came from.

## Legacy block pages

Pages with **Legacy Blocks** and no Layout still open in the desk viewer at
`/app/synapse-view/<page>`. They use the older component library in
`synapse/public/js/library` and the MCP tools `get_dashboard_contract` and
`validate_dashboard_component`. New dashboards should use the Synapse app.

## Tests

```sh
python -m unittest discover -s synapse -p 'test_mcp_*.py' -t .
```

These need no site. Site tests run with `bench run-tests --app synapse`.
