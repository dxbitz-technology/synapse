// Copyright (c) 2026, Dxbitz and contributors

import { clearEl } from "./theme.js";

export function section_break(el, config) {
	clearEl(el);
	const wrap = document.createElement("div");
	wrap.className = "synapse-section-break";
	if (config && config.title) {
		const h = document.createElement("div");
		h.className = "synapse-section-title";
		h.textContent = config.title;
		wrap.appendChild(h);
	}
	el.appendChild(wrap);
	return wrap;
}

export function column_break(el) {
	clearEl(el);
	const wrap = document.createElement("div");
	wrap.className = "synapse-column-break";
	el.appendChild(wrap);
	return wrap;
}

export function spacer(el, config) {
	clearEl(el);
	const wrap = document.createElement("div");
	wrap.className = "synapse-spacer";
	const h = config && Number(config.height) ? Number(config.height) : 24;
	wrap.style.height = h + "px";
	el.appendChild(wrap);
	return wrap;
}
