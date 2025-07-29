import frappe
from frappe.query_builder import DocType
from frappe.utils.caching import site_cache
from webshop.webshop.shopping_cart.cart import _get_cart_quotation, get_cart_quotation

from ls_shop.utils import (
	format_addresses,
	get_addresses,
	get_cod_configuration,
	get_country_list,
	get_delivery_configuration,
)

# from ls_shop.api.utils import auth_required

no_cache = True


# @auth_required
def get_context(context):
	current_user = frappe.session.user
	if current_user == "Guest":
		raise frappe.PermissionError
	cart_quotation = _get_cart_quotation()
	if not cart_quotation or not cart_quotation.items:
		frappe.redirect(f"/{frappe.local.lang}/cart")
	lifestyle_settings = frappe.get_cached_doc("Lifestyle Settings")
	default_price_list = lifestyle_settings.get("default_price_list")
	context.show_telr = lifestyle_settings.get("telr_enabled", 0)
	context.show_tabby = lifestyle_settings.get("tabby_enabled", 0)
	context.show_cod = lifestyle_settings.get("cod_enabled", 0)
	context.cart_quotation = cart_quotation
	context.coupon_code = get_coupon_code(cart_quotation)
	context.country_list = get_country_list()
	items = get_checkout_items(cart_quotation)
	if default_price_list:
		for item in items:
			item["default_price"] = frappe.get_cached_value(
				"Item Price",
				{"item_code": item.item_code, "price_list": default_price_list},
				"price_list_rate",
			)
	context.items = items
	context.billing_addresses = get_addresses()
	context.shipping_addresses = get_addresses(address_type="Shipping")
	context.store_pickup_addresses = get_store_pickup_addresses()
	context.delivery_charge, context.delivery_charge_applicable_below = (
		get_delivery_configuration()
	)
	context.cod_charge_applicable_below, context.cod_charge = get_cod_configuration()
	context.breadcrumbs = [
		{
			"label": "Cart",
			"href": f"/{frappe.local.lang}/cart/",
		},
		{
			"label": "Checkout",
			"href": "#",
		},
	]


def get_coupon_code(cart_quotation):
	coupon_code = ""
	try:
		coupon_code = frappe.get_cached_value(
			"Coupon Code", cart_quotation.coupon_code, "coupon_code"
		)
	except Exception:
		pass
	return coupon_code


def get_checkout_items(cart_quotation):
	quotation_item = DocType("Quotation Item")
	style_attribute_variant = DocType("Style Attribute Variant")
	color_size_item = DocType("Color Size Item")
	website_slideshow_item = DocType("Website Slideshow Item")
	item = DocType("Item")
	item_variant_attribute = DocType("Item Variant Attribute")
	has_custom_name_ar = frappe.db.has_column("Item", "custom_item_name_ar")
	query = (
		frappe.qb.from_(color_size_item)
		.left_join(quotation_item)
		.on(quotation_item.item_code == color_size_item.item_code)
		.left_join(style_attribute_variant)
		.on(color_size_item.parent == style_attribute_variant.name)
		.left_join(website_slideshow_item)
		.on(website_slideshow_item.parent == style_attribute_variant.name)
		.left_join(item)
		.on(item.name == style_attribute_variant.item_style)
		.left_join(item_variant_attribute)
		.on(item_variant_attribute.parent == quotation_item.item_code)
		.where(quotation_item.parent == cart_quotation.name)
		.where(item_variant_attribute.attribute == "Size")
		.select(
			style_attribute_variant.name,
			style_attribute_variant.item_style,
			style_attribute_variant.display_name,
			item.brand,
			item.item_name,
			website_slideshow_item.image.as_("image"),
			quotation_item.item_code,
			quotation_item.qty,
			quotation_item.rate,
			quotation_item.price_list_rate,
			quotation_item.amount,
			item_variant_attribute.attribute_value.as_("size"),
		)
		.groupby(quotation_item.name)
	)
	if has_custom_name_ar:
		query = query.select(item.custom_item_name_ar.as_("custom_item_name_ar"))
	return query.run(as_dict=True)


@site_cache(ttl=60 * 60)
def get_store_pickup_addresses():
	# Get all warehouse names with store pickup
	warehouses = frappe.get_all(
		"Warehouse", filters={"custom_store_pickup": 1}, pluck="name"
	)
	if not warehouses:
		return []

	# Get all dynamic links for those warehouses and build a warehouse -> address map
	links = frappe.get_all(
		"Dynamic Link",
		filters={
			"link_doctype": "Warehouse",
			"link_name": ["in", warehouses],
			"parenttype": "Address",
		},
		fields=["link_name", "parent"],
	)

	if not links:
		return []

	# Map address to warehouse
	address_to_warehouse = {link["parent"]: link["link_name"] for link in links}
	address_names = list(address_to_warehouse.keys())
	addresses = frappe.get_all(
		"Address", filters={"name": ["in", address_names]}, fields=["*"]
	)
	# Format and attach warehouse info
	formatted_addresses = format_addresses(addresses, address_type="Shop")
	for addr in formatted_addresses:
		addr["warehouse_name"] = address_to_warehouse.get(addr["name"])

	return formatted_addresses
