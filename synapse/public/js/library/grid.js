// Copyright (c) 2026, Dxbitz and contributors

import { render } from "./registry.js";
import { clearEl } from "./theme.js";

const SECTION_BREAK = "section_break";
const COLUMN_BREAK = "column_break";
const SPACER = "spacer";

function asObject(value) {
	if (value && typeof value === "object") return value;
	if (typeof value === "string" && value.trim()) {
		try {
			return JSON.parse(value);
		} catch (e) {
			return {};
		}
	}
	return {};
}

function clampSpan(n) {
	const v = parseInt(n, 10);
	if (isNaN(v)) return 12;
	return Math.max(1, Math.min(v, 12));
}

export function renderPage(container, page) {
	clearEl(container);
	const root = document.createElement("div");
	root.className = "synapse-page";
	container.appendChild(root);

	const blocks = (page && page.blocks) || [];
	let grid = startSection(root, null);
	let forceNewRow = false;

	blocks.forEach((block) => {
		const type = block.component_type;

		if (type === SECTION_BREAK) {
			grid = startSection(root, asObject(block.config).title);
			forceNewRow = false;
			return;
		}
		if (type === COLUMN_BREAK) {
			forceNewRow = true;
			return;
		}
		if (type === SPACER) {
			const cell = placeCell(grid, 12, true);
			render(cellBody(cell), SPACER, asObject(block.config), {});
			forceNewRow = false;
			return;
		}

		const span = clampSpan(block.columns);
		const cell = placeCell(grid, span, forceNewRow);
		forceNewRow = false;
		render(cellBody(cell), type, asObject(block.config), asObject(block.frozen_data));
	});

	return root;
}

function startSection(root, title) {
	const section = document.createElement("div");
	section.className = "synapse-page-section";
	if (title) {
		const h = document.createElement("div");
		h.className = "synapse-section-title";
		h.textContent = title;
		section.appendChild(h);
	}
	const grid = document.createElement("div");
	grid.className = "synapse-page-grid";
	section.appendChild(grid);
	root.appendChild(section);
	return grid;
}

function placeCell(grid, span, newRow) {
	const cell = document.createElement("div");
	cell.className = "synapse-page-block";
	cell.style.setProperty("--span", span);
	cell.setAttribute("data-span", span);
	if (newRow) cell.classList.add("synapse-new-row");
	const body = document.createElement("div");
	body.className = "synapse-page-block-body";
	cell.appendChild(body);
	grid.appendChild(cell);
	return cell;
}

function cellBody(cell) {
	return cell.querySelector(".synapse-page-block-body");
}
