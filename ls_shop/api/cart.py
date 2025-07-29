import frappe
from frappe import _

from ls_shop.utils import get_available_stock
from ls_shop.www.products.details import (
	get_available_sizes,
	get_price_data,
	get_selected_item,
)


@frappe.whitelist(allow_guest=True)
def get_detail_for_cart_items(items):
	stock_data = {}
	warehouse = frappe.get_cached_value(
		"Lifestyle Settings", "Lifestyle Settings", "ecommerce_warehouse"
	)
	default_price_list = frappe.get_cached_value(
		"Lifestyle Settings", "Lifestyle Settings", "default_price_list"
	)
	sale_price_list = frappe.get_cached_value(
		"Lifestyle Settings", "Lifestyle Settings", "sale_price_list"
	)
	default_price = 0
	sale_price = 0
	for entry in items:
		item_code = entry.get("variant", {}).get("item_code")

		if not item_code:
			continue

		stock_qty = get_available_stock(item_code, warehouse=warehouse)

		sale_item_price = frappe.get_all(
			"Item Price",
			{"price_list": sale_price_list, "item_code": item_code},
			limit=1,
			pluck="price_list_rate",
		)
		sale_price = sale_item_price[0] if sale_item_price else 0
		default_item_price = (
			frappe.get_all(
				"Item Price",
				{"price_list": default_price_list, "item_code": item_code},
				limit=1,
				pluck="price_list_rate",
			)
			if default_price_list
			else 0
		)
		default_price = default_item_price[0] if default_item_price else 0

		stock_data[f"{item_code}"] = {
			"stock": stock_qty.get("stock_qty", 0),
			"default_price": default_price,
			"sale_price": sale_price,
		}
	return {"stock_data": stock_data}


@frappe.whitelist(allow_guest=True)
def validate_cart_stock(items):
	errors = []
	warehouse = frappe.get_cached_value(
		"Lifestyle Settings", "Lifestyle Settings", "ecommerce_warehouse"
	)
	for entry in items:
		item_code = entry.get("variant", {}).get("item_code")
		item_name = entry.get("item", {}).get("display_name")
		requested_qty = entry.get("qty", 1)
		if not item_code:
			continue

		stock_qty = get_available_stock(item_code, warehouse=warehouse)

		if requested_qty > stock_qty.get("stock_qty", 0):
			errors.append(
				f"{item_name} - Requested: {requested_qty}, In Stock: {stock_qty.get('stock_qty',0)}"
			)

	if errors:
		return {"message": errors}

	return {"success": True}


@frappe.whitelist()
def update_variant(product_name, size):
	product_variant = frappe.get_cached_doc("Style Attribute Variant", product_name)
	lifestyle_settings = frappe.get_cached_doc("Lifestyle Settings")
	warehouse = lifestyle_settings.ecommerce_warehouse
	available_sizes = get_available_sizes(product_variant, warehouse)
	selected_item = get_selected_item(available_sizes, size)
	if not selected_item or selected_item.get("size") != size:
		frappe.throw(_("Selected size not found."))
	default_price_list = lifestyle_settings.get_default_price_list()
	sale_price_list = lifestyle_settings.get_sale_price_list()

	default_price = get_price_data(selected_item, default_price_list)
	sale_price = get_price_data(selected_item, sale_price_list)

	return {
		"variant": selected_item,
		"default_price": default_price,
		"price": sale_price,
	}
