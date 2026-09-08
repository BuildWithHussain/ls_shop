no_cache = True

import frappe

from ls_shop.www.account.orders import detail


def get_context(context):
	detail.get_context(context)
	# Items arrive as a JSON_ARRAYAGG string; the theme jinja environment exposes no json global.
	context.order_items = frappe.parse_json(context.order.get("items")) or []
	context.invoice_name = get_invoice_name(context.order.name)
	context.print_format = (
		frappe.get_cached_value("Lifestyle Settings", "Lifestyle Settings", "print_format") or "Standard"
	)
	return context


def get_invoice_name(order_id):
	invoices = frappe.get_all("Sales Invoice", filters={"sales_order": order_id}, pluck="name", limit=1)
	return invoices[0] if invoices else None
