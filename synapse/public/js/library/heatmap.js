// Copyright (c) 2026, Dxbitz and contributors
import { placeholder, cssVar } from "./theme.js";
import { chartShell, empty, text, colors } from "./chart_helpers.js";
const DAY = 86400000;
export function heatmap(el, config, data) {
	if (!data || !data.dataPoints || typeof data.dataPoints !== "object" || Array.isArray(data.dataPoints))
		return placeholder(el, "Heatmap data needs daily dataPoints");
	const entries = Object.entries(data.dataPoints);
	if (entries.some(([key, value]) => !Number.isFinite(Number(key)) || !Number.isFinite(value) || value < 0))
		return placeholder(el, "Heatmap needs numeric timestamps and non-negative values");
	const body = chartShell(el, config);
	if (!entries.length && !data.start && !data.end) return empty(body);
	const stamps = entries.map(([k]) => Number(k) * 1000);
	let start = data.start ? Date.parse(data.start) : Math.min(...stamps),
		end = data.end ? Date.parse(data.end) : Math.max(...stamps);
	if (!Number.isFinite(start) || !Number.isFinite(end) || end < start || end - start > 3660 * DAY)
		return placeholder(el, "Choose a valid calendar range of at most ten years");
	start = Math.floor(start / DAY) * DAY;
	end = Math.floor(end / DAY) * DAY;
	const first = start - new Date(start).getUTCDay() * DAY,
		max = Math.max(1, ...entries.map(([, v]) => v));
	const palette = config.colors?.length
		? colors(config, el)
		: [cssVar("--control-bg", el) || "#e7eef6", "#b7d5d3", "#71b6a5", "#379783", "#18715e"];
	const scroll = text("div", "synapse-heatmap-scroll", ""),
		wrap = text("div", "synapse-heatmap-calendar", ""),
		months = text("div", "synapse-heatmap-months", ""),
		grid = text("div", "synapse-heatmap-grid", "");
	const weeks = Math.ceil(((end - first) / DAY + 1) / 7);
	months.style.gridTemplateColumns = `repeat(${weeks}, 14px)`;
	let lastMonth = "";
	for (let w = 0; w < weeks; w++) {
		const date = new Date(Math.max(start, first + w * 7 * DAY));
		const month = date.toLocaleDateString(undefined, { month: "short", timeZone: "UTC" });
		const label = text("span", "", month === lastMonth ? "" : month);
		lastMonth = month;
		months.append(label);
	}
	for (let t = first; t <= end; t += DAY) {
		const date = new Date(t),
			value = Number(data.dataPoints[String(t / 1000)] || 0),
			cell = text("div", "synapse-heatmap-day", "");
		if (t < start) {
			cell.style.visibility = "hidden";
		} else {
			cell.style.background =
				palette[
					value === 0
						? 0
						: Math.min(palette.length - 1, Math.max(1, Math.ceil((value / max) * (palette.length - 1))))
				];
			cell.title = `${date.toISOString().slice(0, 10)}: ${value} ${config.count_label || "events"}`;
			cell.tabIndex = 0;
			cell.setAttribute("aria-label", cell.title);
		}
		grid.append(cell);
	}
	const days = text("div", "synapse-heatmap-days", "");
	["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].forEach((d, i) =>
		days.append(text("span", "", i % 2 ? d : ""))
	);
	const rows = text("div", "synapse-heatmap-rows", "");
	rows.append(days, grid);
	wrap.append(months, rows);
	scroll.append(wrap);
	body.append(scroll);
	const key = text("div", "synapse-heatmap-key", "Less");
	palette.forEach((color) => {
		const swatch = text("span", "", "");
		swatch.style.background = color;
		key.append(swatch);
	});
	key.append(document.createTextNode("More"));
	body.append(key);
	return grid;
}
