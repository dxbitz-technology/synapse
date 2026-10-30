import { render } from "../../public/js/library/registry.js";
import { renderPage } from "../../public/js/library/grid.js";
import { clearEl, formatValue } from "../../public/js/library/theme.js";
export function runEdgeChecks(container) {
	const checks = [];
	const check = (name, passed) => checks.push({ name, passed: Boolean(passed) });
	check("percentages have bounded precision", formatValue(51.9679069767442, "percent") === "51.97%");
	function fixture(title, type, config, data) {
		const section = document.createElement("section");
		section.className = "sample";
		const h = document.createElement("h2");
		h.textContent = title;
		const host = document.createElement("div");
		section.append(h, host);
		container.append(section);
		render(host, type, config, data);
		return host;
	}
	const empty = fixture("Empty data", "donut_chart", { title: "No orders yet" }, { labels: [], values: [] });
	check("empty pie has a useful empty state", !!empty.querySelector(".synapse-empty"));
	const zeros = fixture(
		"Zero values",
		"percentage_chart",
		{ title: "No allocation" },
		{ labels: ["A", "B"], values: [0, 0] }
	);
	check("zero total is not drawn as a misleading share", !!zeros.querySelector(".synapse-empty"));
	const negative = fixture(
		"Negative and positive bars",
		"bar_horizontal",
		{ title: "Net movement" },
		{ labels: ["Returns", "Issues", "Receipts"], series: [{ name: "Quantity", values: [-25, 0, 50] }] }
	);
	check(
		"negative values use a signed baseline",
		negative.querySelector(".synapse-horizontal-fill").style.left === "0%"
	);
	check(
		"positive bars do not begin at negative bound",
		parseFloat(negative.querySelectorAll(".synapse-horizontal-fill")[2].style.left) > 0
	);
	const constant = fixture(
		"Single-point scatter",
		"scatter_chart",
		{ title: "One observation" },
		{ labels: [4], series: [{ name: "Jobs", values: [0] }] }
	);
	check(
		"single point has finite coordinates",
		Number.isFinite(Number(constant.querySelector("circle")?.getAttribute("cx")))
	);
	const bad = fixture(
		"Invalid series · expected rejection",
		"line_chart",
		{ title: "Invalid input" },
		{ labels: ["A", "B"], series: [{ name: "Mismatch", values: [3] }] }
	);
	check("mismatched arrays are rejected", !!bad.querySelector(".synapse-placeholder"));
	const over = fixture("Above target", "progress", { title: "Collected" }, { value: 150, target: 100 });
	check("above-target percentage stays truthful", over.textContent.includes("150%"));
	check(
		"progress fill stays within track",
		over.querySelector(".synapse-progress-fill").style.width === "100%"
	);
	const noTarget = fixture("Target not set", "progress", { title: "Goal" }, { value: 15, target: 0 });
	check("zero target is explained", noTarget.textContent.includes("No target set"));
	const delta = fixture(
		"Independent delta precision",
		"number_card",
		{ title: "Revenue", value_type: "currency", currency: "AED", precision: 0, delta_type: "percent" },
		{ value: 1234567, delta: 12.8 }
	);
	check("delta is not rounded with currency precision", delta.textContent.includes("12.8%"));
	check("delta does not repeat percent sign", !delta.textContent.includes("%%"));
	const lots = fixture(
		"Many pie categories",
		"pie_chart",
		{ title: "Share by category", max_slices: 5 },
		{
			labels: Array.from({ length: 24 }, (_, i) => `Group ${i + 1}`),
			values: Array.from({ length: 24 }, (_, i) => i + 1),
		}
	);
	check(
		"legend matches grouped pie slices",
		lots.querySelectorAll(".synapse-legend-item").length === 5 &&
			lots.textContent.includes("Other categories")
	);
	const colored = fixture(
		"Unavailable color token",
		"bar_chart",
		{ title: "Resolved color fallback", colors: ["--missing-token"] },
		{ labels: ["A", "B"], series: [{ name: "Jobs", values: [4, 9] }] }
	);
	check(
		"unresolved theme colors have a valid fallback",
		CSS.supports("color", colored.querySelector(".synapse-legend-dot").style.backgroundColor)
	);
	const long = fixture(
		"Long labels",
		"bar_horizontal",
		{ title: "Revenue by service" },
		{
			labels: ["Annual maintenance and preventive inspection services for commercial facilities"],
			series: [{ name: "Revenue", values: [123456789] }],
		}
	);
	check("long labels remain in their container", long.scrollWidth <= long.clientWidth + 1);
	const calendar = fixture(
		"One-day calendar",
		"heatmap",
		{ title: "One day" },
		{ start: "2026-10-21", end: "2026-10-21", dataPoints: { 1792540800: 3 } }
	);
	check(
		"one-day range renders one focusable day",
		calendar.querySelectorAll(".synapse-heatmap-day[tabindex]").length === 1
	);
	const invalidMap = fixture(
		"Invalid location · expected rejection",
		"map",
		{ title: "Invalid coordinates" },
		{ points: [{ label: "Outside globe", latitude: 120, longitude: 55 }] }
	);
	check("invalid map coordinates are rejected", !!invalidMap.querySelector(".synapse-placeholder"));
	const cleanup = document.createElement("div");
	container.append(cleanup);
	render(cleanup, "line_chart", {}, { labels: ["A", "B"], series: [{ name: "Count", values: [1, 2] }] });
	const chart = cleanup.querySelector(".synapse-chart-host").__synapseChart;
	let destroyed = 0;
	const original = chart.destroy.bind(chart);
	chart.destroy = () => {
		destroyed++;
		original();
	};
	renderPage(cleanup, { blocks: [] });
	check("refresh disposes existing native chart", destroyed === 1);
	clearEl(cleanup);
	cleanup.remove();
	return checks;
}
