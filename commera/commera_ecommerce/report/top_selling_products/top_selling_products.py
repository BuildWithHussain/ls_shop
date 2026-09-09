# Copyright (c) 2026, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.data import add_days, cint, nowdate

from commera.api.analytics_dashboard import get_top_products


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_top_products(
		filters.from_date or add_days(nowdate(), -29),
		filters.to_date or nowdate(),
		sort_by="revenue",
		limit=cint(filters.limit) or 50,
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
			"label": _("Units Sold"),
			"fieldname": "units",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": _("Revenue"),
			"fieldname": "revenue",
			"fieldtype": "Currency",
			"width": 150,
		},
	]
