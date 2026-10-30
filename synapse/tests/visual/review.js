import { runEdgeChecks } from "./edge_cases.js";
import { samples, modules } from "./samples.js";
import { render, known_types } from "../../public/js/library/registry.js";
import { clearEl } from "../../public/js/library/theme.js";
import { renderPage } from "../../public/js/library/grid.js";
const params = new URLSearchParams(location.search),
	view = params.get("view") || "charts-1";
if (params.get("theme") === "dark") document.body.dataset.theme = "dark";
document.querySelector("#theme").textContent = params.get("theme") === "dark" ? "Light mode" : "Dark mode";
const nav = document.querySelector("#nav");
for (const [id, label] of [
	["charts-1", "Charts 1"],
	["charts-2", "Charts 2"],
	["widgets", "Widgets"],
	["edges", "Edge cases"],
	...Object.entries(modules).map(([k, v]) => [k, v.title]),
]) {
	const a = document.createElement("a");
	a.href = `?view=${id}&theme=${params.get("theme") || "light"}${
		params.get("source") === "local" ? "&source=local" : ""
	}`;
	a.textContent = label;
	if (id === view) a.className = "active";
	nav.append(a);
}
document.querySelector("#source").hidden = !modules[view];
document.querySelector("#source").textContent =
	params.get("source") === "local" ? "Use sample data" : "Use local snapshot";
document.querySelector("#source").onclick = () => {
	params.set("source", params.get("source") === "local" ? "sample" : "local");
	location.search = params.toString();
};
let currentModel = null;
const checks = [];
window.addEventListener("error", (e) => checks.push({ name: `Browser error: ${e.message}`, passed: false }));
window.addEventListener("unhandledrejection", (e) =>
	checks.push({ name: `Unhandled: ${e.reason}`, passed: false })
);
function check(name, value) {
	checks.push({ name, passed: Boolean(value) });
}
async function draw() {
	const content = document.querySelector("#content");
	clearEl(content);
	if (view === "edges") {
		content.className = "gallery";
		checks.push(...runEdgeChecks(content));
	} else if (modules[view]) {
		const model = structuredClone(modules[view]);
		document.querySelector("#title").textContent = model.title;
		document.querySelector("#subtitle").textContent = `${model.subtitle} · Sample data`;
		if (params.get("source") === "local") {
			const local = await fetch("./local-dashboards.json").then((r) => r.json());
			Object.assign(model, local[view]);
			document.querySelector("#subtitle").textContent = model.subtitle;
		}
		currentModel = model;
		renderPage(content, model);
	} else {
		content.className = "gallery";
		let entries =
			view === "charts-1"
				? samples.slice(0, 6)
				: view === "charts-2"
				? samples.slice(6, 11)
				: samples.slice(11);
		for (const [type, config, data] of entries) {
			const outer = document.createElement("section");
			outer.className = `sample ${view === "widgets" ? "widgets" : ""}`;
			outer.dataset.type = type;
			const label = document.createElement("h2");
			label.textContent = type.replaceAll("_", " ").toUpperCase();
			const host = document.createElement("div");
			outer.append(label, host);
			content.append(outer);
			render(host, type, { ...config, animate: false }, data);
		}
	}
	await new Promise((r) => setTimeout(r, 1200));
	check(
		"all renderer keys have a visual sample",
		known_types().every((type) => samples.some((s) => s[0] === type))
	);
	check(
		"no failed or unavailable components",
		view === "edges" || !content.querySelector(".synapse-placeholder")
	);
	check("page fits viewport", document.documentElement.scrollWidth <= innerWidth + 1);
	for (const node of content.querySelectorAll(".synapse-chart-host svg"))
		check("chart contains drawn marks", !!node.querySelector("path,rect,circle"));
	check(
		"no invalid SVG coordinates",
		![...content.querySelectorAll("svg *")].some((node) =>
			[...node.attributes].some((a) => /NaN|Infinity/.test(a.value))
		)
	);
	document.querySelector("#results").textContent = JSON.stringify(checks);
	document.documentElement.dataset.complete = "true";
	window.visualReview = { checks, model: currentModel };
}
document.querySelector("#theme").onclick = () => {
	params.set("theme", document.body.dataset.theme === "dark" ? "light" : "dark");
	location.search = params.toString();
};
document.querySelector("#refresh").onclick = () => {
	checks.length = 0;
	delete document.documentElement.dataset.complete;
	draw();
};
await draw();
