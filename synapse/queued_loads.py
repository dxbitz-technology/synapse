# Copyright (c) 2026, Dxbitz and contributors
"""Script dashboards load in a background job, not in the web request.

The browser asks for data. If this user loaded the same page with the same filters
in the last few minutes, the stored result comes back at once. Otherwise one job is
queued and the browser shows a loader and checks back until the job is done. The
result is stored per user, since a script can show each user different data.

A changed page or script gives a new ticket, so an edit never serves old data.
"""

import hashlib
import json
import re
import time

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from synapse import dashboards as dash

FRESH = 300  # seconds a stored result is served without running again
LOST = 600  # a job queued longer than this is taken as lost and queued again
FAILED_FOR = 60  # a failure is shown again for this long instead of rerunning
KEEP = 86400  # seconds a result is kept at all


def queue_on() -> bool:
	return bool(cint(frappe.conf.get("synapse_script_queue", 1))) and not frappe.flags.in_test


def ticket_for(doc, values) -> str:
	script_modified = frappe.db.get_value("Synapse Script", doc.data_script, "modified")
	raw = json.dumps([doc.name, str(doc.modified), str(script_modified), values], sort_keys=True, default=str)
	return hashlib.sha1(raw.encode()).hexdigest()[:20]


def _key(ticket, user=None) -> str:
	return f"synapse:load:{user or frappe.session.user}:{ticket}"


def _reply(entry, ticket) -> dict:
	out = {"status": entry.get("status"), "ticket": ticket}
	if entry.get("data") is not None:
		out["data"] = entry["data"]
	if entry.get("updated_at"):
		out["updated_at"] = entry["updated_at"]
	if entry.get("error"):
		out["error"] = entry["error"]
	return out


def plain(error) -> str:
	"""The message without Frappe's exception class prefix."""
	text = str(error) or error.__class__.__name__
	return re.sub(r"^[A-Z]\w+: ", "", text)


def request(doc, filters=None, refresh=False) -> dict:
	"""Stored data, or a queued job and a ticket to check on."""
	values = dash.clean_filters(dash.layout_of(doc), filters)
	ticket = ticket_for(doc, values)
	key = _key(ticket)
	cache = frappe.cache
	entry = cache.get_value(key) or {}
	now = time.time()
	fresh = cint(frappe.conf.get("synapse_script_fresh_seconds")) or FRESH
	status = entry.get("status")

	if status == "ready" and not refresh and now - entry["at"] < fresh:
		return _reply(entry, ticket)
	if status == "queued" and now - entry["queued_at"] < LOST:
		return _reply(entry, ticket)
	if status == "failed" and not refresh and now - entry["at"] < FAILED_FOR:
		return _reply(entry, ticket)

	stopped = cache.get_value(dash.stopped_key(doc, values))
	if stopped:
		entry = {
			"status": "failed",
			"at": now,
			"error": _("{0} It will not run again for a few minutes.").format(stopped),
		}
		return _reply(entry, ticket)

	if not queue_on():
		run(frappe.session.user, doc.name, values, ticket, queued=False)
		return _reply(cache.get_value(key) or {}, ticket)

	# Older data stays visible while the new run is in the queue.
	entry = {
		"status": "queued",
		"queued_at": now,
		"data": entry.get("data"),
		"at": entry.get("at"),
		"updated_at": entry.get("updated_at"),
	}
	cache.set_value(key, entry, expires_in_sec=KEEP)
	frappe.enqueue(
		"synapse.queued_loads.run",
		queue="default",
		timeout=300,
		job_id=f"synapse-load-{frappe.session.user}-{ticket}",
		deduplicate=True,
		user=frappe.session.user,
		page=doc.name,
		values=values,
		ticket=ticket,
	)
	return _reply(entry, ticket)


def status(doc, ticket) -> dict:
	if not re.fullmatch(r"[0-9a-f]{20}", ticket or ""):
		frappe.throw(_("Unknown ticket."))
	entry = frappe.cache.get_value(_key(ticket))
	if not entry:
		return {"status": "lost", "ticket": ticket}
	if entry.get("status") == "queued" and time.time() - entry["queued_at"] >= LOST:
		return {"status": "lost", "ticket": ticket}
	return _reply(entry, ticket)


def run(user, page, values, ticket, queued=True):
	"""The job: run the script as the user who asked, and store what came back."""
	from synapse.scripts import new_budget

	if queued:
		frappe.set_user(user)
	key = _key(ticket, user)
	try:
		doc = dash.readable_page(page)
		frappe.local.synapse_budget = new_budget(queued=queued)
		try:
			data = dash.data_for(doc, values, queued=queued)
		finally:
			frappe.local.synapse_budget = None
		entry = {"status": "ready", "at": time.time(), "updated_at": str(now_datetime())[:19], "data": data}
	except Exception as error:
		# A stopped run is also remembered by the guard, so it is not rerun for a while.
		entry = {"status": "failed", "at": time.time(), "error": plain(error)}
		if not queued and not isinstance(error, frappe.ValidationError):
			raise
	frappe.cache.set_value(key, entry, expires_in_sec=KEEP)
