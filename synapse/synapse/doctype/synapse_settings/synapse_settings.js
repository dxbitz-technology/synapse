// Copyright (c) 2026, Dxbitz and contributors

frappe.ui.form.on("Synapse Settings", {
	refresh(frm) {
		// Only Frappe 16.53 and later has its own MCP server. On older Frappe this is still the way in.
		const [major, minor] = String((frappe.boot.versions || {}).frappe || "0").split(".").map(Number);
		if (major < 16 || (major === 16 && minor < 53)) return;
		frm.set_intro(
			__(
				"The Synapse MCP endpoint is deprecated. These switches, the backstop and Synapse Profiles only apply to clients still connected to it. New clients use Frappe's own MCP server (Enable MCP in System Settings)."
			),
			"orange"
		);
	},
});
