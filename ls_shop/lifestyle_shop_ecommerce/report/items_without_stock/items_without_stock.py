# Copyright (c) 2025, company@bwhstudios.com and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count
from pypika.functions import Sum
from pypika.terms import Case


def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
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
			"label": _("Published but No Stock"),
			"fieldname": "published_but_no_stock",
			"fieldtype": "Check",
			"width": 180,
		},
		{
			"label": _("Unpublished but Has Stock"),
			"fieldname": "unpublished_but_has_stock",
			"fieldtype": "Check",
			"width": 200,
		},
		{
			"label": _("Images"),
			"fieldname": "images",
			"fieldtype": "Check",
			"width": 200,
		},
		{
			"label": _("Published"),
			"fieldname": "is_published",
			"fieldtype": "Check",
			"width": 200,
		},
		{
			"label": _("Available Qty"),
			"fieldname": "available_qty",
			"fieldtype": "Float",
			"width": 120,
		},
	]
	return columns


def get_data(filters=None):
	ecommerce_warehouse = frappe.get_cached_value(
		"Lifestyle Settings", "Lifestyle Settings", "ecommerce_warehouse"
	)

	style_attribute_variant = DocType("Style Attribute Variant")
	color_size_item = DocType("Color Size Item")
	bin = DocType("Bin")
	website_slideshow_item = DocType("Website Slideshow Item")
	available_qty_expr = Sum(bin.actual_qty - bin.reserved_qty)

	# CASE expressions to compute the checkboxes
	published_no_stock = (
		Case()
		.when(
			(style_attribute_variant.is_published == 1)
			& ((available_qty_expr < 1) | (available_qty_expr.isnull())),
			1,
		)
		.else_(0)
		.as_("published_but_no_stock")
	)

	unpublished_has_stock = (
		Case()
		.when((style_attribute_variant.is_published == 0) & (available_qty_expr > 0), 1)
		.else_(0)
		.as_("unpublished_but_has_stock")
	)

	query = (
		frappe.qb.from_(style_attribute_variant)
		.left_join(color_size_item)
		.on(style_attribute_variant.name == color_size_item.parent)
		.left_join(website_slideshow_item)
		.on(website_slideshow_item.parent == style_attribute_variant.name)
		.left_join(bin)
		.on(
			(color_size_item.item_code == bin.item_code)
			& (bin.warehouse == ecommerce_warehouse)
		)
		.select(
			style_attribute_variant.name,
			style_attribute_variant.display_name,
			style_attribute_variant.attribute_value,
			style_attribute_variant.item_style,
			published_no_stock,
			unpublished_has_stock,
			(Count(website_slideshow_item.image) > 0).as_("images"),
			style_attribute_variant.is_published,
			available_qty_expr.as_("available_qty"),
		)
		.groupby(style_attribute_variant.name)
	)
	if filters:
		if filters.published_but_no_stock and not filters.unpublished_but_has_stock:
			query = query.having(published_no_stock == 1)
		elif filters.unpublished_but_has_stock and not filters.published_but_no_stock:
			query = query.having(unpublished_has_stock == 1)
		else:
			query = query.having(
				(published_no_stock == 1) | (unpublished_has_stock == 1)
			)
	else:
		query = query.having((published_no_stock == 1) | (unpublished_has_stock == 1))

	return query.run(as_dict=True)


@frappe.whitelist()
def bulk_unpublish(filters):
	filters = frappe.parse_json(filters) if filters else {}
	data = get_data(filters)

	style_attribute_variants = [d.name for d in data]

	frappe.db.set_value(
		"Style Attribute Variant",
		{"name": ["in", style_attribute_variants]},
		{"is_published": 0},
	)


@frappe.whitelist()
def bulk_publish(filters):
	filters = frappe.parse_json(filters) if filters else {}

	data = get_data(filters)

	style_attribute_variants = [d.name for d in data]
	doc = frappe.get_single("Bulk Publish Variants")
	return doc.bulk_toggle_publish(
		publish=True, style_attribute_variant_list=style_attribute_variants
	)
