// Copyright (c) 2026, Dxbitz and contributors

frappe.ui.form.on("User", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.name !== frappe.session.user) {
			return;
		}

		frappe.call("synapse.api.connect_context").then((r) => {
			const ctx = (r && r.message) || {};
			if (!ctx.covered) {
				return;
			}

			frm.add_custom_button(__("Connect to Synapse"), () => show_synapse_connect(ctx.endpoint));
		});
	},
});

function show_synapse_connect(endpoint) {
	const url = endpoint || "";
	const d = new frappe.ui.Dialog({ title: __("Connect to Synapse") });

	$(`
		<div style="font-size:13px;line-height:1.6;">
			<p class="text-muted" style="margin-bottom:12px;">
				${__("Connect a compatible MCP client using the link below, then sign in with your usual Frappe login. The same link and access settings apply whichever client or model you use.")}
			</p>
			<div style="font-weight:600;margin-bottom:6px;">${__("Your MCP link")}</div>
			<div style="display:flex;gap:8px;align-items:center;">
				<input type="text" readonly class="form-control" style="font-family:monospace;font-size:12px;" value="${frappe.utils.escape_html(url)}">
				<button class="btn btn-primary btn-sm synapse-copy" style="white-space:nowrap;">${__("Copy")}</button>
			</div>
			<p class="text-muted" style="font-size:12px;margin-top:12px;">
				${__("The assistant only ever sees what your roles allow. Every action it takes is logged.")}
			</p>
		</div>
	`).appendTo(d.body);

	d.$wrapper.find(".synapse-copy").on("click", () => {
		if (url) frappe.utils.copy_to_clipboard(url);
	});
	d.show();
}
