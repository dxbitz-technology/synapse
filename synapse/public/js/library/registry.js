// Copyright (c) 2026, Dxbitz and contributors

import * as charts from "./charts.js";
import * as widgets from "./widgets.js";
import * as layout from "./layout.js";
import { placeholder } from "./theme.js";

export const RENDERERS = {
	bar_chart: charts.bar_chart,
	bar_horizontal: charts.bar_horizontal, // not native in this build, placeholder
	line_chart: charts.line_chart,
	area_chart: charts.area_chart,
	scatter_chart: charts.scatter_chart, // not native in this build, placeholder
	pie_chart: charts.pie_chart,
	donut_chart: charts.donut_chart,
	percentage_chart: charts.percentage_chart,
	mixed_chart: charts.mixed_chart,
	heatmap: charts.heatmap,
	map: charts.map, // deferred, placeholder

	number_card: widgets.number_card,
	table: widgets.table,
	list: widgets.list,
	progress: widgets.progress,
	pivot: widgets.pivot,
	callout: widgets.callout,
	text_block: widgets.text_block,

	section_break: layout.section_break,
	column_break: layout.column_break,
	spacer: layout.spacer,
};

export function resolve(componentType) {
	const fn = RENDERERS[componentType];
	if (fn) return fn;
	return function unknown(el) {
		return placeholder(el, "Unknown component", `No renderer for "${componentType}"`);
	};
}

export function render(el, componentType, config, data) {
	const fn = resolve(componentType);
	try {
		return fn(el, config || {}, data || {});
	} catch (e) {
		return placeholder(el, "This component could not render", String(e && e.message ? e.message : e));
	}
}

export function known_types() {
	return Object.keys(RENDERERS);
}
