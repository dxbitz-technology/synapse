export const axis = {
	labels: ["May", "Jun", "Jul", "Aug", "Sep", "Oct"],
	series: [
		{ name: "Revenue", values: [84, 96, 89, 122, 135, 148] },
		{ name: "Cost", values: [62, 68, 70, 81, 87, 92] },
	],
	axes: { x: "Month", y: "AED thousands" },
};
export const parts = { labels: ["Services", "Equipment", "Maintenance", "Other"], values: [48, 28, 18, 6] };
const activity = {};
for (let i = 0; i < 90; i++)
	activity[String(Date.UTC(2026, 7, 1 + i) / 1000)] = i % 7 === 0 ? 0 : (i * 7) % 15;
export const samples = [
	["bar_chart", { title: "Revenue and cost · AED thousands" }, axis],
	["line_chart", { title: "Monthly performance" }, axis],
	["area_chart", { title: "Revenue trend" }, { labels: axis.labels, series: [axis.series[0]] }],
	[
		"mixed_chart",
		{ title: "Billed and collected · AED thousands" },
		{ ...axis, series: axis.series.map((s, i) => ({ ...s, chartType: i ? "line" : "bar" })) },
	],
	["pie_chart", { title: "Revenue by business line" }, parts],
	["donut_chart", { title: "Revenue mix" }, parts],
	[
		"percentage_chart",
		{ title: "Order fulfilment" },
		{ labels: ["Delivered", "In progress", "Pending"], values: [68, 24, 8] },
	],
	[
		"heatmap",
		{ title: "Daily service activity", count_label: "jobs" },
		{ dataPoints: activity, start: "2026-08-01", end: "2026-10-29" },
	],
	[
		"scatter_chart",
		{ title: "Order size vs delivery time" },
		{
			labels: [2, 4, 6, 8, 10, 12],
			series: [
				{ name: "Standard", values: [12, 22, 18, 39, 43, 55] },
				{ name: "Express", values: [8, 16, 19, 26, 33, 41] },
			],
			axes: { x: "Delivery days", y: "Order value · AED thousands" },
		},
	],
	[
		"bar_horizontal",
		{ title: "Top product categories" },
		{
			labels: [
				"Maintenance services",
				"Air conditioning equipment",
				"Industrial pumps",
				"Spare parts",
				"Installation",
			],
			series: [
				{ name: "Revenue", values: [148, 112, 86, 64, 48] },
				{ name: "Cost", values: [92, 79, 58, 42, 28] },
			],
		},
	],
	[
		"map",
		{ title: "Service locations" },
		{
			points: [
				{ label: "Dubai", latitude: 25.2, longitude: 55.27, value: 148 },
				{ label: "Abu Dhabi", latitude: 24.45, longitude: 54.38, value: 92 },
				{ label: "Riyadh", latitude: 24.71, longitude: 46.67, value: 63 },
				{ label: "Muscat", latitude: 23.59, longitude: 58.41, value: 38 },
			],
		},
	],
	[
		"number_card",
		{ title: "Revenue", value_type: "currency", currency: "AED", precision: 0 },
		{ value: 1482500, delta: 12.8, trend: "up" },
	],
	[
		"table",
		{ title: "Open orders", currency: "AED" },
		{
			columns: [
				{ key: "name", label: "Order", type: "text" },
				{ key: "customer", label: "Customer", type: "text" },
				{ key: "date", label: "Delivery", type: "date" },
				{ key: "amount", label: "Outstanding", type: "currency" },
			],
			rows: [
				{
					name: "SO-2026-0148",
					customer: "Gulf Facilities Management LLC",
					date: "2026-10-24",
					amount: 48500,
				},
				{ name: "SO-2026-0149", customer: "Al Noor Technical Services", date: "2026-10-26", amount: 18250 },
				{ name: "SO-2026-0150", customer: "Coastal Industrial Supplies", date: "2026-10-28", amount: 96000 },
			],
		},
	],
	[
		"list",
		{ title: "Top customers", value_type: "currency", currency: "AED", precision: 0 },
		{
			items: [
				{ label: "Gulf Facilities Management LLC", value: 148000, bar: 1 },
				{ label: "Al Noor Technical Services", value: 112000, bar: 0.76 },
				{ label: "Coastal Industrial Supplies", value: 86000, bar: 0.58 },
			],
		},
	],
	[
		"progress",
		{ title: "Collection target", value_type: "currency", currency: "AED" },
		{ value: 382000, target: 500000, label: "October" },
	],
	[
		"pivot",
		{ title: "Sales by region · AED", currency: "AED", row_totals: true },
		{
			rowLabels: ["Dubai", "Abu Dhabi", "Sharjah"],
			colLabels: ["Services", "Equipment", "Parts"],
			cells: [
				[48000, 82000, 21000],
				[36000, 64000, 18000],
				[24000, 42000, 12000],
			],
			measureType: "number",
			corner: "Region",
		},
	],
	[
		"callout",
		{},
		{
			level: "warning",
			title: "Collections need attention",
			body: "8 invoices are more than 30 days overdue. Outstanding: AED 84,250.",
		},
	],
	[
		"text_block",
		{},
		{
			markdown:
				"### October performance\nRevenue is up **12.8%** on last month. Services account for the largest share.\n\n- Review overdue invoices\n- Confirm next week’s deliveries",
		},
	],
	["section_break", { title: "Operational detail" }, {}],
	["column_break", {}, {}],
	["spacer", { height: 24 }, {}],
];
export function block(type, columns = 6, title) {
	const sample = samples.find((s) => s[0] === type);
	return {
		component_type: type,
		columns,
		config: { ...sample[1], ...(title ? { title } : {}) },
		frozen_data: structuredClone(sample[2]),
	};
}
export const modules = {
	sales: {
		title: "Sales",
		subtitle: "Orders, revenue and collections",
		blocks: [
			{ ...block("number_card", 4, "Revenue · October"), frozen_data: { value: 1482500, delta: 12.8 } },
			{
				...block("number_card", 4, "Open orders"),
				config: { title: "Open orders", value_type: "int" },
				frozen_data: { value: 42, delta: 6 },
			},
			{
				...block("number_card", 4, "Outstanding"),
				frozen_data: { value: 284250, delta: -8.2, trend: "down" },
			},
			block("mixed_chart", 8, "Revenue and collections · AED thousands"),
			block("donut_chart", 4, "Revenue mix"),
			block("bar_horizontal", 6, "Top categories · AED thousands"),
			block("table", 6),
		],
	},
	buying: {
		title: "Buying",
		subtitle: "Spend, supplier mix and purchasing",
		blocks: [
			{ ...block("number_card", 4, "Purchases · October"), frozen_data: { value: 742800, delta: 4.2 } },
			{
				...block("number_card", 4, "Open purchase orders"),
				config: { title: "Open purchase orders", value_type: "int" },
				frozen_data: { value: 28 },
			},
			{ ...block("number_card", 4, "Unpaid supplier invoices"), frozen_data: { value: 168500, delta: -6.4 } },
			block("bar_chart", 8, "Purchases and payments · AED thousands"),
			block("pie_chart", 4, "Spend by category"),
			block("progress", 6, "Monthly purchasing budget"),
			block("list", 6, "Top suppliers"),
		],
	},
	stock: {
		title: "Stock",
		subtitle: "Stock value, availability and movement",
		blocks: [
			{ ...block("number_card", 4, "Stock value"), frozen_data: { value: 2845000, delta: 3.6 } },
			{
				...block("number_card", 4, "Active items"),
				config: { title: "Active items", value_type: "int" },
				frozen_data: { value: 1284 },
			},
			{
				...block("number_card", 4, "Items below reorder level"),
				config: { title: "Items below reorder level", value_type: "int" },
				frozen_data: { value: 18 },
			},
			block("area_chart", 8, "Stock value · AED thousands"),
			block("percentage_chart", 4, "Stock availability"),
			block("pivot", 6, "Warehouse stock · AED"),
			block("heatmap", 6, "Daily stock movements"),
		],
	},
	projects: {
		title: "Projects",
		subtitle: "Delivery progress, workload and activity",
		blocks: [
			{
				...block("number_card", 4, "Active projects"),
				config: { title: "Active projects", value_type: "int" },
				frozen_data: { value: 24 },
			},
			{
				...block("number_card", 4, "Open tasks"),
				config: { title: "Open tasks", value_type: "int" },
				frozen_data: { value: 148, delta: -12.5 },
			},
			{
				...block("number_card", 4, "Completed this month"),
				config: { title: "Completed this month", value_type: "int" },
				frozen_data: { value: 86, delta: 18.6 },
			},
			block("line_chart", 8, "Tasks opened and closed"),
			block("progress", 4, "Project completion"),
			block("scatter_chart", 6, "Delivery time vs project value"),
			block("map", 6, "Project locations"),
		],
	},
};

// Keep the module examples internally consistent rather than reusing chart labels.
modules.sales.blocks[3].frozen_data.series[0].name = "Billed";
modules.sales.blocks[3].frozen_data.series[1].name = "Collected";
modules.buying.blocks[3].frozen_data.series[0].name = "Purchases";
modules.buying.blocks[3].frozen_data.series[1].name = "Payments";
modules.buying.blocks[5].frozen_data = { value: 742800, target: 900000, label: "October" };
modules.stock.blocks[3].frozen_data = {
	labels: axis.labels,
	series: [{ name: "Stock value", values: [2300, 2420, 2370, 2600, 2740, 2845] }],
};
modules.stock.blocks[4].frozen_data = {
	labels: ["Available", "Low stock", "Out of stock"],
	values: [1266, 12, 6],
};
modules.projects.blocks[3].frozen_data = {
	labels: axis.labels,
	series: [
		{ name: "Opened", values: [68, 74, 81, 92, 88, 96] },
		{ name: "Closed", values: [52, 61, 64, 76, 73, 86] },
	],
};
modules.projects.blocks[4].config = { title: "Project completion", value_type: "int" };
modules.projects.blocks[4].frozen_data = { value: 132, target: 180, label: "Tasks completed" };

modules.sales.blocks[3].frozen_data.series[0].values = [840, 960, 890, 1220, 1350, 1482.5];
modules.sales.blocks[3].frozen_data.series[1].values = [620, 680, 700, 810, 870, 920];
modules.buying.blocks[3].frozen_data.series[0].values = [486, 540, 518, 620, 688, 742.8];
modules.buying.blocks[3].frozen_data.series[1].values = [440, 490, 470, 570, 612, 680];
modules.stock.blocks[5].frozen_data = {
	rowLabels: ["Dubai", "Abu Dhabi", "Sharjah"],
	colLabels: ["Equipment", "Consumables", "Spare parts"],
	cells: [
		[480000, 210000, 150000],
		[560000, 190000, 140000],
		[620000, 260000, 235000],
	],
	measureType: "number",
	corner: "Warehouse",
};
modules.projects.blocks[5].frozen_data.axes.y = "Project value · AED thousands";
