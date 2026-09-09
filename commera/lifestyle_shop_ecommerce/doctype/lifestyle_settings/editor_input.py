# Copyright (c) 2026, company@bwhstudios.com and contributors
# For license information, please see license.txt

"""Trust-boundary helpers shared by the navbar and footer editors."""

import frappe
from frappe.utils import validate_url

# Anything outside these — javascript:, data:, vbscript: — is a script-injection vector once rendered.
SAFE_URL_SCHEMES = ("", "http", "https")


def parse_list(value):
	if isinstance(value, str):
		# frappe.parse_json lets orjson's error through, so malformed input would 500 instead of throwing.
		try:
			value = frappe.parse_json(value)
		except Exception:
			frappe.throw(frappe._("Expected a list, got: {0}").format(value))
	if value is None:
		return []
	return value if isinstance(value, list) else [value]


def require_value(value, message):
	value = (value or "").strip()
	if not value:
		frappe.throw(message)
	return value


def require_safe_url(value, message):
	value = require_value(value, message)
	if not validate_url(value, valid_schemes=SAFE_URL_SCHEMES):
		frappe.throw(frappe._("Link URL {0} uses a scheme that is not allowed.").format(value))
	return value
