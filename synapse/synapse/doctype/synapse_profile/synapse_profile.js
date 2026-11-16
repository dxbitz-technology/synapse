// Copyright (c) 2026, Dxbitz and contributors

frappe.ui.form.on("Synapse Profile", {
	refresh(frm) {
		// Only Frappe 16.53 and later has its own MCP server. On older Frappe this is still the way in.
		const [major, minor] = String((frappe.boot.versions || {}).frappe || "0").split(".").map(Number);
		if (major < 16 || (major === 16 && minor < 53)) return;
		frm.set_intro(
			__(
				"Deprecated. Profiles only apply to the old Synapse MCP endpoint. Frappe now has its own MCP server, where plain Frappe permissions decide what an assistant can reach. Connect new clients there."
			),
			"orange"
		);
	},
});
