# Copyright (c) 2026, Dxbitz and contributors
"""Totals, counts and averages over any reachable DocType, without SQL."""

from synapse.mcp import mcp
from synapse.mcp_core import ToolAnnotations
from synapse.mcp_tools import audit, settings
from synapse.mcp_tools.policy import READ, check


@mcp.tool(
	annotations=ToolAnnotations(title="Totals and counts", readOnlyHint=True),
	enabled=settings.read_tools_enabled,
)
@audit.audited(audit.READ)
def aggregate(
	doctype: str,
	metrics: list | None = None,
	group_by: list | None = None,
	period: dict | None = None,
	filters: dict | None = None,
	order_by: str | None = None,
	limit: int | None = None,
):
	"""Count, sum, average, min or max over a DocType, grouped if you like. Use this to study data.

	It reads through Frappe permissions, needs no SQL and works on any number of
	records. The same spec, as a widget's query, makes a live Query dashboard.

	Args:
	        doctype: The DocType, for example "Sales Invoice".
	        metrics: List of "count", "sum:<field>", "avg:<field>", "min:<field>", "max:<field>". Default ["count"].
	        group_by: Up to 3 field names, for example ["customer"].
	        period: Time buckets, {"field": "posting_date", "by": "day|week|month|quarter|year"}.
	        filters: Field/value pairs, same form as get_list, for example {"docstatus": 1}.
	        order_by: A result column and direction, for example "sum_base_grand_total desc". Default: biggest first, or by period.
	        limit: Rows to return, 1 to 500. Default 50."""

	from synapse import aggregate as engine

	resolved = check(settings.get_policy(), READ, doctype)
	audit.current().target(resolved)
	spec = {
		"doctype": resolved,
		"metrics": metrics,
		"group_by": group_by,
		"period": period,
		"filters": filters,
		"order_by": order_by,
		"limit": limit,
	}
	try:
		result = engine.run(engine.compile_spec(spec))
	except engine.SpecError as error:
		import frappe

		frappe.throw(str(error))
	audit.current().rows(result["row_count"])
	return result
