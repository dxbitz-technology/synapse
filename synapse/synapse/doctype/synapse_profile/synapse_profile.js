// Copyright (c) 2026, Dxbitz and contributors

frappe.ui.form.on("Synapse Profile", {
	refresh(frm) {
		frm.set_intro(
			__(
				"Deprecated. Profiles only apply to the old Synapse MCP endpoint. Frappe now has its own MCP server, where plain Frappe permissions decide what an assistant can reach. Connect new clients there."
			),
			"orange"
		);
	},
});
