// Copyright (c) 2026, Dxbitz and contributors
import { shell, resolveColors, formatValue } from "./theme.js";
export const PALETTE = [
	"#3974d9",
	"#229a83",
	"#e3a34a",
	"#946bca",
	"#dd7280",
	"#56a5bd",
	"#8c9470",
	"#a77858",
];
export function colors(config, el) {
	return resolveColors(config.colors, el) || PALETTE;
}
export function chartShell(el, config) {
	const body = shell(el, config.title);
	body.classList.add("synapse-chart-body");
	return body;
}
export function empty(body, message = "No data for this period") {
	const node = document.createElement("div");
	node.className = "synapse-empty";
	node.textContent = message;
	body.append(node);
	return node;
}
export function text(tag, className, value) {
	const node = document.createElement(tag);
	node.className = className;
	node.textContent = String(value ?? "");
	return node;
}
export function compact(value) {
	return new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(value);
}
export function legend(body, entries, palette) {
	const wrap = text("div", "synapse-chart-legend", "");
	entries.forEach((entry, i) => {
		const row = text("div", "synapse-legend-item", "");
		const dot = text("span", "synapse-legend-dot", "");
		dot.style.background = palette[i % palette.length];
		row.append(dot, text("span", "synapse-legend-label", entry.name));
		if (entry.value !== undefined)
			row.append(text("span", "synapse-legend-value", formatValue(entry.value, "number")));
		wrap.append(row);
	});
	body.append(wrap);
	return wrap;
}
export function svgNode(tag, attrs = {}, label) {
	const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
	for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
	if (label !== undefined) node.textContent = String(label);
	return node;
}
export function svgChart(body, config, height = 260) {
	const svg = svgNode("svg", {
		viewBox: `0 0 600 ${height}`,
		role: "img",
		"aria-label": config.title || "Chart",
		class: "synapse-svg-chart",
	});
	body.append(svg);
	return svg;
}
export function pointTitle(node, label) {
	node.append(svgNode("title", {}, label));
	node.setAttribute("tabindex", "0");
	node.setAttribute("aria-label", label);
}
export function validAxis(data) {
	return (
		data &&
		Array.isArray(data.labels) &&
		Array.isArray(data.series) &&
		data.series.length > 0 &&
		data.series.every(
			(s) =>
				s &&
				Array.isArray(s.values) &&
				s.values.length === data.labels.length &&
				s.values.every((v) => v === null || (typeof v === "number" && Number.isFinite(v)))
		)
	);
}
export function hasValues(data) {
	return data.labels.length && data.series.some((s) => s.values.some((v) => v !== null));
}
