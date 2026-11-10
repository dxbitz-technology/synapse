# Copyright (c) 2026, Dxbitz and contributors
"""What Synapse tells an MCP client at initialize. No Frappe import, so pure tests can read it."""

INSTRUCTIONS = """Synapse gives you access to this Frappe / ERPNext site as the signed-in user. Synapse Profiles decide which DocTypes and actions you may use, and Frappe permissions still apply.

- Call describe_doctype before reading or writing a DocType. Never guess field names.
- For totals, counts and trends use aggregate. Use get_list and get_count for records. Use run_sql_query only when none of them can answer, it is read only.
- Writes change real records. Confirm with the user before create, update, submit, cancel or delete. Use the child row tools for child tables.
- Dashboards: call get_dashboard_guide first, then build with save_dashboard and data_source Query. No code is needed. Never write Python files or ask the user to install anything. Users open dashboards at /synapse#/<page>.
- After writing or changing a Synapse Script, run it with execute_synapse_script, read cost, and fix the script until it loads with no advice.
- A refused call says which rule stopped it. Tell the user, do not work around it."""
