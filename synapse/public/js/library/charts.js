// Copyright (c) 2026, Dxbitz and contributors

import { chartsAvailable, placeholder } from "./theme.js";
import { chartShell, colors, empty, legend, validAxis, hasValues, text } from "./chart_helpers.js";
export { scatter_chart, bar_horizontal, map } from "./extra_charts.js";
export { heatmap } from "./heatmap.js";

const DEFAULT_HEIGHT = 260;

function mount(el, cfg, config, entries) {
	const body = chartShell(el, config);
	const host = document.createElement("div");
	host.className = "synapse-chart-host";
	body.append(host);
	try {
		host.__synapseChart = new frappe.Chart(host, { ...cfg, showLegend: 0 });
		host.__synapseChart.update(cfg.data);
		const svg = host.querySelector("svg");
		if (svg) {
			svg.setAttribute("role", "img");
			svg.setAttribute("aria-label", config.title || "Chart");
		}
		legend(body, entries, cfg.colors);
		return host.__synapseChart;
	} catch (e) {
		return placeholder(el, "This chart could not be drawn", String(e.message || e));
	}
}

function commonOptions(config, el) {
	const cfg = {};
	cfg.colors = colors(config, el);
	cfg.height = Math.max(180, Math.min(600, Number(config.height) || DEFAULT_HEIGHT));
	cfg.disableEntryAnimation = 1;
	cfg.animate = config.animate === true ? 1 : 0;
	if (config.truncate_legends) cfg.truncateLegends = 1;
	return cfg;
}

function axisChart(el, config, data, type, perDatasetType) {
	if (!chartsAvailable()) return placeholder(el, "Charts are not loaded on this page");
	if (!validAxis(data)) {
		return placeholder(
			el,
			"Chart data does not fit its template",
			"Expected { labels: [...], series: [{ name, values }] }"
		);
	}

	if (!hasValues(data)) return empty(chartShell(el, config));
	const datasets = data.series.map((s) => {
		const ds = { name: s.name, values: s.values };
		if (perDatasetType && s.chartType) ds.chartType = s.chartType;
		return ds;
	});

	const cfg = {
		type,
		data: { labels: data.labels, datasets },
		...commonOptions(config, el),
	};

	cfg.colors = data.series.map((_, i) => cfg.colors[i % cfg.colors.length]);
	const axisOptions = {};
	if (config.x_axis_mode) axisOptions.xAxisMode = config.x_axis_mode; // "span" | "tick"
	if (config.y_axis_mode) axisOptions.yAxisMode = config.y_axis_mode;
	if (config.shorten_y_numbers) axisOptions.shortenYAxisNumbers = 1;
	if (config.x_is_series) axisOptions.xIsSeries = 1;
	if (Object.keys(axisOptions).length) cfg.axisOptions = axisOptions;

	if (config.stacked || config.bar_space_ratio !== undefined) {
		cfg.barOptions = {};
		if (config.stacked) cfg.barOptions.stacked = 1;
		if (config.bar_space_ratio !== undefined) cfg.barOptions.spaceRatio = Number(config.bar_space_ratio);
	}

	const lineOptions = {};
	if (config.region_fill) lineOptions.regionFill = 1; // area fill under the line
	if (config.hide_dots) lineOptions.hideDots = 1;
	if (config.heatline) lineOptions.heatline = 1;
	if (Object.keys(lineOptions).length) cfg.lineOptions = lineOptions;

	if (config.value_labels) cfg.valuesOverPoints = 1;

	const chart = mount(el, cfg, config, data.series);
	if (data.axes && (data.axes.x || data.axes.y)) {
		const caption = text("div", "synapse-axis-caption", "");
		if (data.axes.y) caption.append(text("span", "", data.axes.y));
		if (data.axes.x) caption.append(text("span", "", data.axes.x));
		el.querySelector(".synapse-chart-body")?.append(caption);
	}
	return chart;
}

function validPartData(data) {
	return (
		data &&
		Array.isArray(data.labels) &&
		Array.isArray(data.values) &&
		data.labels.length === data.values.length &&
		data.values.every((v) => typeof v === "number" && Number.isFinite(v) && v >= 0)
	);
}

function partChart(el, config, data, type) {
	if (!chartsAvailable()) return placeholder(el, "Charts are not loaded on this page");
	if (!validPartData(data)) {
		return placeholder(
			el,
			"Chart data does not fit its template",
			"Expected { labels: [...], values: [...] }"
		);
	}

	if (!data.values.some((v) => v > 0)) return empty(chartShell(el, config));
	let entries = data.labels.map((name, i) => ({ name, value: data.values[i] }));
	const maxSlices = Math.max(2, Math.floor(Number(config.max_slices) || 20));
	if (entries.length > maxSlices) {
		entries.sort((a, b) => b.value - a.value);
		const remainder = entries.slice(maxSlices - 1).reduce((sum, item) => sum + item.value, 0);
		entries = [...entries.slice(0, maxSlices - 1), { name: "Other categories", value: remainder }];
	}
	const cfg = {
		type,
		data: {
			labels: entries.map((item) => item.name),
			datasets: [{ values: entries.map((item) => item.value) }],
		},
		...commonOptions(config, el),
		maxSlices: entries.length + 1,
	};
	cfg.colors = entries.map((_, i) => cfg.colors[i % cfg.colors.length]);
	const chart = mount(el, cfg, config, entries);
	const maxLegend = Math.max(1, Math.floor(Number(config.max_legend_points) || entries.length));
	if (entries.length > maxLegend) {
		const legendRows = el.querySelectorAll(".synapse-legend-item");
		legendRows.forEach((row, i) => {
			if (i >= maxLegend) row.remove();
		});
		el.querySelector(".synapse-chart-legend")?.append(
			text("span", "synapse-legend-label", `+${entries.length - maxLegend} categories`)
		);
	}
	return chart;
}

export function bar_chart(el, config, data) {
	return axisChart(el, config, data, "bar", false);
}

export function line_chart(el, config, data) {
	return axisChart(el, config, data, "line", false);
}

export function area_chart(el, config, data) {
	return axisChart(el, { ...config, region_fill: true }, data, "line", false);
}

export function mixed_chart(el, config, data) {
	return axisChart(el, config, data, "axis-mixed", true);
}

export function pie_chart(el, config, data) {
	return partChart(el, config, data, "pie");
}

export function donut_chart(el, config, data) {
	return partChart(el, config, data, "donut");
}

export function percentage_chart(el, config, data) {
	if (!validPartData(data)) return placeholder(el, "Chart data does not fit its template");
	const body = chartShell(el, config);
	const total = data.values.reduce((a, b) => a + b, 0);
	if (!total) return empty(body);
	const palette = colors(config, el);
	const track = text("div", "synapse-percentage-track", "");
	data.values.forEach((value, i) => {
		if (!value) return;
		const segment = text("div", "synapse-percentage-segment", "");
		segment.style.flexGrow = String(value);
		segment.style.background = palette[i % palette.length];
		segment.title = `${data.labels[i]}: ${value} (${((value / total) * 100).toFixed(1)}%)`;
		segment.tabIndex = 0;
		segment.setAttribute("aria-label", segment.title);
		track.append(segment);
	});
	body.append(track);
	legend(
		body,
		data.labels.map((name, i) => ({ name, value: data.values[i] })),
		palette
	);
	return track;
}
