# Copyright (c) 2026, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.data import add_days, nowdate

from commera.api.analytics_dashboard import get_product_engagement


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_product_engagement(
		filters.from_date or add_days(nowdate(), -29),
		filters.to_date or nowdate(),
		limit=100,
	)
	return get_columns(), data


def get_columns():
	return [
		{
			"label": _("Item"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 200,
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 240,
		},
		{
			"label": _("Views"),
			"fieldname": "views",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("Adds"),
			"fieldname": "adds",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("Purchases"),
			"fieldname": "purchases",
			"fieldtype": "Int",
			"width": 110,
		},
		{
			"label": _("Cart-to-View %"),
			"fieldname": "cart_to_view_rate",
			"fieldtype": "Percent",
			"precision": 1,
			"width": 140,
		},
		{
			"label": _("Purchase-to-View %"),
			"fieldname": "purchase_to_view_rate",
			"fieldtype": "Percent",
			"precision": 1,
			"width": 160,
		},
	]
