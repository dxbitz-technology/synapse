// Copyright (c) 2026, Dxbitz and contributors
// The Synapse app at /synapse. SynapseUI draws everything; this file only wires
// it to the server: the explorer list, one config call and one data call per
// dashboard, saved filters, and links out to the other apps.

(function () {
	const boot = window.synapse_boot || {};
	const UI = window.SynapseUI;
	const root = document.getElementById("synapse-app");
	if (!UI || !root) return;

	window.csrf_token = boot.csrf_token;
	UI.currency = boot.currency || "AED";
	UI.frappeTheme = false;

	const call = (method, args) => UI.call(`synapse.ui.${method}`, args);
	const h = UI.h;

	// ------------------------------------------------------------ theme
	const THEMES = { Light: "light", Dark: "dark", Automatic: "auto" };
	let stored = null;
	try {
		stored = localStorage.getItem("bz:theme");
	} catch (e) {
		stored = null;
	}
	if (!stored) UI.theme(THEMES[boot.theme] || "light");
	addEventListener("bz:theme", (e) => {
		const theme = { light: "Light", dark: "Dark", auto: "Automatic" }[e.detail];
		if (theme) UI.call("frappe.core.doctype.user.user.switch_theme", { theme }).catch(() => {});
	});

	// ------------------------------------------------------------ small notices
	function notice(text, kind) {
		const el = h("div", { class: "sy-toast" + (kind ? " sy-toast-" + kind : ""), role: "status" }, text);
		document.body.append(el);
		setTimeout(() => el.classList.add("sy-toast-out"), 2200);
		setTimeout(() => el.remove(), 2600);
	}

	// ------------------------------------------------------------ dashboard config
	// The values to save. Date ranges are read from the URL so a preset like
	// this_month stays a preset instead of freezing into two dates. Everything
	// else comes from the last load, so a cleared filter saves as cleared.
	function rawFilters(cfg, current) {
		const url = new URLSearchParams(location.search);
		const out = {};
		(cfg.filters || []).forEach((f) => {
			let v;
			if (f.type === "daterange") {
				v = url.has(f.key) ? url.get(f.key) : f.default;
				if (typeof v === "string" && v.includes(",")) v = v.split(",");
			} else {
				v = current && f.key in current ? current[f.key] : f.default;
			}
			if (v !== undefined && v !== null) out[f.key] = v;
		});
		return out;
	}

	function reopen(cfg) {
		location.href = location.pathname + "#/" + encodeURIComponent(cfg.id);
		location.reload();
	}

	function assistantNotes(cfg) {
		const a = cfg.assistant || {};
		return (el) => {
			const when = a.updated_on ? "Updated " + UI.fmt(a.updated_on, "datetime") : "Waiting for the first update";
			const every = a.refresh && a.refresh !== "On Request" ? ", refreshes every " + a.refresh.toLowerCase() : "";
			const paras = String(a.notes || "No notes yet.")
				.split(/\n{2,}/)
				.map((p) => h("p", null, p));
			el.replaceChildren(
				h(
					"div",
					{ class: "sy-assistant" },
					h("div", { class: "sy-assistant-h" }, h("span", { class: "bz-pill bz-pill-blue" }, "Assistant"), h("span", { class: "bz-muted" }, when + every)),
					h("div", { class: "sy-assistant-b" }, paras)
				)
			);
		};
	}

	function buildConfig(cfg) {
		const actions = [];
		let current = null;
		if ((cfg.filters || []).length && cfg.data_mode !== "Assistant") {
			actions.push({
				label: "Save filters",
				onClick: async () => {
					try {
						await call("save_dashboard_filters", { name: cfg.id, filters: rawFilters(cfg, current) });
						cfg.has_saved_filters = true;
						notice("Filters saved. They open by default next time.");
					} catch (e) {
						notice(e.message, "error");
					}
				},
			});
			if (cfg.has_saved_filters) {
				actions.push({
					label: "Clear saved filters",
					onClick: async () => {
						try {
							await call("reset_dashboard_filters", { name: cfg.id });
							reopen(cfg);
						} catch (e) {
							notice(e.message, "error");
						}
					},
				});
			}
		}
		if (cfg.can_edit) {
			actions.push({ label: "Edit", onClick: () => (location.href = "/app/synapse-page/" + encodeURIComponent(cfg.id)) });
		}

		const out = Object.assign({}, cfg, {
			actions,
			themeToggle: false,
			fetch: (filters) => call("get_dashboard_data", { name: cfg.id, filters }),
			onChange: (filters) => (current = filters),
		});

		if (cfg.data_mode === "Assistant") {
			if (out.type === "report") {
				const a = cfg.assistant || {};
				out.subtitle = [cfg.subtitle, a.updated_on ? "Assistant snapshot, updated " + UI.fmt(a.updated_on, "datetime") : "Assistant snapshot"]
					.filter(Boolean)
					.join(". ");
			} else {
				out.sections = [
					{ key: "sy-assistant", collapsible: false, widgets: [{ key: "sy-assistant", type: "html", col: 12, card: false, data: {}, render: assistantNotes(cfg) }] },
					...(cfg.sections || []),
				];
			}
		}
		return out;
	}

	// ------------------------------------------------------------ sidebar footer
	async function copyText(text) {
		try {
			await navigator.clipboard.writeText(text);
			return true;
		} catch (e) {
			// Clipboard API is blocked on plain http hosts other than localhost.
			const area = h("textarea", { style: { position: "fixed", opacity: "0" } }, text);
			document.body.append(area);
			area.select();
			const ok = document.execCommand && document.execCommand("copy");
			area.remove();
			return !!ok;
		}
	}

	function mcpButton() {
		if (!boot.mcp_endpoint) return null;
		return h(
			"button",
			{
				type: "button",
				class: "bz-btn sy-mcp-btn",
				title: boot.mcp_endpoint,
				onclick: async () => {
					const ok = await copyText(boot.mcp_endpoint);
					notice(ok ? "MCP link copied. Paste it into your MCP client as a remote server." : boot.mcp_endpoint, ok ? null : "error");
				},
			},
			h("span", { class: "sy-link-ico", "aria-hidden": "true" }),
			"Copy MCP link"
		);
	}

	function footer() {
		const apps = (boot.apps || []).map((a) => ({ label: a.title, onClick: () => (location.href = a.route) }));
		const account = [
			{ label: "Open Desk", onClick: () => (location.href = "/app") },
			boot.is_admin && { label: "Synapse settings", onClick: () => (location.href = "/app/synapse") },
			boot.is_admin && { label: "New dashboard", onClick: () => (location.href = "/app/synapse-page/new") },
			{
				label: "Log out",
				danger: true,
				onClick: () => UI.call("logout").finally(() => (location.href = "/login")),
			},
		].filter(Boolean);
		const initials = String(boot.full_name || "?")
			.split(/\s+/)
			.filter(Boolean)
			.slice(0, 2)
			.map((w) => w[0].toUpperCase())
			.join("");
		return h(
			"div",
			{ class: "sy-foot-wrap" },
			mcpButton(),
			h(
			"div",
			{ class: "sy-foot" },
			h(
				"button",
				{ type: "button", class: "bz-btn sy-apps-btn", "aria-label": "Switch app", onclick: (e) => UI.menu(e.currentTarget, apps) },
				h("span", { class: "sy-grid-ico", "aria-hidden": "true" }, h("i"), h("i"), h("i"), h("i")),
				"Apps"
			),
			h(
				"button",
				{ type: "button", class: "sy-user", "aria-label": "Account", title: boot.full_name, onclick: (e) => UI.menu(e.currentTarget, account) },
				boot.user_image ? h("img", { src: boot.user_image, alt: "" }) : h("span", null, initials)
			)
		)
		);
	}

	// ------------------------------------------------------------ start
	const app = UI.app(root, {
		title: "Synapse",
		themeToggle: true,
		footer: footer(),
		items: async () => {
			let list = [];
			let failed = null;
			try {
				list = (await call("list_dashboards")) || [];
			} catch (e) {
				failed = e;
			}
			if (!list.length) {
				const text = failed
					? "Could not load dashboards: " + (failed.message || failed) + ". Refresh to try again."
					: "No dashboards yet. Ask an admin to create one or share one with you.";
				setTimeout(() => app.message(h("div", { class: "bz-empty sy-empty" + (failed ? " sy-error" : "") }, text)));
			}
			return list.map((m) => Object.assign({}, m, { load: async (it) => buildConfig(await call("get_dashboard", { name: it.id })) }));
		},
	});
	window.synapse_app = app;
})();
