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

Data Scripts run through Frappe's safe exec. Turn it on for the bench:

```sh
bench set-config -g server_script_enabled 1
```

This is a bench setting, so it enables Server Scripts on every site of the bench.
Synapse never turns it on by itself.

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

A dashboard is a **Synapse Page** with a **Layout** and one data source.

**Layout** is JSON in the Synapse UI format: `filters` plus `sections` of
`widgets` (a dashboard), or `filters` plus `table` options (a report). Every
widget has a `key`.

```json
{
  "filters": [{"key": "period", "label": "Period", "type": "daterange", "default": "this_year"}],
  "sections": [
    {"key": "kpi", "collapsible": false, "widgets": [
      {"key": "order_value", "type": "stat", "col": 4, "label": "Order value", "format": "currency"}
    ]},
    {"key": "customers", "title": "Customers", "widgets": [
      {"key": "by_customer", "type": "bar", "col": 12, "horizontal": true, "format": "ccompact"}
    ]}
  ]
}
```

Sections can hold child `sections`, up to 4 levels. Child sections are indented
and collapse on their own. Tables and lists take `groupBy` as one key or a list of
keys, for groups inside groups.

**Data Source: Script.** Pick one **Synapse Script**. It receives the resolved
filters in `args["filters"]` and returns one dict keyed by widget key:

```python
f = args["filters"]
rows = query(
    """select customer, sum(base_grand_total) as total from `tabSales Order`
    where docstatus = 1 and transaction_date between %(a)s and %(b)s
    group by customer order by total desc limit 10""",
    {"a": f["period"][0], "b": f["period"][1]},
)
total = 0
for r in rows:
    total += r["total"]
result = {"order_value": {"value": total}, "by_customer": rows}
```

A report returns rows, or `{"columns": [...], "result": rows}`.

Scripts can use `frappe.get_list` and `frappe.get_count`, which keep Synapse
grants and Frappe permissions, and `query(sql, values)` for bound read-only SQL
(System Manager with SQL access). Scripts cannot import, write, call the network
or run other scripts. Variables made in a script are not visible inside list or
dict comprehensions, so build lists with loops.

**Data Source: Assistant.** The data dict is stored on the page and written by a
connected LLM with `publish_dashboard_snapshot`. Fill in **Brief for the
Assistant** and **Refresh Every**. The assistant's notes show above the widgets.
Filters do nothing on Assistant dashboards, and html widgets are not allowed.

Data never changes how a widget draws itself. Template, style and script keys in
data are removed, and links must be site paths or http(s).

## MCP tools for dashboards

| Tool | What it does |
|---|---|
| `get_dashboard_guide` | The full contract: layout, widgets, data shapes, filters, scripts, Assistant rules, an example |
| `list_dashboards` | Dashboards you can read, their data source, and which Assistant ones are due |
| `get_dashboard` | One dashboard's layout, source, brief and current snapshot |
| `preview_dashboard_data` | Runs a load as the browser does and lists widgets that got no data |
| `save_dashboard` | Creates or changes a dashboard. Arguments left out keep their values |
| `publish_dashboard_snapshot` | Stores new data and notes on an Assistant dashboard |

The two write tools need the **Dashboard tools** switch in Synapse Settings and a
profile with write on Synapse Page. They write only Synapse Pages, so the general
write tools can stay off. Data Scripts are still created by a System Manager.

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
