app_name = "synapse"
app_title = "Synapse"
app_publisher = "Dxbitz"
app_description = "Dashboards for Frappe and ERPNext, built through Frappe's MCP server"
app_email = "info@dxbitz.com"
app_license = "agpl-3.0"

app_include_js = ["synapse.bundle.js"]
app_include_css = ["/assets/synapse/css/synapse_library.css"]

after_install = ["synapse.components.catalog.seed", "synapse.frappe_mcp.add_agent_note"]
after_migrate = "synapse.components.catalog.seed"


add_to_apps_screen = [
	{
		"name": "synapse",
		"logo": "/assets/synapse/images/synapse-mark.svg",
		"title": "Synapse",
		"route": "/synapse",
		"has_permission": "synapse.api.has_desk_permission",
	},
]

website_route_rules = [
	{"from_route": "/synapse/<path:app_path>", "to_route": "synapse"},
]

doctype_js = {
	"User": "public/js/synapse_user.js",
}

scheduler_events = {
	"daily": [
		"synapse.synapse.doctype.synapse_log.synapse_log.delete_old_logs",
	],
}

# OAuth discovery for MCP clients on Frappe v15. v16 serves these itself (OAuth
# Settings), so the routes are only added on v15 and never shadow Frappe's own.
# The (/.*)? suffix also catches the path-suffixed forms some clients try first,
# e.g. /.well-known/oauth-protected-resource/api/method/synapse.mcp.handle_mcp.
from synapse.compat import native_oauth_discovery as _native_oauth_discovery

if not _native_oauth_discovery():
	website_redirects = [
		{
			"source": r"/.well-known/oauth-authorization-server(/.*)?",
			"target": "/api/method/synapse.oauth_compat.authorization_server_metadata",
			"redirect_http_status": 307,
		},
		{
			"source": r"/.well-known/oauth-protected-resource(/.*)?",
			"target": "/api/method/synapse.oauth_compat.protected_resource_metadata",
			"redirect_http_status": 307,
		},
	]
