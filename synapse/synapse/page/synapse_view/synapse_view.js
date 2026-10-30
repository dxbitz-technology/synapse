// Copyright (c) 2026, Dxbitz and contributors

frappe.pages["synapse-view"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Synapse View"),
		single_column: true,
	});
	wrapper.__synapse = new SynapsePageView(page);
};

frappe.pages["synapse-view"].on_page_show = function (wrapper) {
	if (wrapper.__synapse) wrapper.__synapse.load();
};

frappe.pages["synapse-view"].on_page_hide = function (wrapper) {
	if (wrapper.__synapse) wrapper.__synapse.dispose();
};

class SynapsePageView {
	constructor(page) {
		this.page = page;
		this.page.set_primary_action(__("Refresh"), () => this.load());
		this.request_id = 0;
		this.page.add_inner_button?.(__("Dashboards"), () => frappe.set_route("synapse"));
	}

	dispose() {
		this.request_id++;
		if (this.page.main[0] && window.synapse?.library) synapse.library.clear?.(this.page.main[0]);
	}

	route_name() {
		const route = frappe.get_route() || [];
		return route[1] || null;
	}

	load() {
		this.dispose();
		this.page.clear_secondary_action?.();
		if (!(window.synapse && synapse.library && synapse.library.render_page)) {
			this.page.main.html(
				placeholder("Library bundle not loaded", "Run bench build --app synapse and reload.")
			);
			return;
		}

		const name = this.route_name();
		if (!name) {
			this.page.main.html(
				placeholder(
					"No page named",
					"Open /app/synapse-view/<name>, or pick a Synapse Page from the list."
				)
			);
			return;
		}

		const request_id = ++this.request_id;
		this.page.main.html(`<div class="text-muted" style="padding:24px;">${__("Loading...")}</div>`);
		frappe.call("synapse.api.get_page_layout", { name, include_data: 0 }).then(
			(r) => {
				if (request_id !== this.request_id) return;
				const model = r && r.message;
				if (!model) {
					this.page.main.html(placeholder("Page not found", name));
					return;
				}
				if (!model.enabled) {
					this.page.main.html(placeholder(__("This page is disabled.")));
					return;
				}
				this.page.set_title(model.title || name);
				const host = document.createElement("div");
				this.page.main.empty().append(host);
				synapse.library.render_page(host, model);
				if (model.can_edit)
					this.page.set_secondary_action?.(__("Edit Dashboard"), () =>
						frappe.set_route("Form", "Synapse Page", name)
					);
				const status = document.createElement("div");
				status.className = "synapse-view-status";
				status.setAttribute("role", "status");
				host.append(status);
				this.load_blocks(host, model, status, request_id);
			},
			() => {
				if (request_id === this.request_id)
					this.page.main.html(placeholder("Could not load page", name));
			}
		);
	}

	async load_blocks(host, model, status, request_id) {
		const pending = (model.blocks || []).filter((block) => block.pending);
		const hasSnapshots = (model.blocks || []).some(
			(block) =>
				!block.live && !["section_break", "column_break", "spacer"].includes(block.component_type)
		);
		let failures = (model.blocks || []).filter((block) => block.data_error).length;
		status.textContent = pending.length ? __("Loading current data...") : "";
		const worker = async () => {
			while (pending.length && request_id === this.request_id) {
				const block = pending.shift();
				const cell = Array.from(host.querySelectorAll("[data-block-name]")).find(
					(item) => item.dataset.blockName === block.name
				);
				if (!cell) continue;
				const body = cell.querySelector(".synapse-page-block-body");
				try {
					const response = await frappe.call("synapse.api.get_page_block_data", {
						name: model.name,
						block_name: block.name,
					});
					if (request_id !== this.request_id) return;
					const current = response.message;
					if (!current || current.data_error) throw new Error("unavailable");
					synapse.library.render(body, current.component_type, current.config, current.frozen_data);
				} catch (_) {
					if (request_id !== this.request_id) return;
					failures++;
					synapse.library.clear?.(body);
					body.textContent = __(
						"Current data unavailable. Check the script and your access, then refresh."
					);
					body.setAttribute("role", "alert");
				}
			}
		};
		await Promise.all(Array.from({ length: Math.min(3, pending.length) }, worker));
		if (request_id !== this.request_id) return;
		status.textContent = failures
			? __("Some components could not load.")
			: __("Loaded") + " " + new Date().toLocaleTimeString();
		if (hasSnapshots) status.textContent += " · " + __("Includes saved snapshots");
	}
}

function placeholder(title, sub) {
	return (
		`<div class="synapse-placeholder" style="margin:24px;">` +
		`<div class="synapse-placeholder-title">${frappe.utils.escape_html(title)}</div>` +
		(sub ? `<div class="synapse-placeholder-sub">${frappe.utils.escape_html(sub)}</div>` : "") +
		`</div>`
	);
}
