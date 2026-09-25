// Copyright (c) 2026, Dxbitz and contributors

import { clearEl, formatValue, placeholder, shell } from "./theme.js";

function elem(tag, className, text) {
	const node = document.createElement(tag);
	if (className) node.className = className;
	if (text !== undefined && text !== null) node.textContent = String(text);
	return node;
}

export function number_card(el, config, data) {
	if (!data || data.value === undefined || data.value === null) {
		return placeholder(el, "Number card has no value");
	}
	clearEl(el);
	const card = elem("div", "synapse-number-card");

	const label = data.label || config.title || "";
	if (label) card.appendChild(elem("div", "synapse-number-label", label));

	const value = formatValue(data.value, config.value_type || "number", {
		currency: config.currency,
		precision: config.precision,
	});
	card.appendChild(elem("div", "synapse-number-value", value));

	if (data.delta !== undefined && data.delta !== null) {
		const trend = data.trend || (data.delta > 0 ? "up" : data.delta < 0 ? "down" : "flat");
		const row = elem("div", `synapse-number-delta trend-${trend}`);
		const arrow = trend === "up" ? "↑" : trend === "down" ? "↓" : "→";
		row.appendChild(elem("span", "synapse-delta-arrow", arrow));
		const deltaText = formatValue(Math.abs(data.delta), config.delta_type || "number", {
			precision: config.precision,
		});
		row.appendChild(elem("span", "synapse-delta-value", config.delta_is_percent === false ? deltaText : deltaText + "%"));
		card.appendChild(row);
	}

	el.appendChild(card);
	return card;
}

const RIGHT_TYPES = new Set(["currency", "int", "float", "number", "percent"]);

export function table(el, config, data) {
	if (!data || !Array.isArray(data.columns) || !Array.isArray(data.rows)) {
		return placeholder(el, "Table data does not fit its template", "Expected { columns: [...], rows: [...] }");
	}
	const body = shell(el, config.title);
	const t = elem("table", "synapse-table");

	const thead = elem("thead");
	const htr = elem("tr");
	data.columns.forEach((c) => {
		const th = elem("th", RIGHT_TYPES.has(c.type) ? "text-right" : null, c.label || c.key);
		htr.appendChild(th);
	});
	thead.appendChild(htr);
	t.appendChild(thead);

	const tbody = elem("tbody");
	data.rows.forEach((row) => {
		const tr = elem("tr");
		data.columns.forEach((c) => {
			const td = elem("td", RIGHT_TYPES.has(c.type) ? "text-right" : null);
			td.textContent = formatValue(row[c.key], c.type, { currency: config.currency, precision: c.precision });
			tr.appendChild(td);
		});
		tbody.appendChild(tr);
	});
	t.appendChild(tbody);
	body.appendChild(t);
	return t;
}

export function list(el, config, data) {
	if (!data || !Array.isArray(data.items)) {
		return placeholder(el, "List data does not fit its template", "Expected { items: [{ label, value }] }");
	}
	const body = shell(el, config.title);
	const wrap = elem("div", "synapse-list");

	data.items.forEach((item) => {
		const rowEl = elem("div", "synapse-list-row");
		if (typeof item.bar === "number") {
			const fill = elem("div", "synapse-list-bar");
			fill.style.width = Math.max(0, Math.min(1, item.bar)) * 100 + "%";
			rowEl.appendChild(fill);
		}
		rowEl.appendChild(elem("span", "synapse-list-label", item.label));
		rowEl.appendChild(
			elem("span", "synapse-list-value", formatValue(item.value, config.value_type || "number", {
				currency: config.currency,
				precision: config.precision,
			})),
		);
		wrap.appendChild(rowEl);
	});
	body.appendChild(wrap);
	return wrap;
}

export function progress(el, config, data) {
	if (!data || data.value === undefined || data.target === undefined) {
		return placeholder(el, "Progress data does not fit its template", "Expected { value, target }");
	}
	const body = shell(el, config.title);
	const wrap = elem("div", "synapse-progress");

	const target = Number(data.target) || 0;
	const value = Number(data.value) || 0;
	const ratio = target > 0 ? Math.max(0, Math.min(1, value / target)) : 0;

	const head = elem("div", "synapse-progress-head");
	head.appendChild(elem("span", "synapse-progress-label", data.label || config.title || ""));
	const vt = config.value_type || "number";
	head.appendChild(
		elem("span", "synapse-progress-figures",
			formatValue(value, vt, { currency: config.currency }) + " / " + formatValue(target, vt, { currency: config.currency })),
	);
	wrap.appendChild(head);

	const track = elem("div", "synapse-progress-track");
	const fill = elem("div", "synapse-progress-fill");
	fill.style.width = ratio * 100 + "%";
	track.appendChild(fill);
	wrap.appendChild(track);

	wrap.appendChild(elem("div", "synapse-progress-percent", Math.round(ratio * 100) + "%"));
	body.appendChild(wrap);
	return wrap;
}

export function pivot(el, config, data) {
	const ok = data && Array.isArray(data.rowLabels) && Array.isArray(data.colLabels) && Array.isArray(data.cells);
	if (!ok) {
		return placeholder(el, "Pivot data does not fit its template", "Expected { rowLabels, colLabels, cells: [[...]] }");
	}
	const body = shell(el, config.title);
	const t = elem("table", "synapse-table synapse-pivot");
	const measureType = data.measureType || config.value_type || "number";

	const thead = elem("thead");
	const htr = elem("tr");
	htr.appendChild(elem("th", null, data.corner || ""));
	data.colLabels.forEach((c) => htr.appendChild(elem("th", "text-right", c)));
	if (config.row_totals) htr.appendChild(elem("th", "text-right", "Total"));
	thead.appendChild(htr);
	t.appendChild(thead);

	const tbody = elem("tbody");
	data.rowLabels.forEach((rLabel, i) => {
		const tr = elem("tr");
		tr.appendChild(elem("th", "synapse-pivot-rowhead", rLabel));
		const cells = data.cells[i] || [];
		let total = 0;
		data.colLabels.forEach((_c, j) => {
			const v = cells[j];
			total += Number(v) || 0;
			tr.appendChild(elem("td", "text-right", formatValue(v, measureType, { currency: config.currency })));
		});
		if (config.row_totals) tr.appendChild(elem("td", "text-right synapse-pivot-total", formatValue(total, measureType, { currency: config.currency })));
		tbody.appendChild(tr);
	});
	t.appendChild(tbody);
	body.appendChild(t);
	return t;
}

const CALLOUT_LEVELS = new Set(["info", "success", "warning", "danger"]);

export function callout(el, config, data) {
	if (!data || (!data.title && !data.body)) {
		return placeholder(el, "Callout has no content");
	}
	clearEl(el);
	const level = CALLOUT_LEVELS.has(data.level) ? data.level : "info";
	const box = elem("div", `synapse-callout level-${level}`);
	if (data.title) box.appendChild(elem("div", "synapse-callout-title", data.title));
	if (data.body) box.appendChild(elem("div", "synapse-callout-body", data.body));
	el.appendChild(box);
	return box;
}

export function text_block(el, config, data) {
	const md = (data && (data.markdown || data.text)) || "";
	clearEl(el);
	const box = elem("div", "synapse-text-block");
	try {
		if (window.frappe && frappe.markdown) {
			box.appendChild(safeMarkdown(frappe.markdown(String(md))));
		} else {
			box.textContent = md;
		}
	} catch (e) {
		box.textContent = md;
	}
	el.appendChild(box);
	return box;
}

function safeMarkdown(html) {
	const template = document.createElement("template");
	template.innerHTML = html;
	const allowed = new Set(["P", "BR", "STRONG", "B", "EM", "I", "DEL", "S", "CODE", "PRE", "BLOCKQUOTE", "UL", "OL", "LI", "H1", "H2", "H3", "H4", "H5", "H6", "HR", "TABLE", "THEAD", "TBODY", "TR", "TH", "TD", "A"]);
	const discard = new Set(["SCRIPT", "STYLE", "IFRAME", "OBJECT", "EMBED", "SVG", "MATH", "FORM", "TEMPLATE"]);
	function copy(source, target) {
		for (const node of source.childNodes) {
			if (node.nodeType === Node.TEXT_NODE) {
				target.appendChild(document.createTextNode(node.textContent));
			} else if (node.nodeType === Node.ELEMENT_NODE && !discard.has(node.tagName)) {
				if (!allowed.has(node.tagName)) {
					copy(node, target);
					continue;
				}
				const clean = document.createElement(node.tagName.toLowerCase());
				if (node.tagName === "A" && node.hasAttribute("href")) {
					try {
						const url = new URL(node.getAttribute("href"), document.baseURI);
						if (["https:", "http:", "mailto:"].includes(url.protocol)) {
							clean.setAttribute("href", url.href);
							clean.setAttribute("rel", "noopener noreferrer");
						}
					} catch (_) { /* Ignore invalid links. */ }
				}
				copy(node, clean);
				target.appendChild(clean);
			}
		}
	}
	const fragment = document.createDocumentFragment();
	copy(template.content, fragment);
	return fragment;
}
