import frappe
from frappe.utils.caching import site_cache

from ls_shop.utils import get_available_stock, get_discount_percent, get_product_list


def get_context(context):
	# Get route and size from URL
	product_route = frappe.form_dict.get("route")
	selected_size = frappe.form_dict.get("size")
	size_selected = selected_size

	# Get settings
	lifestyle_settings = frappe.get_cached_doc("Lifestyle Settings")
	warehouse = lifestyle_settings.ecommerce_warehouse

	try:
		# Fetch product variant and related item
		product_variant = frappe.get_doc(
			"Style Attribute Variant", {"route": product_route}
		)
		product = frappe.get_doc("Item", product_variant.item_style)

		# Get available sizes and selected item
		available_sizes = get_available_sizes(product_variant, warehouse)
		selected_item = get_selected_item(available_sizes, selected_size)
		if not selected_item:
			selected_item = available_sizes[0] if available_sizes else None

		# Default to first size if none selected
		if not selected_size:
			selected_size = selected_item["size"]

		# Get prices
		default_price_list = lifestyle_settings.get_default_price_list()
		sale_price_list = lifestyle_settings.get_sale_price_list()
		price_data = {
			"default_price": get_price_data(selected_item, default_price_list),
			"sale_price": get_price_data(selected_item, sale_price_list),
		}

		recommended_items = get_recommended_products(product_variant)

	except frappe.exceptions.DoesNotExistError:
		raise frappe.PageDoesNotExistError()

	if not product_variant.is_published:
		raise frappe.PageDoesNotExistError()

	# Get other variants
	other_variants = get_other_variants(product_variant)

	# Basic context setup
	context.product_variant = product_variant
	context.product = product
	context.images = (
		[image.image for image in product_variant.images]
		if product_variant.images
		else [default_product_image()]
	)
	context.product_in_stock = (
		selected_item.get("stock_detail", {}).get("stock_qty", 0) > 0
	)

	# Enrich selected item details
	selected_item_doc = frappe.get_cached_doc("Item", selected_item["item_code"])
	selected_item.update(
		{
			"item_name": selected_item_doc.item_name,
			"item_name_ar": selected_item_doc.get("custom_item_name_ar")
			or selected_item_doc.item_name,
			"style_code": selected_item_doc.get("custom_style_code", ""),
			"material": selected_item_doc.get("custom_material", ""),
			"description": selected_item_doc.get("description", ""),
			"description_ar": selected_item_doc.get(
				"custom_description_ar", selected_item_doc.description
			),
		}
	)

	# Set final context values
	context.available_sizes = available_sizes
	context.selected_size = selected_size
	context.size_selected = size_selected
	context.selected_item = selected_item
	context.selected_price = price_data["sale_price"]
	context.default_price = price_data["default_price"]
	context.recommended_items = recommended_items
	context.other_variants = other_variants
	context.discount_percent = get_discount_percent(
		price_data["default_price"], price_data["sale_price"]
	)
	context.size_chart = get_size_chart(product.brand, product_variant.item_group)
	context.item_qty = get_available_stock(product.item_code, warehouse)
	context.breadcrumbs = [
		{"label": "Products", "href": f"/{frappe.local.lang}/products/"},
		{"label": product_variant.display_name, "href": ""},
	]


def default_product_image():
	return "/assets/ls_shop/images/1.jpg"


def get_recommended_products(product_variant):
	style_attribute_variants = frappe.get_all(
		"Style Attribute Variant",
		filters={
			"item_group": product_variant.item_group,
			"is_published": True,
			"configurator": ["not in", [product_variant.configurator]],
		},
		pluck="name",
		limit=8,
	)

	return get_product_list(product_list=style_attribute_variants)


def get_available_sizes(product_variant, warehouse):
	size_order_list = ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]

	sizes = [
		{
			"item_code": size.item_code,
			"size": size.size,
			"stock_detail": get_available_stock(size.item_code, warehouse),
		}
		for size in product_variant.sizes
	]

	first_size = sizes[0]["size"]
	is_numeric = False
	try:
		float(first_size)
		is_numeric = True
	except ValueError:
		pass

	if is_numeric:
		sorted_sizes = sorted(sizes, key=lambda x: float(x["size"]))
	else:
		sorted_sizes = sorted(
			sizes,
			key=lambda x: size_order_list.index(x["size"].upper())
			if x["size"].upper() in size_order_list
			else 999,
		)

	return sorted_sizes


def get_price_data(selected_item, price_list):
	price = frappe.get_cached_value(
		"Item Price",
		{
			"item_code": selected_item["item_code"],
			"price_list": price_list,
		},
		"price_list_rate",
	)
	if price is None:
		price = 0.0
	return price


def get_other_variants(product_variant):
	variants = frappe.db.get_all(
		"Style Attribute Variant",
		filters={
			"configurator": product_variant.configurator,
			"name": ("!=", product_variant.name),
			"is_published": True,
		},
		fields=["name"],
	)
	variants = [variant["name"] for variant in variants]
	if not variants:
		return []
	other_variants = get_product_list(product_list=variants)
	return other_variants


def get_selected_item(available_sizes, selected_size):
	return next(
		(s for s in available_sizes if s["size"] == selected_size),
		next(
			(s for s in available_sizes if s["stock_detail"].get("in_stock") == 1),
			None,  # fallback if none are in stock
		),
	)


def get_size_chart(brand, item_group):
	size_chart = frappe.get_cached_value(
		"Size Chart", {"brand": brand, "item_group": item_group}, "size_chart_json"
	)

	return size_chart
