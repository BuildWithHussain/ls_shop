# Copyright (c) 2025, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns, data = get_columns(), get_data()
	return columns, data


def get_columns():
	columns = [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 200,
		},
	]
	return columns


def get_data():
	items = set(frappe.get_all("Item", {"has_variants": True}, pluck="name"))
	style_attribute_variants = set(
		frappe.get_all("Style Attribute Variant", pluck="item_style")
	)
	unmatched_items = items - style_attribute_variants
	return [{"item_code": item} for item in unmatched_items]
