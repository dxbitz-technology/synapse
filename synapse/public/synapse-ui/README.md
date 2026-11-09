# synapse-ui

A small, zero-dependency UI kit for dashboards in a Frappe / ERPNext custom frontend.
Two files, no build step:

| File | Lines | Gzipped |
|---|---|---|
| `synapse-ui.js` | ~990 | ~19 KB |
| `synapse-ui.css` | ~300 | ~5 KB |

It looks like Frappe desk (Inter, 13px, gray controls, soft cards, Frappe status pills) and reads
Frappe's own CSS variables when they exist, so light and dark mode follow the desk theme.

`demo.html` is a mock explorer with 2 dashboards and 3 reports (loads the two files next to it).
`demo-standalone.html` is the same page with everything inlined, so it opens on its own.

---

## 1. Install

Copy the two files into your app, for example `bitz_app/public/bitz-ui/`, then load them:

```html
<link rel="stylesheet" href="/assets/synapse/synapse-ui/synapse-ui.css">
<script src="/assets/synapse/synapse-ui/synapse-ui.js"></script>
```

Everything is on `window.SynapseUI`. Global settings:

```js
SynapseUI.currency = 'AED';   // default for format 'currency'
SynapseUI.locale = 'en-US';   // number formatting locale
```

---

## 1a. Explorer (sidebar with all dashboards and reports)

```js
SynapseUI.app('#app', {
  title: 'Dxbitz Insights',
  home: 'sales-overview',                       // opened when the URL has no #/id
  items: [salesOverview, receivables, salesRegister],   // or: async () => [...] from the server
  themeToggle: true,
  onOpen: (item, view) => {}
});
```

Each item is a full dashboard or report config plus:

| key | |
|---|---|
| `id` | used in the URL: `/dashboards#/sales-register` (made from title if missing) |
| `title`, `group`, `description`, `keywords` | shown in and searched by the sidebar. Items are grouped under `group` |
| `type` | `'dashboard'` (default) or `'report'` |
| `load: async item => config` | optional, fetch the config only when the item is opened |
| `render: (el, item) => view` | optional, fully custom page |

- Search sits on top of the sidebar. `/` or `Ctrl/Cmd + K` focuses it, `Enter` opens the first match, `Esc` clears.
- The sidebar can be hidden on desktop (remembered). On screens under 900px it becomes a drawer.
- Switching views clears the previous view's filters from the URL. Links to a view (`#/sales-register`) work, and its filters stay in the query string so a filtered view can be shared.

To list dashboards from the server, return metadata and keep the configs in JS:

```js
const CONFIGS = { 'sales-overview': salesOverview, 'sales-register': salesRegister };
SynapseUI.app('#app', { items: async () => (await SynapseUI.call('bitz_app.api.dashboards.list'))
  .map(m => Object.assign({}, CONFIGS[m.id], m)) });   // python returns [{id, title, group}] the user may see
```

---

## 1b. Theme

```js
SynapseUI.theme('dark');      // 'light' | 'dark' | 'auto' (follow the OS)
SynapseUI.theme();            // read current
SynapseUI.themeButton();      // icon-only switch: sun (light), moon (dark), half circle (auto)
addEventListener('bz:theme', e => console.log(e.detail));
```

The choice is stored per browser. Inside Frappe desk it also saves the user's desk theme
(`switch_theme`), so desk and dashboards stay in sync. Set `SynapseUI.frappeTheme = false` to stop that.
The explorer shows the toggle in the sidebar. A standalone dashboard shows it with `themeToggle: true`.

---

## 2. Dashboard (layout + filters + one server call)

```js
SynapseUI.dashboard('#dash', {
  id: 'sales-overview',                       // used to remember collapsed sections
  title: 'Sales Overview',
  subtitle: 'All amounts in AED',
  method: 'bitz_app.dashboards.sales_overview.get_data',   // ONE python method per dashboard
  filters: [ ... ],                           // see 2.2
  sections: [ ... ],                          // see 2.3
  actions: [{ label: 'Export', onClick: dash => {...} }],
  autoApply: true,                            // false = show an Apply button
  syncUrl: true,                              // filters are kept in the URL query string
  header: true                                // false = hide title row (e.g. inside a Frappe page)
});
```

### 2.1 How data flows

1. On load and on every filter change, the dashboard calls `method` with one argument: `filters`.
2. The method returns one dict. Each key matches a widget `key`.
3. Each widget gets its value and renders it.

Inside desk it uses `frappe.call`. Outside desk it POSTs to `/api/method/<method>` with the CSRF token.
To use your own transport, pass `fetch: async filters => ({...})` instead of `method` (the demo does this).

```python
# bitz_app/dashboards/sales_overview.py
import frappe

@frappe.whitelist()
def get_data(filters=None):
    f = frappe._dict(frappe.parse_json(filters or "{}"))
    from_date, to_date = f.period            # daterange arrives as ["2026-01-01", "2026-12-31"]

    return {
        # stat: a number, or a dict with value/delta/spark/hint
        "revenue": {"value": 6489662, "delta": 6.5, "spark": [410, 455, 430, 520]},

        # charts: rows straight from SQL work (first text column = label, numeric columns = series)
        "sales_trend": frappe.db.sql("""
            select date_format(posting_date, '%%b') as month, sum(base_net_total) as sales
            from `tabSales Invoice`
            where docstatus = 1 and company = %(company)s and posting_date between %(f)s and %(t)s
            group by month(posting_date) order by month(posting_date)
        """, {"company": f.company, "f": from_date, "t": to_date}, as_dict=True),

        # or the simplest form: {label: number}
        "by_territory": {"Dubai": 45.5, "Abu Dhabi": 24.9, "Sharjah": 16},

        # lists: a list of dicts
        "overdue": [{"title": "ACC-SINV-2026-00412", "subtitle": "Gulf Star Trading",
                     "value": 48250, "status": "Overdue", "name": "ACC-SINV-2026-00412"}],
    }
```

A value can also carry option overrides. If the value is a dict with a `data` key, the other keys are merged
into the widget options for this render:

```python
"margin_trend": {"data": rows, "series": ["Gross %", "Net %"], "title": "Margin (YTD)"}
```

A widget with no matching key falls back to its own `data` option (useful for static widgets).

### 2.2 Filters

| type | value sent to python | options |
|---|---|---|
| `select` | string | `options: ['A', 'B']` or `[{value, label}]`, `required`, `placeholder` |
| `segment` | string | same `options`, shown as a button group |
| `daterange` | `[from, to]` (YYYY-MM-DD) | `default: 'this_month'` or `['2026-01-01','2026-03-31']`, `presets: [...]` |
| `date` | string | |
| `link` | string | `doctype: 'Customer'` (uses `search_link`) or `search: async txt => [...]` |
| `check` | `0` / `1` | `checkLabel` |
| `text`, `number` | string | `placeholder` |

Every filter takes `key`, `label`, `default` (value or function).
Date presets: `today, last_7, last_30, this_month, last_month, this_quarter, last_quarter, this_year, last_year, custom`.

On mobile the filter bar folds behind a "Filters (n)" button, where n is the number of changed filters.

### 2.3 Sections and the 12 column grid

```js
sections: [
  { key: 'kpi', collapsible: false, widgets: [
      { key: 'revenue', type: 'stat', col: 3, label: 'Revenue', format: 'currency' }, ...
  ]},
  { key: 'sales', title: 'Sales', description: 'Invoiced sales', collapsed: false, widgets: [
      { key: 'sales_trend', type: 'line', col: 8, title: 'Monthly sales' },
      { key: 'by_territory', type: 'donut', col: 4, title: 'By territory' }
  ]}
]
```

### Nested sections

A section can hold `sections` of its own, next to or instead of `widgets`. Child sections are indented
under their parent with a guide line, collapse on their own and remember their state. Up to 4 levels.

```js
{ key: 'sales', title: 'Sales', widgets: [ ...headline widgets ], sections: [
    { key: 'customers', title: 'By customer', collapsed: true, widgets: [ ... ], sections: [
        { key: 'overdue', title: 'Overdue', collapsed: true, widgets: [ ... ] }
    ]}
]}
```

- `col` (1 to 12) is the desktop width.
- Below 1000px of dashboard width, `col <= 4` becomes 6 and everything else becomes 12. Override with `colMd`.
- Below 640px everything stacks vertically.
- Breakpoints use container queries, so they follow the dashboard's own width, not the window. It behaves the same inside a desk page with the sidebar open.
- Sections are collapsible by default. The open/closed state is remembered per browser.

Widget options shared by all types: `key, type, col, colMd, title, subtitle, actions: [{label, onClick(data, dash)}], card: false, class, minHeight, data`.

### 2.4 Dashboard API

```js
const dash = SynapseUI.dashboard(...);
dash.refresh();                       // reload from server
dash.getFilters();                    // current filters as sent to python
dash.setFilters({ company: 'X' });    // set and reload
dash.setData('sales_trend', rows);    // push data into one widget without a server call
```

---

## 3. Charts

```js
SynapseUI.chart('#el', { type: 'bar', data, format: 'currency', height: 240 });
// returns { update(data, moreOpts), destroy() }
```

| type | notes |
|---|---|
| `bar` | `horizontal`, `stacked`, `values` (labels at bar ends), `barWidth` |
| `line` | `smooth`, `area`, `stacked` (stacked areas), `zero: false` to not force 0 |
| `area` | shortcut for `line` + `area` |
| `dot` | `horizontal`. `stacked: true` = all series on one lane with a connector (dumbbell). Otherwise series sit side by side |
| `pie` / `donut` | `centerLabel`, `centerFormat`, `inner` (0 to 1). More than 8 slices fold into "Other" |
| `split` | horizontal 100% bars. One series = one bar with legend. Many series = one bar per label, `barHeight` |

Common options: `format`, `axisFormat`, `colors: ['#hex', ...]`, `legend: false`, `onClick({label, index, values})`, `empty`, `labelWidth`.

### Accepted data shapes (pick the simplest that fits)

```js
[12, 18, 9]                                         // + labels: ['Jan','Feb','Mar']
{ Paid: 120, Unpaid: 40 }                           // one series keyed by label
{ labels: ['Q1','Q2'], values: [10, 20] }
{ labels: ['Q1','Q2'], series: { Sales: [10, 20], Cost: [6, 9] } }
{ labels: [...], datasets: [{ name, values }] }     // frappe-charts shape
[{ month: 'Jan', sales: 10, cost: 6 }, ...]         // SQL rows (as_dict=True)
[['Dubai', 92, 88], ['Sharjah', 85, 80]]            // rows as lists, names via series: ['This year','Last year']
```

For SQL rows, the label column is the first text column (or `labelKey`), and series are all numeric columns
(or `valueKeys`). Column names become legend names (`net_total` shows as "Net Total"), or map them with
`seriesNames: { net_total: 'Net' }`.

### Formats

`'number'`, `'number:0'`, `'int'`, `'date'` (DD-MM-YYYY), `'datetime'`, `'text'`, `'check'`, `'currency'` (AED), `'currency:USD'`, `'compact'` (1.2K), `'ccompact'` (AED 1.2M),
`'percent'` (value already in %, e.g. 18.5), `'percent:0'`, or any function `v => string`.
`SynapseUI.fmt(value, format)` is exported for your own blocks.

---

## 4. Stat card

```js
SynapseUI.stat('#el', { label: 'Revenue', value: 6489662, format: 'currency',
  delta: 6.5, deltaFormat: 'percent', hint: 'vs last month', inverse: false, spark: [..] });
```
`inverse: true` means a rise is bad (costs, overdue). Arrows always show direction, not color alone.

---

## 5. Quick lists

```js
SynapseUI.list('#el', {
  size: 'sm',                  // 'sm' = one compact line, 'lg' = avatar, two lines, visible buttons
  items: [{ title, subtitle, value, format, meta, status, indicator, avatar, color, href }],
  format: 'currency', limit: 5, empty: 'All clear',
  more: { label: 'View all', href: '/app/sales-invoice?status=Overdue' },
  onClick: (item, e) => {},
  actions: [
    { label: 'Approve', primary: true, onClick: item => {} },     // 'lg': shown as a button
    { label: 'Reject', danger: true, onClick: item => {} },       // others go in the ... menu
    { label: 'Write off', show: item => item.value < 5000, onClick: item => {} }
  ]
});
```

`status` is a string ("Paid", "Overdue", "Draft" ...) and gets the matching Frappe color, or
`{ label, color }` with color `green | red | orange | yellow | blue | gray`.

Inside a dashboard use `type: 'list'` with the same options. Python returns the `items` array.

---

## 5a. Report view and tables

A report is a dashboard with filters and one full-width table. Python returns rows.

```js
{
  id: 'sales-register', title: 'Sales Register', type: 'report',
  method: 'bitz_app.reports.sales_register.get_data',   // or report: 'Accounts Receivable' (runs a Frappe query/script report)
  filters: [ ... ],                                      // same filters as dashboards
  mapFilters: f => ({ ...f, from_date: f.period[0], to_date: f.period[1] }),   // optional, reshape before sending
  columns: [ ... ],          // optional if python sends them
  groupBy: 'customer',       // collapsible sections, a key or a function(row)
  collapsed: false,          // start with all groups closed
  totals: true,              // true = sum numeric columns, false, or ['qty', 'value']
  sortBy: 'posting_date', sortDir: 'desc',
  pageSize: 200,             // "Show more" when not grouped
  search: true, export: true,
  onClick: (row, e) => {}
}
```

Python can return any of these:

```python
return rows                                        # list of dicts or list of lists
return {"columns": columns, "result": rows}        # same as a Frappe script report
return {"data": rows, "groupBy": "status"}          # rows + override any table option for this load
```

Columns accept the Frappe formats you already use:

```python
{"fieldname": "grand_total", "label": "Grand Total", "fieldtype": "Currency", "width": 120}
{"fieldname": "customer", "label": "Customer", "fieldtype": "Link", "options": "Customer"}   # links to /app/customer/<name>
"Item:Link/Item:180"                                                                       # old string style
{"fieldname": "status", "label": "Status", "type": "status"}                               # coloured pill
```

`fieldtype` maps to formats: Currency, Float, Int, Percent, Date and Datetime (shown DD-MM-YYYY), Check.

Table features: click a header to sort, row search, CSV export of the visible rows, sticky header, sticky first
column, sticky totals row, subtotals on every group row, "Expand all" and "Collapse all". While grouped, the
group column is hidden because the group row already shows it.

Use a table anywhere: `type: 'table'` as a dashboard widget, or `SynapseUI.table(el, { columns, rows, groupBy })`.

### Groups inside groups

`groupBy` also takes a list, outermost first: `groupBy: ['customer', 'status']`. Each level is indented, has
its own count and subtotals, and collapses on its own. All group columns are hidden while grouped.
`collapsed` takes `true`, `false`, or a level number: `collapsed: 1` keeps the first level open and closes
the deeper ones. "Expand all" and "Collapse all" reach every level.

### Grouped lists

Quick lists take the same option: `groupBy: 'customer'` or a list of keys (and `collapsed`). Each group header shows the
count and the sum of `value`, and collapses on click.

---

## 6. Custom blocks

For anything the kit does not cover. A block gets data from python like any widget.

```js
{ key: 'target', type: 'html', col: 12, title: 'Annual target',
  // either a template with {{field}} or {{field | format}}
  template: '<b class="big">{{achieved | currency}}</b> of {{target | currency}}',
  // or full control
  render: (el, data, opts) => { el.innerHTML = '...'; },
  css: ':scope { padding: 4px } .big { font-size: 28px }',
  isolate: 'scoped'
}
```

CSS isolation modes:

| `isolate` | effect |
|---|---|
| `'scoped'` (default) | every selector is prefixed with this block, `:scope` means the block itself. Kit styles and tokens still apply |
| `'shadow'` | block renders in a Shadow DOM. Nothing leaks in or out, except CSS variables (`--bz-*`), so it still matches the theme |
| `'global'` | the CSS is added to the page as is |
| `'none'` | same as global, kept for clarity |

Reusable block types:

```js
SynapseUI.register('kpi-banner', (el, data, opts) => { ... });
// then in a section: { key: 'banner', type: 'kpi-banner', col: 12 }
```

Global CSS for the whole dashboard: `SynapseUI.css(cssText, 'my-id')` (calling again with the same id replaces it).
Outside dashboards: `SynapseUI.block(el, { template, render, css, isolate }, data)`.

---

## 7. Theming

All tokens are CSS variables on `:root`. Inside desk they read Frappe's variables first
(`--text-color`, `--border-color`, `--control-bg`, `--fg-color` ...). Override any of them:

```css
:root {
  --bz-radius: 10px;
  --bz-gap: 12px;
  --bz-c1: #0289f7;            /* series colors --bz-c1 .. --bz-c8 */
  --bz-sticky-top: 48px;       /* keep sticky filters under the desk navbar */
}
```

Dark mode works with `[data-theme="dark"]` on `<html>` (what Frappe sets) and with the OS setting when no theme is set.
Series colors are a fixed, colour-blind checked order. Keep charts at 8 series or fewer; pie and split fold the rest into "Other".

---

## 8. Using it in a Frappe desk Page

```js
frappe.pages['sales-overview'].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({ parent: wrapper, title: 'Sales Overview', single_column: true });
  frappe.require(['/assets/synapse/synapse-ui/synapse-ui.css', '/assets/synapse/synapse-ui/synapse-ui.js'], () => {
    SynapseUI.dashboard(page.main[0], { header: false, method: 'bitz_app.dashboards.sales_overview.get_data', filters: [...], sections: [...] });
  });
};
```

## 9. Notes

- Browser support: any browser from 2023 on (container queries, ResizeObserver).
- Charts redraw on resize and on section expand. Hover shows a tooltip on every chart; legend items toggle series.
- Python errors show inside each card. The full error goes to the browser console.
- Requests that finish out of order are ignored, so fast filter changes never show stale data.
