# Copyright (c) 2025, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count


def execute(filters=None):
	columns, data = get_columns(), get_data()
	return columns, data


def get_columns():
	columns = [
		{
			"label": _("Style Attribute Variant"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Style Attribute Variant",
			"width": 200,
		},
		{
			"label": _("Display Name"),
			"fieldname": "display_name",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Colour"),
			"fieldname": "attribute_value",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Item Style"),
			"fieldname": "item_style",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{
			"label": _("Published"),
			"fieldname": "is_published",
			"fieldtype": "Check",
			"width": 200,
		},
		{
			"label": _("Has Images"),
			"fieldname": "has_images",
			"fieldtype": "Check",
			"width": 200,
		},
	]
	return columns


def get_data():
	style_attribute_variant = DocType("Style Attribute Variant")
	website_slideshow_item = DocType("Website Slideshow Item")

	query = (
		frappe.qb.from_(style_attribute_variant)
		.left_join(website_slideshow_item)
		.on(website_slideshow_item.parent == style_attribute_variant.name)
		.groupby(style_attribute_variant.name)
		.having(
			(style_attribute_variant.is_published == 0)
			| (Count(website_slideshow_item.image) == 0)
		)
		.select(
			style_attribute_variant.name,
			style_attribute_variant.display_name,
			style_attribute_variant.attribute_value,
			style_attribute_variant.item_style,
			style_attribute_variant.is_published,
			(Count(website_slideshow_item.image) > 0).as_("has_images"),
		)
	)

	data = query.run(as_dict=True)
	return data
