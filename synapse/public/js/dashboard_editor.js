// Copyright (c) 2026, Dxbitz and contributors

frappe.provide("synapse.dashboard");
synapse.dashboard.catalog = async () => {
	if (!synapse.dashboard._catalog) {
		const response = await frappe.call("synapse.api.get_component_catalog");
		synapse.dashboard._catalog = response.message || [];
	}
	return synapse.dashboard._catalog;
};

synapse.dashboard.component_dialog = async (frm, row, options = {}) => {
	const catalog = await synapse.dashboard.catalog();
	let preview_id = 0;
	let initializing = true;
	const dialog = new frappe.ui.Dialog({
		title: row ? __("Configure Component") : __("Add Component"),
		size: "extra-large",
		fields: [
			{
				fieldname: "component_type",
				fieldtype: "Select",
				label: __("Component"),
				options: catalog.map((item) => ({
					label: item.label,
					value: item.key,
				})),
				reqd: 1,
				onchange: () => update_help(!initializing),
			},
			{ fieldname: "help", fieldtype: "HTML" },
			{
				fieldname: "columns",
				fieldtype: "Int",
				label: __("Width (1 to 12 columns)"),
				default: 6,
				reqd: 1,
			},
			{
				fieldname: "config",
				onchange: () => {
					preview_id++;
				},
				fieldtype: "Code",
				options: "JSON",
				label: __("Options (JSON)"),
				default: "{}",
			},
			{
				fieldname: "source",
				fieldtype: "Select",
				label: __("Data Source"),
				options: ["Saved Snapshot", "Data Script"],
				default: "Saved Snapshot",
				onchange: () => {
					preview_id++;
				},
			},
			{
				fieldname: "frozen_data",
				onchange: () => {
					preview_id++;
				},
				fieldtype: "Code",
				options: "JSON",
				label: __("Snapshot Data (JSON)"),
				depends_on: 'eval:doc.source==="Saved Snapshot"',
			},
			{
				fieldname: "data_script",
				onchange: () => {
					preview_id++;
				},
				fieldtype: "Link",
				options: "Synapse Script",
				label: __("Data Script"),
				depends_on: 'eval:doc.source==="Data Script"',
				get_query: () => ({ filters: { enabled: 1 } }),
			},
			{
				fieldname: "script_parameters",
				onchange: () => {
					preview_id++;
				},
				fieldtype: "Code",
				options: "JSON",
				label: __("Script Parameters (JSON)"),
				default: "{}",
				depends_on: 'eval:doc.source==="Data Script"',
			},
			{
				fieldname: "use_example",
				fieldtype: "Button",
				label: __("Use Example Data"),
				click: () => use_example(),
			},
			{
				fieldname: "new_script",
				fieldtype: "Button",
				label: __("New Script from Template"),
				click: () => {
					const item = selected();
					if (item?.script_template) {
						dialog.hide();
						frappe.new_doc("Synapse Script", {
							script: item.script_template,
							description: item.description,
						});
					}
				},
			},
			{
				fieldname: "preview",
				fieldtype: "Button",
				label: __("Preview Component"),
				click: () => preview(),
			},
			{ fieldname: "output", fieldtype: "HTML" },
		],
		primary_action_label: options.preview_only ? __("Close") : row ? __("Apply") : __("Add"),
		primary_action: async () => {
			if (options.preview_only) return dialog.hide();
			const values = dialog.get_values();
			if (!values) return;
			const payload = payload_for(values);
			if (!payload) return;
			await frappe.call("synapse.api.preview_component", {
				...payload,
				validate_only: 1,
			});
			const target = row || frm.add_child("blocks");
			Object.assign(target, {
				component_type: values.component_type,
				columns: values.columns,
				config: values.config || "{}",
				frozen_data: values.frozen_data || "{}",
				data_script: values.source === "Data Script" ? values.data_script : "",
				script_parameters: values.script_parameters || "{}",
			});
			frm.dirty();
			frm.refresh_field("blocks");
			dialog.hide();
		},
	});
	const selected = () => catalog.find((item) => item.key === dialog.get_value("component_type"));
	function update_help(reset = false) {
		preview_id++;
		const item = selected();
		if (!item) return;
		if (reset) use_example();
		const help = dialog.fields_dict.help.$wrapper.empty();
		const description = document.createElement("p");
		description.textContent = item.description;
		const details = document.createElement("details");
		details.className = "synapse-component-help";
		const summary = document.createElement("summary");
		summary.textContent = __("Accepted options and data structure");
		const code = document.createElement("pre");
		code.textContent = JSON.stringify(
			{ options: item.options_schema, data: item.data_template },
			null,
			2
		);
		details.append(summary, code);
		help.append(description, details);
		if (!dialog.get_value("frozen_data"))
			dialog.set_value("frozen_data", JSON.stringify(item.example_data, null, 2));
		if (item.is_layout) dialog.set_value("source", "Saved Snapshot");
		dialog.set_df_property("source", "hidden", Boolean(item.is_layout));
		dialog.set_df_property("new_script", "hidden", Boolean(item.is_layout));
	}
	function use_example() {
		const item = selected();
		if (!item) return;
		dialog.set_value("config", JSON.stringify(item.example_config, null, 2));
		dialog.set_value("frozen_data", JSON.stringify(item.example_data, null, 2));
		dialog.set_value("source", "Saved Snapshot");
	}
	function payload_for(values) {
		if (values.source === "Data Script" && !values.data_script) {
			frappe.msgprint(__("Select a saved data script first."));
			return null;
		}
		return {
			component_type: values.component_type,
			config: values.config || "{}",
			frozen_data: values.frozen_data || "{}",
			data_script: values.source === "Data Script" ? values.data_script : null,
			script_parameters: values.script_parameters || "{}",
		};
	}
	async function preview() {
		const values = dialog.get_values();
		if (!values) return;
		const payload = payload_for(values);
		if (!payload) return;
		const request = ++preview_id;
		const host = dialog.fields_dict.output.$wrapper[0];
		synapse.library.clear(host);
		host.className = "synapse-component-preview";
		host.textContent = __("Loading preview...");
		try {
			const response = await frappe.call("synapse.api.preview_component", payload);
			if (request !== preview_id) return;
			const model = response.message;
			synapse.library.render(host, model.component_type, model.config, model.data);
		} catch (_) {
			if (request === preview_id)
				host.textContent = __("Preview failed. Check the configuration, data and script access.");
		}
	}
	dialog.onhide = () => {
		preview_id++;
		synapse.library.clear(dialog.fields_dict.output.$wrapper[0]);
	};
	dialog.show();
	await dialog.set_values(
		row
			? { ...row, source: row.data_script ? "Data Script" : "Saved Snapshot" }
			: { component_type: catalog[0].key }
	);
	initializing = false;
	update_help();
};
