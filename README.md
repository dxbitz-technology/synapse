# Synapse

An MCP server for Frappe 16 and ERPNext, with access profiles and an audit log.

- [Documentation](https://github.com/dxbitz-technology/synapse/wiki/Documentation)
- [Endpoints](https://github.com/dxbitz-technology/synapse/wiki/Endpoints)
- [Privacy policy](https://github.com/dxbitz-technology/synapse/wiki/Privacy-Policy)
- [Terms of Service](https://github.com/dxbitz-technology/synapse/wiki/Terms-of-Service)
- [Issues](https://github.com/dxbitz-technology/synapse/issues)

For security reports, email info@dxbitz.com.

Licensed under AGPL-3.0-or-later. The adapted MCP core includes its original
[MIT notice](synapse/mcp_core/LICENSE).

## Live dashboard data

Create a **Synapse Script** in Desk. Read parameters from `args` and assign the
component's data object to `result`. For example, a Number Card script:

```python
result = {"value": frappe.get_count("Task", filters={"status": "Open"})}
```

`frappe.get_list(doctype, filters=..., fields=..., limit=...)` and
`frappe.get_count(doctype, filters=...)` enforce Synapse profile grants and Frappe
permissions. Scripts have no document write, unrestricted `get_all`, import,
network, or other-script execution API.

For aggregate queries, System Managers with Synapse SQL access can use bound
parameters:

```python
rows = query(
    "SELECT COUNT(name) AS total FROM `tabTask` WHERE status = %(status)s",
    {"status": args.get("status", "Open")},
)
result = {"value": rows[0]["total"]}
```

`frappe.db.sql(query, values)` is an alias for `query(query, values)`. Only SELECT
queries accepted by Synapse's existing SQL guard run. Queries have a 15-second
statement timeout and the Synapse row cap. SQL does not apply record-level Frappe
permissions, so it additionally requires System Manager and the existing SQL
profile/configuration gates.

On a **Synapse Page** block, select **Data Script** and optionally set **Script
Parameters (JSON)**, for example `{"status": "Open"}`. The script runs on opening
and when **Refresh** is clicked. Its result must match the component's Data
Template. Blocks without a script keep using Frozen Data. A failed script shows
an error on that block without presenting old data as current.

Call the same function directly with the authenticated API method
`synapse.scripts.run_script`, passing `name` and optional `args`, or through the
MCP tool `execute_synapse_script`. Callers need read access to the script and a
Synapse profile allowing reads of Synapse Script and any queried DocTypes. Calls
are audited. Only System Managers can maintain script definitions; remote writes
also require Synapse's existing configuration-write setting.

After updating the app, migrate the target site and build Synapse's assets.
Frappe's bench-level `server_script_enabled` setting must be enabled by the
operator. Synapse respects this switch and does not enable it automatically.

## Chart library review

The library includes 11 charts, seven widgets and three layout components.
Scatter and grouped horizontal bars use local renderers. The point map bundles
[Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/) land outlines
in the public domain; no map service or API key is required. Map data is
`{"points": [{"label": "Dubai", "latitude": 25.2, "longitude": 55.27, "value": 12}]}`.
Scatter uses numeric `labels` for x coordinates and matching series values for y.

The visual gallery is at `synapse/tests/visual/index.html`. Serve the bench root
on localhost and open `/apps/synapse/synapse/tests/visual/index.html`. It includes
every renderer, edge cases, and Sales, Buying, Stock and Projects examples.
Sample data is labelled. A theme switch and narrow viewports exercise dark mode
and responsive layouts. `scripts/validate_visual_samples.py` checks every sample
against the same component schemas used for saved dashboards.

To generate local aggregate snapshots, run from the bench's `sites` directory:

```sh
../env/bin/python ../apps/synapse/scripts/review_dashboards.py --site int.local \
  --output ../apps/synapse/synapse/tests/visual/local-dashboards.json
```

Use the intended local site name. The exporter exercises restricted script
execution with test-only script documents and scripting/SQL gate overrides.
It does not enable server scripts, alter site records, or prove deployed access
configuration. Its output is ignored by Git. In the module previews, choose
**Use local snapshot** to view those aggregates instead of sample data.

## Dashboard access and editing

Open **Synapse** from the Apps screen to find dashboards you can read. System
Managers also have shortcuts to Pages, Data Scripts, Components, Profiles,
Settings and the Audit Log. Search filters the available dashboard cards.

Pages stay private by default. System Managers can use the standard **Share**
control on a Synapse Page to give a Desk user read access. Sharing a page does
not grant source-document access. For scripted blocks, also share the Synapse
Script and grant Synapse reads of **Synapse Script** and its source DocTypes
through the reader's profile. Normal Frappe permissions still apply. SQL remains
restricted to System Managers with SQL access. Frozen snapshots are visible to
page readers without rechecking access to their original source records.

On a Synapse Page, use **Add Component** or a block's **Configure / Preview**
button. Choose the component, width and data source. The dialog includes valid
example data and the accepted options/data schemas. **Use Example Data** resets
the block to a sample snapshot. **Preview Component** checks and renders the
current inputs; scripted previews use the saved script and current user's
access. **Apply** validates configuration without executing live scripts. Saving
the page validates every block again. **Open Dashboard** opens the saved result.

On a Synapse Script, **Component Templates** supplies restricted Python examples
for each data component. These templates contain example values, not business
queries. Inspect actual DocType fields and replace the values with permitted
reads. **Test Component Output** lets you select the target component, parameters
and options, then run and preview the saved script. Unsaved scripts must be
saved before testing.

For MCP clients generating dashboards, call **get_dashboard_contract** before
writing a page or script. It returns the same schemas, examples, script templates
and runtime rules used by the editor. Call **validate_dashboard_component** with
a data object or saved script before saving a page. Existing create/update tools
retain their normal write and configuration-write gates. Script output, preview,
snapshot validation and saved-page rendering use the same component contract.
Series lengths, part-chart values and pivot dimensions must match their labels.

Dashboard layouts load before scripted data. Up to three scripted blocks load
at a time. Failed blocks show an error independently and never fall back to an
old snapshot. Refresh fetches current data again; navigating away discards late
responses. The footer identifies dashboards containing saved snapshots.
Tables support search, numeric/text sorting and pagination (20 rows by default).
Options are `page_size` (1–100), `searchable` and `sortable`. For record links,
use a column with `type: "link"` and `doctype: "Sales Invoice"`; document access
is still checked when the record is opened.

After updating an existing site, run its normal migration and build the Synapse
assets. Sites with custom DocPerm overrides may need their administrator to
review those overrides; migration does not replace custom permission policy.
