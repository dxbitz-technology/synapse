// Copyright (c) 2026, Dxbitz and contributors

export function cssVar(name, el) {
	const node = el || document.documentElement;
	const value = getComputedStyle(node).getPropertyValue(name);
	return (value || "").trim();
}

const PALETTE_FAMILIES = new Set([
	"blue",
	"green",
	"red",
	"orange",
	"yellow",
	"purple",
	"pink",
	"cyan",
	"teal",
	"violet",
	"gray",
	"grey",
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
	const fallback = ["#3974d9", "#229a83", "#e3a34a", "#946bca", "#dd7280", "#56a5bd"];
	return colors.map((c, i) => {
		const resolved = resolveColor(c, el);
		return typeof resolved === "string" && CSS.supports("color", resolved)
			? resolved
			: fallback[i % fallback.length];
	});
}

export function formatValue(value, type, options) {
	const opts = options || {};
	if (value === null || value === undefined || value === "") return "";

	try {
		switch (type) {
			case "currency":
				if (window.format_currency) return format_currency(value, opts.currency, opts.precision);
				return new Intl.NumberFormat(undefined, {
					style: "currency",
					currency: opts.currency || "AED",
					maximumFractionDigits: opts.precision ?? 2,
				}).format(Number(value));
			case "int":
				if (window.frappe && frappe.format_number) return frappe.format_number(value, null, 0);
				return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(Number(value));
			case "float":
			case "number":
				if (window.frappe && frappe.format_number) return frappe.format_number(value, null, opts.precision);
				return new Intl.NumberFormat(undefined, { maximumFractionDigits: opts.precision ?? 2 }).format(
					Number(value)
				);
			case "percent":
				if (window.frappe && frappe.format_number)
					return frappe.format_number(value, null, opts.precision) + "%";
				return (
					new Intl.NumberFormat(undefined, { maximumFractionDigits: opts.precision ?? 2 }).format(
						Number(value)
					) + "%"
				);
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
	for (const host of [el, ...el.querySelectorAll(".synapse-chart-host")]) {
		if (host.__synapseChart) {
			try {
				host.__synapseChart.destroy?.();
				host.__synapseChart.update = () => {};
				host.__synapseChart.draw = () => {};
			} catch (_) {
				/* Detached charts may already be disposed. */
			}
			host.__synapseChart = null;
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
