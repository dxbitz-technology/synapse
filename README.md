# Synapse

An MCP server for Frappe 16 and ERPNext. Connect a compatible client to read and
update records as a Frappe user, with a separate access profile and an audit log.

## Install

```sh
bench get-app --branch version-16 https://github.com/dxbitz-technology/synapse
bench --site <site> install-app synapse
```

Requires Frappe 16. The optional SQL tool supports MariaDB only. ERPNext is not
required. The component catalog is created during installation and refreshed
on migration.

## Connect

1. In OAuth Settings, enable server metadata, protected-resource metadata and
   dynamic client registration if your client uses automatic OAuth setup.
2. Create a Synapse Profile. Add the user's roles and the DocTypes and actions
   they may use.
3. In Synapse Settings, enable the endpoint and read tools. Enable writes only
   when needed.
4. Connect your MCP client to:

```text
https://<site>/api/method/synapse.mcp.handle_mcp
```

OAuth uses Frappe's login. API keys and authenticated sessions are also supported.
OAuth tokens authorize the user's wider Frappe API access, not just Synapse.
Use a dedicated user with suitable permissions.

Check setup from the Synapse console or run:

```sh
bench --site <site> execute synapse.mcp_tools.check.report
```

## Access

Enabled profiles are combined across the user's roles. A profile never replaces
Frappe permissions. No matching profile means no document access.

- Read, write, submit, cancel, delete and operate are separate grants.
- Full Access grants document actions within the user's Frappe permissions.
  SQL and custom tools still need their own explicit grants.
- Credentials and Synapse's access settings are blocked.
- Schema, code and permission records are read only by default. System Manager
  config writes can be enabled separately for create/update only.
- The site can block additional DocTypes in Synapse Settings.

Document tools cover discovery, reads, counts, creation, updates, submission,
cancellation, deletion and child-row editing. Child-row tools use row names and
support expected-value checks. Batch row edits are saved together. Use whole-table
updates only when deliberately replacing a table.

`run_operation` calls a controller's public business method. It requires the
operate grant and document write permission. Framework methods, lifecycle hooks,
credential access, queued actions and direct database mutators are excluded.
Custom controller code remains responsible for its own effects and permissions.

## Custom tools

An installed app can declare a function through its hooks:

```python
synapse_tools = [
    {"method": "myapp.tools.open_tasks", "read_only": True},
]
```

The function's signature and docstring describe the tool. Alternatively, decorate
functions with `@synapse.tool(read_only=True)` and list the module in the hook.
Tool names must be unique and cannot replace built-ins.

Each tool needs Enable Custom Tools and an exact-name grant in a profile.
Read-only tools also need Enable Read Tools; other tools need Enable Write Tools.
Registrations are resolved for the current site and request. Tool authors must
use permission-aware APIs and must not commit transactions themselves, otherwise
Synapse cannot guarantee rollback with the audit record.

## SQL

SQL is off by default. It requires the site switch, a profile with Allow SQL,
and a separately configured read-only MariaDB account. It bypasses Frappe record
permissions, so grant it only to trusted database users.

Set `mcp_ro_db_user` and `mcp_ro_db_password` in the site's configuration. The
account should have SELECT access only to that site's database. Queries have a
timeout and an enforced result limit. Joined output columns need unique names.

Without that account the tool stays disabled. The explicit
`mcp_sql_allow_guard_only` option permits the weaker fallback on the site's
connection, protected by query checks and rollback. Optional
`mcp_sql_blocked_tables` entries extend the fixed credential-table exclusions.

## Audit and pages

Synapse Log records tool calls, refusals and errors. Successful database changes
and their audit record commit together. If the audit record cannot be saved,
the call fails and its transaction is rolled back. External effects or commits
inside third-party code cannot be undone by Synapse.

Password fields are masked. Disable Log Field Values to omit submitted values,
changes and SQL text. The retention period defaults to 90 days.
See [PRIVACY.md](PRIVACY.md).

Synapse Pages display saved charts, tables, metrics and formatted text on a
responsive grid. Data is stored with each block; there are no live data sources.
Open a page at `/app/synapse-view/<name>`. Page access is restricted to System
Manager by default. Disabled pages cannot be viewed. Maps, scatter charts and
horizontal bar charts are not available. Markdown supports formatting and safe
links; embedded HTML controls and images are removed.

The Model Provider field is a label only. It does not configure a provider.

## Tests and support

```sh
python -m unittest discover -s apps/synapse/synapse -p 'test_mcp_*.py' -t apps/synapse
bench --site <test-site> run-tests --app synapse
```

Run database tests on a disposable site. They create fixtures and exercise real
commits and rollbacks.

Report issues at [GitHub Issues](https://github.com/dxbitz-technology/synapse/issues).
For security reports, email info@dxbitz.com rather than posting details publicly.

Licensed under AGPL-3.0-or-later. The adapted MCP core includes its original
[MIT notice](synapse/mcp_core/LICENSE).
