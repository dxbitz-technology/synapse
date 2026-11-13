// Copyright (c) 2026, Dxbitz and contributors

frappe.ui.form.on("Synapse Settings", {
	refresh(frm) {
		frm.set_intro(
			__(
				"The Synapse MCP endpoint is deprecated. These switches, the backstop and Synapse Profiles only apply to clients still connected to it. New clients use Frappe's own MCP server (Enable MCP in System Settings)."
			),
			"orange"
		);
	},
});
