# Copyright (c) 2026, Dxbitz and contributors
"""What Synapse tells an MCP client at initialize. No Frappe import, so pure tests can read it."""

INSTRUCTIONS = """Synapse gives you access to this Frappe / ERPNext site as the signed-in user. Synapse Profiles decide which DocTypes and actions you may use, and Frappe permissions still apply.

- Call describe_doctype before reading or writing a DocType. Never guess field names.
- Prefer get_list and get_count with filters. Use run_sql_query only when they cannot answer, it is read only.
- Writes change real records. Confirm with the user before create, update, submit, cancel or delete. Use the child row tools for child tables.
- Dashboards: call get_dashboard_guide before building, changing or refreshing one. Users open them at /synapse#/<page>.
- A refused call says which rule stopped it. Tell the user, do not work around it."""
