// Copyright (c) 2026, Dxbitz and contributors

frappe.ui.form.on("Synapse Script", {
	refresh(frm) {
		frm.add_custom_button(__("Component Templates"), async () => {
			const catalog = (await synapse.dashboard.catalog()).filter((item) => item.script_template);
			const dialog = new frappe.ui.Dialog({
				title: __("Script Template"),
				fields: [
					{
						fieldname: "component",
						fieldtype: "Select",
						label: __("Component"),
						options: catalog.map((item) => ({
							label: item.label,
							value: item.key,
						})),
						reqd: 1,
					},
					{
						fieldname: "note",
						fieldtype: "HTML",
						options: `<p>${__(
							"This replaces the editor with example data. Replace the example with permitted reads before using it as current data. Scripts must assign an object to result."
						)}</p>`,
					},
				],
				primary_action_label: __("Use Template"),
				primary_action: (values) => {
					frm.set_value(
						"script",
						catalog.find((item) => item.key === values.component).script_template
					);
					dialog.hide();
				},
			});
			dialog.show();
		});
		if (!frm.is_new())
			frm.add_custom_button(__("Test Component Output"), () => {
				if (frm.is_dirty()) return frappe.msgprint(__("Save the script before testing it."));
				synapse.dashboard.component_dialog(
					null,
					{
						component_type: "number_card",
						columns: 12,
						config: "{}",
						data_script: frm.doc.name,
						script_parameters: "{}",
					},
					{ preview_only: true }
				);
			});
		frm.set_intro(
			__(
				"Use args for parameters and assign the component data object to result. Document reads retain Synapse grants and Frappe permissions. SQL also requires System Manager and SQL access. Share the saved script with its dashboard readers. The bench server_script_enabled switch must be enabled by the operator."
			)
		);
	},
});
