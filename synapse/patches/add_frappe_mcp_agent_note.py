# Copyright (c) 2026, Dxbitz and contributors
"""Tell agents on Frappe's own MCP server where the Synapse dashboard guide is. Runs once."""

from synapse.frappe_mcp import add_agent_note


def execute():
	add_agent_note()
