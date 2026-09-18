# Privacy Policy

Last updated: 18 September 2026

Synapse is an open source app you install on your own Frappe or ERPNext site. It
runs entirely on that site. Dxbitz does not host it, does not receive a copy of
your data, and Synapse does not send anything to Dxbitz or any other outside
service on its own.

This policy explains what Synapse stores on your site, and where your data can go
when you use it.

## Who controls the data

You do. Synapse runs inside your own Frappe site, under your control. The
operator of the site is the data controller. Dxbitz is the app author, not a
processor of your data, because none of it reaches us.

## What Synapse stores on your site

Synapse keeps an audit log (the Synapse Log doctype) so you can see what a
connected AI client did. One row is written for every call, whether it
succeeded, was refused, or errored. A row can hold:

- the user who made the call
- the tool that ran and the action it took
- the date and time, and how long it took
- the IP address the call came from
- how the caller signed in (OAuth, API key or session)
- the DocType and document that was touched, and row counts
- for a write, the values sent and the before and after of each changed field,
  when Log Field Values is on in Synapse Settings

Fields of type Password are always masked in the log. If you do not want values
copied into the log at all, turn off Log Field Values in Synapse Settings. The
row still records who did what and when, without the data itself.

The log stays in your site's own database. A daily job deletes rows older than
the retention window you set in Synapse Settings, which is 90 days by default.

## What Synapse does not do

- It does not send your data to Dxbitz.
- It does not phone home, and it has no analytics or telemetry.
- It has no external dependencies and makes no outbound calls of its own.

## Where your data can go

Synapse is a bridge. When you connect an AI client, for example Claude or any
other MCP client, that client reads and writes your site's data through Synapse,
as the user you signed in as, and within that user's permissions. The data the
client reads then leaves your site to that client and its provider. What they do
with it is covered by their own terms and privacy policy, not this one. Choose
your client accordingly, and scope the connecting user to only what the agent
should see.

OAuth tokens are issued and stored by Frappe itself, not by Synapse.

## Your controls

- Access is off by default. Nothing is reachable until you create a Synapse
  Profile and turn the switches on.
- You decide which users, roles, DocTypes and actions a client can reach.
- You can turn off value logging, shorten the retention window, or switch the
  endpoint off at any time in Synapse Settings.

## Contact

Questions about the app or this policy: info@dxbitz.com, or open an issue at
https://github.com/dxbitz-technology/synapse/issues.

## Changes

If this policy changes, the updated version is committed to the app repository
with a new date at the top.
