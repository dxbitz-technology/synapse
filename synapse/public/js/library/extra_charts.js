// Copyright (c) 2026, Dxbitz and contributors
import { placeholder, formatValue } from "./theme.js";
import {
	chartShell,
	colors,
	empty,
	legend,
	text,
	svgNode,
	svgChart,
	pointTitle,
	validAxis,
	hasValues,
	compact,
} from "./chart_helpers.js";
import { LAND } from "./land.js";

export function bar_horizontal(el, config, data) {
	if (!validAxis(data))
		return placeholder(el, "Chart data does not fit its template", "Series must match the category labels.");
	const body = chartShell(el, config);
	if (!hasValues(data)) return empty(body);
	const palette = colors(config, el),
		values = data.series.flatMap((s) => s.values).filter((v) => v !== null);
	const min = Math.min(0, ...values),
		max = Math.max(0, ...values),
		range = max - min || 1,
		zero = (-min / range) * 100;
	const list = text("div", "synapse-horizontal-bars", "");
	data.labels.forEach((label, i) => {
		const group = text("div", "synapse-horizontal-group", "");
		group.append(text("div", "synapse-horizontal-label", label));
		for (const [j, series] of data.series.entries()) {
			if (series.values[i] === null) continue;
			const value = series.values[i],
				row = text("div", "synapse-horizontal-row", ""),
				track = text("div", "synapse-horizontal-track", ""),
				bar = text("div", "synapse-horizontal-fill", "");
			track.style.setProperty("--zero", `${zero}%`);
			bar.style.left = `${Math.min(zero, ((value - min) / range) * 100)}%`;
			bar.style.width = `${(Math.abs(value) / range) * 100}%`;
			bar.style.background = palette[j % palette.length];
			bar.title = `${label} · ${series.name || ""}: ${formatValue(value, "number")}`;
			bar.tabIndex = 0;
			bar.setAttribute("aria-label", bar.title);
			track.append(bar);
			row.append(track, text("span", "synapse-horizontal-value", compact(value)));
			group.append(row);
		}
		list.append(group);
	});
	body.append(list);
	legend(body, data.series, palette);
	return list;
}

function extent(values) {
	let min = Math.min(...values),
		max = Math.max(...values);
	const pad = (max - min) * 0.12 || Math.max(Math.abs(min) * 0.1, 1);
	return [min - pad, max + pad];
}
export function scatter_chart(el, config, data) {
	if (!validAxis(data) || !data.labels.every((v) => Number.isFinite(Number(v))))
		return placeholder(el, "Scatter data needs numeric x labels and matching series");
	const body = chartShell(el, config);
	if (!hasValues(data)) return empty(body);
	const palette = colors(config, el),
		[x0, x1] = extent(data.labels.map(Number)),
		[y0, y1] = extent(data.series.flatMap((s) => s.values).filter((v) => v !== null));
	const narrow = body.clientWidth < 420;
	const height = narrow ? 390 : 290;
	const svg = svgChart(body, config, height),
		left = 64,
		right = 574,
		top = 18,
		bottom = height - 52;
	const x = (v) => left + ((Number(v) - x0) / (x1 - x0)) * (right - left),
		y = (v) => bottom - ((v - y0) / (y1 - y0)) * (bottom - top);
	for (let i = 0; i <= 4; i++) {
		const yv = y0 + ((y1 - y0) * i) / 4,
			ypos = y(yv),
			xv = x0 + ((x1 - x0) * i) / 4,
			xpos = x(xv);
		svg.append(
			svgNode("line", { x1: left, x2: right, y1: ypos, y2: ypos, class: "synapse-svg-grid" }),
			svgNode(
				"text",
				{ x: left - 12, y: ypos + 4, "text-anchor": "end", class: "synapse-svg-tick" },
				compact(yv)
			),
			svgNode(
				"text",
				{ x: xpos, y: bottom + 21, "text-anchor": "middle", class: "synapse-svg-tick" },
				compact(xv)
			)
		);
	}
	svg.append(svgNode("line", { x1: left, x2: left, y1: top, y2: bottom, class: "synapse-svg-axis" }));
	data.series.forEach((series, j) =>
		series.values.forEach((value, i) => {
			if (value === null) return;
			const dot = svgNode("circle", {
				cx: x(data.labels[i]),
				cy: y(value),
				r: narrow ? 8 : 5.5,
				fill: palette[j % palette.length],
				class: "synapse-scatter-point",
			});
			pointTitle(dot, `${series.name || "Series"} · ${data.labels[i]}, ${formatValue(value, "number")}`);
			svg.append(dot);
		})
	);
	if (data.axes?.x)
		svg.append(
			svgNode(
				"text",
				{ x: (left + right) / 2, y: height - 7, "text-anchor": "middle", class: "synapse-svg-tick" },
				data.axes.x
			)
		);
	if (data.axes?.y) body.prepend(text("div", "synapse-chart-unit", data.axes.y));
	legend(body, data.series, palette);
	return svg;
}

export function map(el, config, data) {
	const valid =
		data &&
		Array.isArray(data.points) &&
		data.points.every(
			(p) =>
				p &&
				typeof p.label === "string" &&
				Number.isFinite(p.latitude) &&
				Number.isFinite(p.longitude) &&
				p.latitude >= -90 &&
				p.latitude <= 90 &&
				p.longitude >= -180 &&
				p.longitude <= 180 &&
				(p.value === undefined || (Number.isFinite(p.value) && p.value >= 0))
		);
	if (!valid) return placeholder(el, "Map data needs labelled latitude and longitude points");
	const body = chartShell(el, config);
	if (!data.points.length) return empty(body, "No locations for this period");
	const palette = colors(config, el),
		svg = svgChart(body, config, 300),
		points = data.points;
	let [west, east] = extent(points.map((p) => p.longitude)),
		[south, north] = extent(points.map((p) => p.latitude));
	let width = Math.max(22, east - west),
		height = Math.max(16, north - south, width / 2),
		cx = (east + west) / 2,
		cy = (north + south) / 2;
	width = Math.max(width, height * 2);
	if (width > 360 || height > 180) {
		width = 360;
		height = 180;
		cx = 0;
		cy = 0;
	}
	cx = Math.max(-180 + width / 2, Math.min(180 - width / 2, cx));
	cy = Math.max(-90 + height / 2, Math.min(90 - height / 2, cy));
	west = cx - width / 2;
	north = cy + height / 2;
	const project = ([lon, lat]) => [((lon - west) / width) * 600, ((north - lat) / height) * 300];
	const ocean = svgNode("rect", { width: 600, height: 300, class: "synapse-map-ocean" });
	svg.append(ocean);
	// Paths are clipped by the SVG viewport. No map service receives the location data.
	for (const ring of LAND) {
		const path =
			ring
				.map(
					(p, i) =>
						`${i ? "L" : "M"}${project(p)
							.map((v) => v.toFixed(1))
							.join(",")}`
				)
				.join("") + "Z";
		svg.append(svgNode("path", { d: path, class: "synapse-map-land" }));
	}
	const max = Math.max(...points.map((p) => p.value || 0), 1);
	points.forEach((p) => {
		const [x, y] = project([p.longitude, p.latitude]);
		const dot = svgNode("circle", {
			cx: x,
			cy: y,
			r: 5 + Math.sqrt((p.value || 0) / max) * 9,
			fill: palette[0],
			class: "synapse-map-point",
		});
		pointTitle(dot, `${p.label}${p.value !== undefined ? `: ${formatValue(p.value, "number")}` : ""}`);
		svg.append(dot);
	});
	const items = points.map((p) => ({ name: p.label, ...(p.value !== undefined ? { value: p.value } : {}) }));
	legend(body, items, [palette[0]]);
	body.append(text("div", "synapse-map-credit", "Made with Natural Earth"));
	return svg;
}
