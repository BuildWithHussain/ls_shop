from functools import lru_cache

import frappe
from erpnext.selling.doctype.customer.customer import (
	get_nested_links as _get_nested_links,
)
from frappe.geo.country_info import get_all
from frappe.query_builder import Case, DocType
from frappe.query_builder.functions import Count, Min, Sum
from frappe.utils import add_days, flt, get_datetime, now_datetime
from pypika import Order
from webshop.webshop.shopping_cart.cart import (
	get_address_docs,
	get_party,
)


def get_complete_nested_links(parent_group):
	"""Recursively fetch all nested item groups."""
	all_links = set()

	def recurse_node(group):
		children = get_nested_links("Item Group", group)
		for child in children:
			if child not in all_links:
				all_links.add(child)
				recurse_node(child)

	recurse_node(parent_group)
	return list(all_links)


def before_request():
	request_path = frappe.request.path

	if request_path.startswith("/en"):
		frappe.local.lang = "en"
	elif request_path.startswith("/ar"):
		frappe.local.lang = "ar"


def get_nested_links(link_doctype, link_name):
	"`get_nested_links` from erpnext, but with permissions ignored!"
	return _get_nested_links(link_doctype, link_name, ignore_permissions=True)


def get_product_list(
	filters=None, product_list=None, page=1, page_length=30, sort_by="default"
):
	"""Fetches products dynamically based on selected filters."""

	query = get_product_base_query(filters, product_list)
	style_attribute_variant = DocType("Style Attribute Variant")
	website_slideshow_item = DocType("Website Slideshow Item")
	color_size_item = DocType("Color Size Item")
	item_price_default = DocType("Item Price").as_("ip_default")
	item_price_sale = DocType("Item Price").as_("ip_sale")
	item = DocType("Item")
	has_custom_name_ar = frappe.db.has_column("Item", "custom_item_name_ar")

	# Select Fields
	discount_expr = (
		Case()
		.when(
			Min(item_price_default.price_list_rate) > 0,
			(
				(
					Min(item_price_default.price_list_rate)
					- Min(item_price_sale.price_list_rate)
				)
				/ Min(item_price_default.price_list_rate)
			)
			* 100,
		)
		.else_(0)
	)
	query = (
		query.select(
			style_attribute_variant.name,
			style_attribute_variant.route,
			style_attribute_variant.item_style,
			style_attribute_variant.display_name,
			style_attribute_variant.attribute_name.as_("attribute_value"),
			item.brand,
			item.item_name,
			color_size_item.item_code.as_("variant_item_code"),
			Min(item_price_default.price_list_rate).as_("default_price"),
			Min(item_price_sale.price_list_rate).as_("sale_price"),
			website_slideshow_item.image.as_("image"),
			discount_expr.as_("discount_percent").as_("discount_percent"),
		)
		.groupby(style_attribute_variant.name)
		.limit(page_length)
		.offset((page - 1) * page_length)
	)
	if has_custom_name_ar:
		query = query.select(item.custom_item_name_ar)
	# Sorting
	if sort_by == "price_low":
		query = query.orderby(Min(item_price_sale.price_list_rate), order=Order.asc)
	elif sort_by == "price_high":
		query = query.orderby(Min(item_price_sale.price_list_rate), order=Order.desc)
	elif sort_by == "name":
		query = query.orderby("display_name", order=Order.asc)
	elif sort_by == "new_arrival":
		query = query.orderby(style_attribute_variant.modified, order=Order.desc)
	elif sort_by == "discount":
		query = query.orderby(discount_expr, order=Order.desc)
	else:
		query = query.orderby("name", order=Order.asc)
	# Execute Query
	variants = query.run(as_dict=True)
	return variants


def get_total_product_count(filters=None, product_list=None):
	"""Returns total products based on filters"""

	query = get_product_base_query(filters, product_list)
	style_attribute_variant = DocType("Style Attribute Variant")
	query = query.select(
		Count(style_attribute_variant.name).distinct().as_("total_count")
	)
	result = query.run(as_dict=True)
	return result[0]["total_count"] if result else 0


def get_product_base_query(filters=None, product_list=None):
	# Define the DocTypes
	lifestyle_settings = frappe.get_cached_doc("Lifestyle Settings")
	default_price_list = lifestyle_settings.default_price_list
	sale_price_list = lifestyle_settings.sale_price_list
	style_attribute_variant = DocType("Style Attribute Variant")
	website_slideshow_item = DocType("Website Slideshow Item")
	color_size_item = DocType("Color Size Item")
	item_price_default = DocType("Item Price").as_("ip_default")
	item_price_sale = DocType("Item Price").as_("ip_sale")
	item = DocType("Item")

	# Base Query
	query = (
		frappe.qb.from_(style_attribute_variant)
		.left_join(website_slideshow_item)
		.on(
			(website_slideshow_item.parent == style_attribute_variant.name)
			& (website_slideshow_item.idx == 1)
		)
		.left_join(color_size_item)
		.on(color_size_item.parent == style_attribute_variant.name)
		.left_join(item_price_default)
		.on(
			(item_price_default.item_code == color_size_item.item_code)
			& (item_price_default.price_list == default_price_list)
		)
		.left_join(item_price_sale)
		.on(
			(item_price_sale.item_code == color_size_item.item_code)
			& (item_price_sale.price_list == sale_price_list)
		)
		.left_join(item)
		.on(item.name == style_attribute_variant.item_style)
	)
	# Get product details with list of style attribute variant
	if product_list:
		query = query.where(style_attribute_variant.name.isin(product_list))
	else:
		query = query.where(style_attribute_variant.is_published == 1)

	# Apply Filters
	if filters:
		if filters.get("has_discount"):
			query = query.where(
				item_price_default.price_list_rate > item_price_sale.price_list_rate
			)
		if filters.get("subcategory"):
			query = query.where(
				style_attribute_variant.item_group.isin(filters["subcategory"])
			)
		if filters.get("colors"):
			query = query.where(
				style_attribute_variant.attribute_name.isin(filters["colors"])
			)
		if filters.get("sizes"):
			query = query.where(color_size_item.size.isin(filters["sizes"]))
		if filters.get("brands"):
			query = query.where(item.brand.isin(filters["brands"]))
		if filters.get("min_price"):
			query = query.where(item_price_sale.price_list_rate >= filters["min_price"])
		if filters.get("max_price"):
			query = query.where(item_price_sale.price_list_rate <= filters["max_price"])
		if filters.get("search"):
			search = filters.get("search")
			child_categories = get_complete_nested_links(search)
			# Start with the base search conditions
			search_condition = (
				(style_attribute_variant.display_name.like(f"%{search}%"))
				| (style_attribute_variant.attribute_name.like(f"%{search}%"))
				| (style_attribute_variant.name.like(f"%{search}%"))
				| (item.brand.like(f"%{search}%"))
				| (style_attribute_variant.display_name.like(f"%{search}%"))
				| (style_attribute_variant.item_group.like(f"%{search}%"))
				| (item.name.like(f"%{search}%"))
			)
			if child_categories:
				search_condition |= style_attribute_variant.item_group.isin(
					child_categories
				)

			# Add exclusion condition if search starts with "men"
			if search.lower().startswith("men"):
				exclusion_condition = (
					~style_attribute_variant.display_name.like("%women%")
				) & (~style_attribute_variant.item_group.like("%women%"))
				search_condition = search_condition & exclusion_condition

			query = query.where(search_condition)
	return query


def get_delivery_configuration():
	shoe_arena_settings = frappe.get_cached_doc("Lifestyle Settings")
	if not shoe_arena_settings.shipping_rule:
		return 0, 0
	shipping_rule = frappe.get_cached_doc(
		"Shipping Rule", shoe_arena_settings.shipping_rule
	)
	if not shipping_rule or not shipping_rule.conditions:
		return 0, 0
	condition = shipping_rule.conditions[0]
	return condition.shipping_amount, condition.to_value


def get_cod_configuration():
	shoe_arena_settings = frappe.get_cached_doc("Lifestyle Settings")
	return (
		shoe_arena_settings.cod_charge_applicable_below,
		shoe_arena_settings.cod_charge,
	)


def get_currency_symbol():
	currency = frappe.get_cached_value(
		"Global Defaults", "Global Defaults", "default_currency"
	)
	if currency == "SAR" or frappe.conf.developer_mode:
		return '<span class="saudi-currency-symbol pe-0.5"></span>'
	return frappe.get_cached_value("Currency", currency, "symbol")


def get_addresses(party=None, address_type="Billing"):
	if not party:
		party = get_party()
	addresses = get_address_docs(party=party)
	return format_addresses(addresses, address_type)


def format_addresses(addresses, address_type):
	return [
		{
			"name": address.name,
			"title": address.address_title,
			"display": ", ".join(
				[
					part
					for part in [
						address.get("address_line1", ""),
						address.get("address_line2", ""),
						address.get("city", ""),
						address.get("state", ""),
						address.get("country", ""),
						address.get("pincode", ""),
						f"Phone: {address.get('phone')}"
						if address.get("phone")
						else "",
					]
					if part
				]
			),
		}
		for address in addresses
		if address.address_type == address_type
	]


@lru_cache(maxsize=2)
def get_country_list():
	country_list = get_all()
	country_list = [
		{
			"name": country,
			"code": details.get("code", "code"),
			"isd": details.get("isd", "isd"),
		}
		for country, details in country_list.items()
	]

	return country_list


def prevent_welcome_email(doc, method):
	if hasattr(doc, "send_welcome_email"):
		doc.send_welcome_email = 0
	add_roles(doc, method)


def add_roles(doc, method):
	# Todo remove the accounts_user permmission and figure out how to create pe for customer
	roles_to_add = ["Customer"]

	for role in roles_to_add:
		doc.append("roles", {"role": role})


def get_local_lang_url(path: str) -> str:
	if "/ar/" in path and frappe.local.lang == "en":
		return path.replace("/ar/", "/en/")

	if "/en/" in path and frappe.local.lang == "ar":
		return path.replace("/en/", "/ar/")

	return path


def get_current_page():
	query_params = frappe.form_dict
	page = int(query_params.get("page", "1"))
	return page


def can_return(order_name, return_period_days):
	"""Check if the order is still within the return period."""

	invoices = frappe.get_all(
		"Sales Invoice", {"sales_order": order_name}, ["name", "creation"], limit=1
	)
	if not invoices:
		return False
	invoice_creation_date = invoices[0].creation
	creation = get_datetime(invoice_creation_date)
	return_deadline = add_days(creation, int(return_period_days))
	return now_datetime() <= return_deadline


def get_available_stock(item_code, warehouse):
	if not warehouse:
		warehouse = "website_warehouse"
	bin_data = frappe.get_value(
		"Bin",
		{"item_code": item_code, "warehouse": warehouse},
		["actual_qty", "reserved_qty"],
		as_dict=True,
	)
	if not bin_data:
		return {
			"stock_qty": 0,
			"in_stock": 0,
		}
	pos_reserved_qty = get_pos_reserved_qty(item_code, warehouse)
	actual_qty = (
		flt(bin_data.actual_qty) - flt(bin_data.reserved_qty) - flt(pos_reserved_qty)
	)
	return {
		"stock_qty": actual_qty,
		"in_stock": int(actual_qty > 0),
	}


def get_discount_percent(default_price, sale_price):
	"""Calculate the discount percentage."""
	if not default_price or not sale_price:
		return 0
	return ((default_price - sale_price) / default_price) * 100


def get_pos_reserved_qty(item_code, warehouse):
	p_inv = frappe.qb.DocType("POS Invoice")
	p_item = frappe.qb.DocType("POS Invoice Item")

	reserved_qty = (
		frappe.qb.from_(p_inv)
		.from_(p_item)
		.select(Sum(p_item.stock_qty).as_("stock_qty"))
		.where(
			(p_inv.name == p_item.parent)
			& (p_inv.status.isin(["Paid", "Return"]))
			& (p_item.docstatus == 1)
			& (p_item.item_code == item_code)
			& (p_item.warehouse == warehouse)
		)
	).run(as_dict=True)

	return flt(reserved_qty[0].stock_qty) if reserved_qty else 0


def update_so_status_from_related_doc(doc, method):
	sales_orders = set()

	if doc.doctype == "Sales Order":
		frappe.enqueue(
			"ls_shop.utils.update_sales_order_ecommerce_status",
			sales_order_name=doc.name,
			enqueue_after_commit=True,
		)

	elif doc.doctype == "Sales Invoice":
		sales_orders.update([d.sales_order for d in doc.items if d.sales_order])

	elif doc.doctype == "Delivery Note":
		sales_orders.update(
			[d.against_sales_order for d in doc.items if d.against_sales_order]
		)

	elif doc.doctype == "Shipment":
		for dn in doc.shipment_delivery_note:
			so_names = frappe.get_all(
				"Delivery Note Item",
				filters={"parent": dn.delivery_note},
				pluck="against_sales_order",
			)
			sales_orders.update([so for so in so_names if so])
	for so in sales_orders:
		frappe.enqueue(
			"ls_shop.utils.update_sales_order_ecommerce_status",
			sales_order_name=so,
			enqueue_after_commit=True,
		)


def update_sales_order_ecommerce_status(sales_order_name):
	sales_order = frappe.get_doc("Sales Order", sales_order_name)

	if sales_order.docstatus == 2:
		new_status = "Cancelled"
	elif sales_order.docstatus == 0:
		new_status = "Waiting for Approval"
	elif sales_order.docstatus == 1:
		# Check related documents
		dn_exists = frappe.db.exists(
			"Delivery Note Item", {"against_sales_order": sales_order.name}
		)
		shipment_exists = frappe.db.exists(
			"Shipment Delivery Note",
			{
				"delivery_note": [
					"in",
					frappe.get_all(
						"Delivery Note",
						{"against_sales_order": sales_order.name},
						pluck="name",
					),
				]
			},
		)
		invoice_exists = frappe.db.exists(
			"Sales Invoice Item", {"sales_order": sales_order.name}
		)

		if invoice_exists:
			new_status = "Delivered"
		elif shipment_exists:
			new_status = "Shipped"
		elif dn_exists:
			new_status = "Preparing for Shipment"
		else:
			new_status = "Order Received"

	frappe.db.set_value(
		"Sales Order", sales_order.name, "custom_ecommerce_status", new_status
	)
