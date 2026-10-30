// Copyright (c) 2026, Dxbitz and contributors

frappe.ui.form.on("Synapse Page", {
	refresh(frm) {
		frm.set_query("component_type", "blocks", () => ({
			filters: { not_implemented: 0 },
		}));
		if (frm.perm?.[0]?.write) {
			frm.add_custom_button(__("Add Component"), () => synapse.dashboard.component_dialog(frm));
		}
		if (!frm.is_new()) {
			frm.add_custom_button(__("Open Dashboard"), () => {
				if (frm.is_dirty())
					return frappe.msgprint(__("Save your changes before opening the dashboard."));
				frappe.set_route("synapse-view", frm.doc.name);
			});
		}
		frm.set_intro(
			__(
				"Use Add Component for examples, options and preview. Share this page with dashboard readers. For current data, also share each data script and grant Synapse reads of the script and source DocTypes. Saved snapshots are visible to everyone who can read this page."
			)
		);
	},
});

frappe.ui.form.on("Synapse Page Block", {
	configure(frm, cdt, cdn) {
		synapse.dashboard.component_dialog(frm, locals[cdt][cdn]);
	},
});
