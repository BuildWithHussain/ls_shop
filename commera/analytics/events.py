import json
import re
from urllib.parse import unquote

import frappe
from frappe.utils.data import cint, cstr, flt

SESSION_COOKIE = "ls_sid"
UTM_COOKIE = "ls_utm"
MAX_SNAPSHOT_ITEMS = 100


def is_first_party_enabled():
	return cint(frappe.get_cached_value("Analytics Settings", "Analytics Settings", "enable_first_party"))


def get_request_cookie(name):
	request = getattr(frappe.local, "request", None)
	if request is None:
		return None
	return request.cookies.get(name)


def get_user_agent():
	# frappe.get_request_header dereferences the unbound request proxy outside HTTP contexts
	request = getattr(frappe.local, "request", None)
	if request is None:
		return None
	return request.headers.get("User-Agent")


def get_utm_values():
	raw_value = get_request_cookie(UTM_COOKIE)
	if not raw_value:
		return {}
	try:
		values = json.loads(unquote(raw_value))
	except ValueError:
		return {}
	return values if isinstance(values, dict) else {}


def clip(value, length):
	if value is None:
		return None
	return cstr(value)[:length] or None


def get_device(user_agent):
	if not user_agent:
		return ""
	# tablet UAs rarely carry "Mobi", so check them first
	if re.search(r"iPad|Tablet", user_agent, re.IGNORECASE):
		return "Tablet"
	if re.search(r"Mobi", user_agent, re.IGNORECASE):
		return "Mobile"
	return "Desktop"


def get_visitor_user():
	if frappe.session.user == "Guest":
		return None
	return frappe.session.user


def get_items_snapshot(items):
	try:
		items = frappe.parse_json(items) if items else None
	except ValueError:
		return None
	if not isinstance(items, list):
		return None
	snapshot = [
		{
			"item_code": clip(row.get("item_code"), 140),
			"qty": cint(row.get("qty")),
			"price": flt(row.get("price")),
		}
		for row in items[:MAX_SNAPSHOT_ITEMS]
		if isinstance(row, dict)
	]
	return json.dumps(snapshot) if snapshot else None


def set_attribution_fields(doc):
	# Analytics must never block checkout — swallow and log everything.
	try:
		if not is_first_party_enabled():
			return
		utm_values = get_utm_values()
		values = {
			"custom_analytics_session_id": clip(get_request_cookie(SESSION_COOKIE), 64),
			"custom_utm_source": clip(utm_values.get("source"), 140),
			"custom_utm_medium": clip(utm_values.get("medium"), 140),
			"custom_utm_campaign": clip(utm_values.get("campaign"), 140),
		}
		for fieldname, value in values.items():
			# server-to-server gateway confirms carry no shopper cookies; keep values mapped from the Quotation
			if value:
				doc.set(fieldname, value)
	except Exception:
		frappe.log_error(title="Analytics attribution stamping failed")


def log_purchase(sales_order):
	# Analytics must never block an order — swallow and log everything.
	try:
		if not is_first_party_enabled():
			return
		utm_values = get_utm_values()
		items = [
			{"item_code": row.item_code, "qty": cint(row.qty), "price": flt(row.rate)}
			for row in sales_order.get("items") or []
		]
		frappe.get_doc(
			{
				"doctype": "Storefront Analytics Event",
				"event": "purchase",
				# the SO carries checkout-time attribution; cookies are absent on server-to-server confirms
				"session_id": clip(
					sales_order.get("custom_analytics_session_id") or get_request_cookie(SESSION_COOKIE), 64
				),
				"visitor_user": get_visitor_user(),
				"device": get_device(get_user_agent()),
				"order_id": sales_order.name,
				"value": flt(sales_order.grand_total),
				"currency": clip(sales_order.currency, 8),
				"items_json": json.dumps(items),
				"utm_source": clip(sales_order.get("custom_utm_source") or utm_values.get("source"), 140),
				"utm_medium": clip(sales_order.get("custom_utm_medium") or utm_values.get("medium"), 140),
				"utm_campaign": clip(
					sales_order.get("custom_utm_campaign") or utm_values.get("campaign"), 140
				),
				"utm_term": clip(utm_values.get("term"), 140),
				"utm_content": clip(utm_values.get("content"), 140),
			}
		).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="Purchase analytics logging failed")
