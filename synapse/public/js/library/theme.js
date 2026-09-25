// Copyright (c) 2026, Dxbitz and contributors

export function cssVar(name, el) {
	const node = el || document.documentElement;
	const value = getComputedStyle(node).getPropertyValue(name);
	return (value || "").trim();
}

const PALETTE_FAMILIES = new Set([
	"blue", "green", "red", "orange", "yellow", "purple",
	"pink", "cyan", "teal", "violet", "gray", "grey",
]);

export function resolveColor(token, el) {
	if (typeof token !== "string" || !token) return token;
	const t = token.trim();

	if (t.startsWith("#") || t.startsWith("rgb") || t.startsWith("hsl")) return t;
	if (t.startsWith("--")) return cssVar(t, el) || t;

	const family = t.includes("-") ? t.split("-")[0] : t;
	if (PALETTE_FAMILIES.has(family)) {
		const name = t.includes("-") ? `--${t}` : `--${t}-500`;
		return cssVar(name, el) || t;
	}
	return t;
}

export function resolveColors(colors, el) {
	if (!Array.isArray(colors) || !colors.length) return undefined;
	return colors.map((c) => resolveColor(c, el));
}

export function formatValue(value, type, options) {
	const opts = options || {};
	if (value === null || value === undefined || value === "") return "";

	try {
		switch (type) {
			case "currency":
				if (window.format_currency) return format_currency(value, opts.currency);
				return String(value);
			case "int":
				if (window.frappe && frappe.format_number) return frappe.format_number(value, null, 0);
				return String(Math.round(value));
			case "float":
			case "number":
				if (window.frappe && frappe.format_number) return frappe.format_number(value, null, opts.precision);
				return String(value);
			case "percent":
				if (window.frappe && frappe.format_number) return frappe.format_number(value, null, opts.precision) + "%";
				return value + "%";
			case "date":
				if (window.frappe && frappe.datetime && frappe.datetime.str_to_user) {
					return frappe.datetime.str_to_user(value);
				}
				return String(value);
			case "link":
			case "text":
			default:
				return String(value);
		}
	} catch (e) {
		return String(value);
	}
}

export function clearEl(el) {
	if (!el) return;
	if (el.__synapseChart) {
		try {
			el.__synapseChart = null;
		} catch (e) {
			/* nothing to do */
		}
	}
	el.innerHTML = "";
}

export function placeholder(el, message, sub) {
	clearEl(el);
	const box = document.createElement("div");
	box.className = "synapse-placeholder";
	const title = document.createElement("div");
	title.className = "synapse-placeholder-title";
	title.textContent = message || "Nothing to show";
	box.appendChild(title);
	if (sub) {
		const s = document.createElement("div");
		s.className = "synapse-placeholder-sub";
		s.textContent = sub;
		box.appendChild(s);
	}
	el.appendChild(box);
	return box;
}

export function shell(el, title) {
	clearEl(el);
	const wrap = document.createElement("div");
	wrap.className = "synapse-component";
	if (title) {
		const h = document.createElement("div");
		h.className = "synapse-component-title";
		h.textContent = title;
		wrap.appendChild(h);
	}
	const body = document.createElement("div");
	body.className = "synapse-component-body";
	wrap.appendChild(body);
	el.appendChild(wrap);
	return body;
}

export function chartsAvailable() {
	return !!(window.frappe && frappe.Chart);
}
