import frappe
from frappe import _
from frappe.utils.data import cstr, flt

from ls_shop.product_detail import get_available_sizes, get_price, get_selected_item
from ls_shop.utils import get_available_stocks


def get_cart_item_codes(items) -> list[str]:
	return [
		cstr(entry.get("variant", {}).get("item_code"))
		for entry in items
		if entry.get("variant", {}).get("item_code")
	]


def get_cart_price(item_code: str, default_price_list: str, sale_price_list: str) -> tuple[float, float]:
	"""Struck-through price and the price actually charged, resolved the way the product page does it.

	get_price returns None for "not on this list", which is why the sale price falls back instead of
	being read as free: an item with no sale row otherwise goes onto the order at zero.
	"""
	default_price = flt(get_price({"item_code": item_code}, default_price_list))
	sale_price = get_price({"item_code": item_code}, sale_price_list)
	return default_price, sale_price if sale_price is not None else default_price


def get_stock_shortfalls(items) -> list[str]:
	"""Cart lines the warehouse cannot fulfil, as shopper-facing strings. Empty when the cart is sellable."""
	warehouse = frappe.get_cached_value("Lifestyle Settings", "Lifestyle Settings", "ecommerce_warehouse")
	stock_by_item_code = get_available_stocks(get_cart_item_codes(items), warehouse)

	shortfalls = []
	for entry in items:
		item_code = cstr(entry.get("variant", {}).get("item_code"))
		if not item_code:
			continue

		available_qty = flt(stock_by_item_code.get(item_code, {}).get("stock_qty", 0))
		requested_qty = flt(entry.get("qty", 1))
		if requested_qty > available_qty:
			item_name = entry.get("item", {}).get("display_name") or item_code
			shortfalls.append(
				_("{0} - Requested: {1}, In Stock: {2}").format(
					item_name, f"{requested_qty:g}", f"{available_qty:g}"
				)
			)

	return shortfalls


def validate_stock_available(items):
	"""Refuse a cart the warehouse cannot fulfil.

	The cart page checks this too, but that check lives in the browser: without this a tampered client
	posts any quantity it likes and gets an accepted quotation back.
	"""
	shortfalls = get_stock_shortfalls(items)
	if not shortfalls:
		return

	frappe.throw(
		_("Some items are out of stock:") + "<br>" + "<br>".join(shortfalls),
		title=_("Out Of Stock"),
	)


@frappe.whitelist(allow_guest=True)
def get_detail_for_cart_items(items):
	items = frappe.parse_json(items)
	lifestyle_settings = frappe.get_cached_doc("Lifestyle Settings")
	warehouse = lifestyle_settings.ecommerce_warehouse
	default_price_list = lifestyle_settings.get_default_price_list()
	sale_price_list = lifestyle_settings.get_sale_price_list()

	item_codes = get_cart_item_codes(items)
	stock_by_item_code = get_available_stocks(item_codes, warehouse)

	stock_data = {}
	for item_code in item_codes:
		default_price, sale_price = get_cart_price(item_code, default_price_list, sale_price_list)
		stock_data[item_code] = {
			"stock": stock_by_item_code.get(item_code, {}).get("stock_qty", 0),
			"default_price": default_price,
			"sale_price": sale_price,
		}

	return {"stock_data": stock_data}


@frappe.whitelist(allow_guest=True)
def validate_cart_stock(items):
	errors = get_stock_shortfalls(frappe.parse_json(items))
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

	default_price, sale_price = get_cart_price(
		selected_item["item_code"],
		lifestyle_settings.get_default_price_list(),
		lifestyle_settings.get_sale_price_list(),
	)

	return {
		"variant": selected_item,
		"default_price": default_price,
		"price": sale_price,
	}
