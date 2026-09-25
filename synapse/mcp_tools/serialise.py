# Copyright (c) 2026, Dxbitz and contributors
"""Value conversion between the database and MCP clients."""

import datetime
import decimal
import re
from dataclasses import dataclass

__all__ = ["DMY", "ISO", "Formats", "to_client", "to_db_date"]


@dataclass(frozen=True)
class Formats:
	"""strftime patterns for one output style."""

	date: str
	datetime: str


ISO = Formats(date="%Y-%m-%d", datetime="%Y-%m-%d %H:%M:%S")
DMY = Formats(date="%d-%m-%Y", datetime="%d-%m-%Y %H:%M:%S")

_DMY_RE = re.compile(
	r"^(?P<d>\d{2})-(?P<m>\d{2})-(?P<y>\d{4})"
	r"(?:[ T](?P<time>\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?))?$"
)


def to_client(value, formats: Formats = ISO):
	"""Convert one database value, or a structure of them, to something JSON can carry."""

	if isinstance(value, datetime.datetime):
		return value.strftime(formats.datetime)

	if isinstance(value, datetime.date):
		return value.strftime(formats.date)

	if isinstance(value, datetime.timedelta):
		total = int(value.total_seconds())
		return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"

	if isinstance(value, decimal.Decimal):
		return float(value)

	if isinstance(value, (bytes, bytearray)):
		return value.decode("utf-8", "replace")

	if isinstance(value, dict):
		return {k: to_client(v, formats) for k, v in value.items()}

	if isinstance(value, (list, tuple)):
		return [to_client(v, formats) for v in value]

	if isinstance(value, (str, int, float, bool)) or value is None:
		return value

	return str(value)


def to_db_date(value):
	"""Turn DD-MM-YYYY (with optional time) into ISO. Anything else is returned as is.

	Only ever called on values bound for a Date, Datetime or Time field, so a
	string that merely looks like a date elsewhere in the document is untouched.
	"""

	if not isinstance(value, str):
		return value

	match = _DMY_RE.match(value.strip())
	if not match:
		return value

	iso = f"{match['y']}-{match['m']}-{match['d']}"
	return f"{iso} {match['time']}" if match["time"] else iso
