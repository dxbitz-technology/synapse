# Copyright (c) 2026, Dxbitz and contributors
"""Plain words for Frappe safe exec errors. No Frappe import, so pure tests can load it."""


def sandbox_hint(error) -> str | None:
	"""Plain words for the safe exec errors that trip up most scripts."""
	text = str(error)
	if "starts with _" in text:
		return (
			"Frappe's safe exec blocks names and dict keys that start with _, for example "
			'row["_total"]. Rename them without the underscore, for example row["total_hidden"].'
		)
	return None
