// Copyright (c) 2026, Dxbitz and contributors

frappe.pages["synapse"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Synapse"),
		single_column: true,
	});
	wrapper.__synapse_console = new SynapseConsole(page);
};
frappe.pages["synapse"].on_page_show = function (wrapper) {
	wrapper.__synapse_console?.load();
};

class SynapseConsole {
	constructor(page) {
		this.page = page;
		this.request_id = 0;
		page.set_primary_action(__("Refresh"), () => this.load());
	}

	async load() {
		const request = ++this.request_id;
		this.page.main.html(
			`<div class="synapse-placeholder" role="status">${__("Loading dashboards...")}</div>`
		);
		try {
			const [context, pages] = await Promise.all([
				frappe.call("synapse.api.connect_context"),
				frappe.call("synapse.api.list_dashboard_pages"),
			]);
			if (request !== this.request_id) return;
			this.render(context.message || {}, pages.message || []);
		} catch (_) {
			if (request !== this.request_id) return;
			this.page.main.html(
				`<div class="synapse-placeholder" role="alert">${__(
					"Could not load dashboards. Use Refresh to try again."
				)}</div>`
			);
		}
	}

	render(context, pages) {
		const escape = frappe.utils.escape_html;
		this.page.main.empty();
		const root = document.createElement("div");
		root.className = "synapse-console";
		this.page.main.append(root);
		const heading = document.createElement("h2");
		heading.textContent = __("Dashboards");
		root.append(heading);
		if (context.is_admin) {
			const actions = document.createElement("div");
			actions.className = "synapse-toolbar";
			const links = [
				["New Dashboard", () => frappe.new_doc("Synapse Page")],
				["Pages", () => frappe.set_route("List", "Synapse Page")],
				["Data Scripts", () => frappe.set_route("List", "Synapse Script")],
				["Components", () => frappe.set_route("List", "Synapse Component")],
				["Profiles", () => frappe.set_route("List", "Synapse Profile")],
				["Settings", () => frappe.set_route("Form", "Synapse Settings", "Synapse Settings")],
				["Audit Log", () => frappe.set_route("List", "Synapse Log")],
				["Health Check", () => this.health_check()],
			];
			for (const [label, action] of links) {
				const button = document.createElement("button");
				button.className = "btn btn-default btn-sm";
				button.textContent = __(label);
				button.onclick = action;
				actions.append(button);
			}
			root.append(actions);
		}
		const search = document.createElement("input");
		search.className = "form-control synapse-dashboard-search";
		search.type = "search";
		search.placeholder = __("Find a dashboard");
		search.setAttribute("aria-label", __("Find a dashboard"));
		root.append(search);
		const list = document.createElement("div");
		list.className = "synapse-dashboard-list";
		root.append(list);
		const show = () => {
			list.replaceChildren();
			const query = search.value.toLocaleLowerCase();
			const matches = pages.filter((item) =>
				`${item.title} ${item.name}`.toLocaleLowerCase().includes(query)
			);
			for (const item of matches) {
				const link = document.createElement("a");
				link.className = "synapse-dashboard-card";
				link.href = `/app/synapse-view/${encodeURIComponent(item.name)}`;
				const title = document.createElement("strong");
				title.textContent = item.title || item.name;
				const detail = document.createElement("span");
				detail.className = "text-muted";
				detail.textContent = item.name;
				link.append(title, detail);
				list.append(link);
			}
			if (!matches.length) {
				const empty = document.createElement("p");
				empty.className = "text-muted";
				empty.textContent = pages.length
					? __("No matching dashboards.")
					: context.is_admin
					? __("Create a dashboard, add components, then share it with the people who need it.")
					: __(
							"No dashboards are available. Ask your administrator to share a dashboard with you."
					  );
				list.append(empty);
			}
		};
		search.oninput = show;
		show();
		if (context.is_admin || context.covered) {
			const connection = $(`<div class="synapse-connect-card"><strong>${__("MCP Endpoint")}</strong>
				<p class="text-muted">${__("Connect a compatible MCP client and sign in with your Frappe account.")}</p>
				<div class="synapse-toolbar"><input class="form-control" readonly aria-label="${__(
					"MCP Endpoint"
				)}" value="${escape(context.endpoint || "")}">
				<button class="btn btn-default btn-sm">${__("Copy")}</button></div></div>`).appendTo(root);
			connection
				.find("button")
				.on("click", () => frappe.utils.copy_to_clipboard(context.endpoint || ""));
		}
	}

	async health_check() {
		const response = await frappe.call("synapse.api.readiness_report");
		const dialog = new frappe.ui.Dialog({
			title: __("Synapse Health Check"),
			size: "large",
		});
		const pre = document.createElement("pre");
		pre.style.whiteSpace = "pre-wrap";
		pre.textContent = response.message || __("No output.");
		$(dialog.body).append(pre);
		dialog.show();
	}
}
