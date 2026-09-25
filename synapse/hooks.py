app_name = "synapse"
app_title = "Synapse"
app_publisher = "Dxbitz"
app_description = "A permission-aware MCP server for Frappe and ERPNext"
app_email = "info@dxbitz.com"
app_license = "agpl-3.0"

app_include_js = ["synapse.bundle.js"]
app_include_css = ["/assets/synapse/css/synapse_library.css"]

after_install = "synapse.components.catalog.seed"
after_migrate = "synapse.components.catalog.seed"


add_to_apps_screen = [
	{
		"name": "synapse",
		"logo": "/assets/synapse/images/synapse-mark.svg",
		"title": "Synapse",
		"route": "/app/synapse",
		"has_permission": "synapse.api.has_admin_permission",
	},
]

doctype_js = {
	"User": "public/js/synapse_user.js",
}

scheduler_events = {
	"daily": [
		"synapse.synapse.doctype.synapse_log.synapse_log.delete_old_logs",
	],
}
