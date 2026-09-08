# Copyright (c) 2026, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe
from erpnext.controllers.item_variant import create_variant
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Count, Sum
from frappe.utils import add_days, create_batch, get_url, nowdate
from frappe.utils.data import cint, cstr, flt

from ls_shop.api.variant_pricing import (
	get_base_price_rows_by_key,
	get_selling_price_lists,
	set_variant_prices,
)
from ls_shop.utils import IN_CLAUSE_CHUNK_SIZE

PAGE_LENGTH = 20
BULK_PRODUCT_LIMIT = 100

# Every doctype that makes a product historical, in the order a merchant would recognise. Storefront
# Analytics Event is a plain Link to Item that hooks.py deliberately does not ignore on delete.
HISTORY_BLOCKERS = (
	"Sales Order Item",
	"Delivery Note Item",
	"Sales Invoice Item",
	"Packing Slip Item",
	"Quotation Item",
	"Material Request Item",
	"Stock Ledger Entry",
	"Storefront Analytics Event",
)

# ERPNext's Item.on_trash deletes these itself, before the framework's link check ever runs, so an
# up-front check that counted them would refuse a product the real delete would have taken.
CLEARED_ON_ITEM_TRASH = ("Bin", "Item Price")


@frappe.whitelist()
def get_products(
	search: str | None = None,
	collection: str | None = None,
	disabled: int | None = None,
	start: int = 0,
	page_length: int = PAGE_LENGTH,
):
	"""One call, one complete Products screen.

	Every lookup is batched across the page, so adding a column never costs a query per row.
	"""
	frappe.has_permission("Item", ptype="read", throw=True)

	# Imported here because orders imports this module at import time; a module-level import would cycle.
	from ls_shop.api.admin.orders import get_reporting_currency

	currency = get_reporting_currency()

	start = cint(start)
	page_length = cint(page_length) or PAGE_LENGTH

	configurators = frappe.get_all(
		"Style Attribute Configurator",
		fields=["name", "item_template", "item_attribute"],
	)
	if not configurators:
		return {"products": [], "total": 0, "currency": currency}

	templates_by_configurator = {row.name: row.item_template for row in configurators}

	item_filters = {"name": ["in", list(set(templates_by_configurator.values()))]}
	if search:
		item_filters["item_name"] = ["like", f"%{search}%"]
	if collection:
		item_filters["item_group"] = collection
	if disabled is not None:
		item_filters["disabled"] = cint(disabled)

	total = frappe.db.count("Item", item_filters)
	templates = frappe.get_all(
		"Item",
		filters=item_filters,
		fields=["name", "item_name", "image", "item_group", "disabled", "modified"],
		order_by="modified desc",
		start=start,
		page_length=page_length,
	)
	if not templates:
		return {"products": [], "total": total, "currency": currency}

	template_names = {row.name for row in templates}
	page_configurators = [
		name for name, template in templates_by_configurator.items() if template in template_names
	]

	variants = frappe.get_all(
		"Style Attribute Variant",
		filters={"configurator": ["in", page_configurators]},
		fields=["name", "configurator", "attribute_value", "display_name", "is_published", "route"],
	)
	variant_names = [row.name for row in variants]

	sizes = (
		frappe.get_all(
			"Color Size Item",
			filters={"parent": ["in", variant_names], "parenttype": "Style Attribute Variant"},
			fields=["parent", "size", "item_code"],
		)
		if variant_names
		else []
	)
	item_codes = [row.item_code for row in sizes if row.item_code]

	rates_by_item_code = get_selling_rates(item_codes)
	stock_by_item_code = get_ecommerce_stock(item_codes)

	# A dashboard-created product never sets Item.image, so fall back to the first option image.
	first_image_by_variant = {}
	if variant_names:
		for row in frappe.get_all(
			"Website Slideshow Item",
			filters={"parent": ["in", variant_names], "parenttype": "Style Attribute Variant"},
			fields=["parent", "image"],
			order_by="idx asc",
		):
			first_image_by_variant.setdefault(row.parent, row.image)

	item_codes_by_variant = {}
	for row in sizes:
		if row.item_code:
			item_codes_by_variant.setdefault(row.parent, []).append(row.item_code)

	variants_by_template = {}
	for row in variants:
		template = templates_by_configurator.get(row.configurator)
		if template:
			variants_by_template.setdefault(template, []).append(row)

	products = []
	for template in templates:
		template_variants = variants_by_template.get(template.name, [])
		template_item_codes = [
			item_code for row in template_variants for item_code in item_codes_by_variant.get(row.name, [])
		]
		rates = [rates_by_item_code[code] for code in template_item_codes if code in rates_by_item_code]

		products.append(
			{
				"name": template.name,
				"title": template.item_name,
				"image": template.image
				or next(
					(
						first_image_by_variant[row.name]
						for row in template_variants
						if row.name in first_image_by_variant
					),
					None,
				),
				"collection": template.item_group,
				"disabled": bool(template.disabled),
				"updated": template.modified,
				"variant_count": len(template_variants),
				"published_count": sum(1 for row in template_variants if row.is_published),
				"price_from": min(rates) if rates else None,
				"price_to": max(rates) if rates else None,
				"stock": sum(stock_by_item_code.get(code, 0) for code in template_item_codes),
				"variants": [
					{
						"name": row.name,
						"option": row.attribute_value or row.display_name,
						"is_published": bool(row.is_published),
						"route": row.route,
						"size_count": len(item_codes_by_variant.get(row.name, [])),
					}
					for row in template_variants
				],
			}
		)

	return {"products": products, "total": total, "currency": currency}


def get_default_rates(item_codes):
	if not item_codes:
		return {}

	default_price_list, _sale_price_list = get_selling_price_lists()
	rows = frappe.get_all(
		"Item Price",
		filters={"item_code": ["in", item_codes], "price_list": default_price_list},
		fields=["item_code", "price_list_rate"],
	)
	return {cstr(row.item_code): flt(row.price_list_rate) for row in rows}


def get_selling_rates(item_codes):
	"""The rate a shopper actually pays: the sale rate where one is set, the default otherwise.
	get_default_rates() is the list price - quoting that advertises the struck-through figure."""
	if not item_codes:
		return {}

	default_price_list, sale_price_list = get_selling_price_lists()
	price_rows_by_key = get_base_price_rows_by_key(item_codes, [default_price_list, sale_price_list])

	rates = {}
	for (item_code, price_list), row in price_rows_by_key.items():
		if price_list == sale_price_list:
			rates[item_code] = flt(row.price_list_rate)
		elif price_list == default_price_list:
			rates.setdefault(item_code, flt(row.price_list_rate))
	return rates


def get_ecommerce_stock(item_codes):
	if not item_codes:
		return {}

	warehouse = frappe.get_cached_value("Lifestyle Settings", "Lifestyle Settings", "ecommerce_warehouse")
	if not warehouse:
		# ponytail: stock reads as zero until the warehouse is set, revisit if multi-warehouse lands
		return {}

	rows = frappe.get_all(
		"Bin",
		filters={"item_code": ["in", item_codes], "warehouse": warehouse},
		fields=["item_code", "actual_qty"],
	)
	return {cstr(row.item_code): flt(row.actual_qty) for row in rows}


def get_size_prices(item_codes):
	"""Both price lists for a set of sizes, keyed by item_code - what a size-level price editor
	needs (get_default_rates() above only serves the list screen's single price_from/price_to)."""
	if not item_codes:
		return {}

	default_price_list, sale_price_list = get_selling_price_lists()
	price_rows_by_key = get_base_price_rows_by_key(item_codes, [default_price_list, sale_price_list])

	prices = {}
	for (item_code, price_list), row in price_rows_by_key.items():
		bucket = prices.setdefault(item_code, {"default_rate": None, "sale_rate": None})
		if price_list == default_price_list:
			bucket["default_rate"] = flt(row.price_list_rate)
		elif price_list == sale_price_list:
			bucket["sale_rate"] = flt(row.price_list_rate)
	return prices


def get_size_stock(item_codes):
	"""On-hand and committed (Bin.reserved_qty) for a set of sizes, keyed by item_code - a superset
	of get_ecommerce_stock() above, which only serves the list screen's summed total."""
	if not item_codes:
		return {}

	warehouse = frappe.get_cached_value("Lifestyle Settings", "Lifestyle Settings", "ecommerce_warehouse")
	if not warehouse:
		return {}

	rows = frappe.get_all(
		"Bin",
		filters={"item_code": ["in", item_codes], "warehouse": warehouse},
		fields=["item_code", "actual_qty", "reserved_qty"],
	)
	return {
		cstr(row.item_code): {"stock": flt(row.actual_qty), "committed": flt(row.reserved_qty)}
		for row in rows
	}


def get_restock_level(item_codes):
	"""The level this product is called low at, or None when its sizes do not share one. Reads
	inventory.get_low_stock_levels(), so the Stock screen cannot judge a size by a different number."""
	from ls_shop.api.admin.inventory import get_low_stock_levels

	if not item_codes:
		return None

	levels = set(get_low_stock_levels(item_codes).values())
	return levels.pop() if len(levels) == 1 else None


def get_product_chain(item_template: str | int):
	"""One product's configurators, options and sellable size item codes, in three batched queries -
	the same traversal get_product() walks, shared by the whole-product operations below."""
	configurators = frappe.get_all(
		"Style Attribute Configurator", filters={"item_template": item_template}, pluck="name"
	)
	variant_names = (
		frappe.get_all(
			"Style Attribute Variant", filters={"configurator": ["in", configurators]}, pluck="name"
		)
		if configurators
		else []
	)
	sizes = (
		frappe.get_all(
			"Color Size Item",
			filters={"parent": ["in", variant_names], "parenttype": "Style Attribute Variant"},
			fields=["item_code"],
		)
		if variant_names
		else []
	)

	return {
		"configurators": configurators,
		"variants": variant_names,
		"item_codes": list({row.item_code for row in sizes if row.item_code}),
	}


def get_collection(collection: str) -> str:
	"""The one answer to "is this a valid collection?", shared by every writer of Item.item_group.
	A collection is a leaf Item Group (see list_collections), so a structural parent is refused."""
	item_group = frappe.db.get_value(
		"Item Group", cstr(collection).strip(), ["name", "lft", "rgt"], as_dict=True
	)
	if not item_group:
		frappe.throw(_("Collection {0} does not exist.").format(collection))
	if item_group.rgt != item_group.lft + 1:
		frappe.throw(
			_("{0} holds other collections, so products cannot be filed under it.").format(item_group.name)
		)
	return item_group.name


def get_variant_names(item_templates: list) -> list:
	"""Every option of a set of products, in two queries however many products are passed."""
	if not item_templates:
		return []

	configurators = frappe.get_all(
		"Style Attribute Configurator", filters={"item_template": ["in", item_templates]}, pluck="name"
	)
	if not configurators:
		return []
	return frappe.get_all(
		"Style Attribute Variant", filters={"configurator": ["in", configurators]}, pluck="name"
	)


def save_variant_collections(item_templates: list) -> None:
	"""Re-file these products' options under the collection the products now carry - the storefront indexes
	Style Attribute Variant.item_group, and update_item_group() only fills it while blank."""
	for variant_name in get_variant_names(item_templates):
		# ponytail: one save per option so update_item_group and the search sync hooks run; move to
		# a background job if a store ever files more options at once than a request can carry.
		variant = frappe.get_doc("Style Attribute Variant", variant_name)
		variant.item_group = None
		variant.save()


@frappe.whitelist()
def get_pricing_rows(
	search: str | None = None,
	collection: str | None = None,
	start: int = 0,
	page_length: int = PAGE_LENGTH,
):
	"""One row per sellable option (Style Attribute Variant) - the unit Pricing.vue prices. Reuses
	get_products()'s batched joins at variant grain, carrying each variant's own default_rate/sale_rate."""
	frappe.has_permission("Item", ptype="read", throw=True)

	from ls_shop.api.admin.orders import get_reporting_currency

	currency = get_reporting_currency()

	start = cint(start)
	page_length = cint(page_length) or PAGE_LENGTH

	configurators = frappe.get_all("Style Attribute Configurator", fields=["name", "item_template"])
	if not configurators:
		return {"rows": [], "total": 0, "currency": currency}
	templates_by_configurator = {row.name: row.item_template for row in configurators}

	item_filters = {"name": ["in", list(set(templates_by_configurator.values()))]}
	if search:
		item_filters["item_name"] = ["like", f"%{search}%"]
	if collection:
		item_filters["item_group"] = collection

	templates = frappe.get_all("Item", filters=item_filters, fields=["name", "item_name"])
	if not templates:
		return {"rows": [], "total": 0, "currency": currency}
	title_by_template = {row.name: row.item_name for row in templates}
	template_names = set(title_by_template)
	page_configurators = [
		name for name, template in templates_by_configurator.items() if template in template_names
	]

	variant_filters = {"configurator": ["in", page_configurators]}
	total = frappe.db.count("Style Attribute Variant", variant_filters)
	variants = frappe.get_all(
		"Style Attribute Variant",
		filters=variant_filters,
		fields=["name", "configurator", "attribute_value", "display_name"],
		order_by="modified desc",
		start=start,
		page_length=page_length,
	)
	if not variants:
		return {"rows": [], "total": total, "currency": currency}

	variant_names = [row.name for row in variants]
	sizes = frappe.get_all(
		"Color Size Item",
		filters={"parent": ["in", variant_names], "parenttype": "Style Attribute Variant"},
		fields=["parent", "size", "item_code"],
		order_by="idx asc",
	)

	# The first size (by idx) stands in for the whole variant - the same "one price for what is
	# really N size-level prices" convention VariantEditor.vue's matrix editor already uses.
	first_size_by_variant = {}
	size_count_by_variant = {}
	for row in sizes:
		size_count_by_variant[row.parent] = size_count_by_variant.get(row.parent, 0) + 1
		first_size_by_variant.setdefault(row.parent, row)

	item_codes = [row.item_code for row in first_size_by_variant.values() if row.item_code]
	prices_by_item_code = get_size_prices(item_codes)

	first_image_by_variant = {}
	for row in frappe.get_all(
		"Website Slideshow Item",
		filters={"parent": ["in", variant_names], "parenttype": "Style Attribute Variant"},
		fields=["parent", "image"],
		order_by="idx asc",
	):
		first_image_by_variant.setdefault(row.parent, row.image)

	rows = []
	for row in variants:
		template = templates_by_configurator.get(row.configurator)
		size = first_size_by_variant.get(row.name)
		price = prices_by_item_code.get(cstr(size.item_code), {}) if size else {}
		rows.append(
			{
				"name": row.name,
				"title": title_by_template.get(template, template),
				"subtitle": row.attribute_value or row.display_name,
				"sku": size.item_code if size else None,
				"image": first_image_by_variant.get(row.name),
				"default_rate": price.get("default_rate"),
				"sale_rate": price.get("sale_rate"),
				"size_count": size_count_by_variant.get(row.name, 0),
			}
		)

	return {"rows": rows, "total": total, "currency": currency}


@frappe.whitelist()
def get_product(item_template: str):
	"""Everything one product's edit screen needs, in one call."""
	frappe.has_permission("Item", doc=item_template, ptype="read", throw=True)

	template = frappe.db.get_value(
		"Item",
		item_template,
		["name", "item_name", "image", "item_group", "description", "disabled", "modified"],
		as_dict=True,
	)
	if not template:
		frappe.throw(_("Product {0} not found").format(item_template))

	configurators = frappe.get_all(
		"Style Attribute Configurator",
		filters={"item_template": item_template},
		fields=["name", "item_attribute"],
	)
	variants = (
		frappe.get_all(
			"Style Attribute Variant",
			filters={"configurator": ["in", [row.name for row in configurators]]},
			fields=["name", "attribute_value", "display_name", "is_published", "route"],
		)
		if configurators
		else []
	)
	variant_names = [row.name for row in variants]

	sizes = (
		frappe.get_all(
			"Color Size Item",
			filters={"parent": ["in", variant_names], "parenttype": "Style Attribute Variant"},
			fields=["parent", "size", "item_code"],
		)
		if variant_names
		else []
	)
	images = (
		frappe.get_all(
			"Website Slideshow Item",
			filters={"parent": ["in", variant_names], "parenttype": "Style Attribute Variant"},
			fields=["parent", "image"],
		)
		if variant_names
		else []
	)

	item_codes = [row.item_code for row in sizes if row.item_code]
	prices_by_item_code = get_size_prices(item_codes)
	stock_by_item_code = get_size_stock(item_codes)
	restock_level = get_restock_level(item_codes)

	sizes_by_variant = {}
	for row in sizes:
		price = prices_by_item_code.get(cstr(row.item_code), {})
		stock = stock_by_item_code.get(cstr(row.item_code), {})
		sizes_by_variant.setdefault(row.parent, []).append(
			{
				"size": row.size,
				"item_code": row.item_code,
				# default_rate is the MRP shown struck through once a sale_rate is set - product_detail.py's
				# get_discount_percent treats sale_rate as what the shopper actually pays.
				"default_rate": price.get("default_rate"),
				"sale_rate": price.get("sale_rate"),
				"stock": stock.get("stock", 0),
				"committed": stock.get("committed", 0),
			}
		)

	images_by_variant = {}
	for row in images:
		images_by_variant.setdefault(row.parent, []).append(row.image)

	return {
		"name": template.name,
		"title": template.item_name,
		"image": template.image,
		"collection": template.item_group,
		"description": template.description,
		"disabled": bool(template.disabled),
		"updated": template.modified,
		"restock_level": restock_level,
		"option_attribute": configurators[0].item_attribute if configurators else None,
		"variants": [
			{
				"name": row.name,
				"option": row.attribute_value or row.display_name,
				"is_published": bool(row.is_published),
				"route": row.route,
				"storefront_url": get_url(f"/products/{row.route}") if row.route else None,
				"sizes": sizes_by_variant.get(row.name, []),
				"images": images_by_variant.get(row.name, []),
				"blockers": get_publish_blockers(
					images_by_variant.get(row.name, []), sizes_by_variant.get(row.name, [])
				),
			}
			for row in variants
		],
		"recent_sales": get_recent_product_sales(item_codes),
	}


def get_recent_product_sales(item_codes, window_days: int = 30):
	"""Units/orders/revenue for one product's own sizes over the trailing window - a single query
	scoped to one product's item codes, not the store-wide scan orders.get_overview() runs."""
	if not item_codes:
		return {"window_days": window_days, "units_sold": 0, "order_count": 0, "revenue": 0}

	sales_order = frappe.qb.DocType("Sales Order")
	sales_order_item = frappe.qb.DocType("Sales Order Item")
	rows = (
		frappe.qb.from_(sales_order_item)
		.join(sales_order)
		.on(sales_order.name == sales_order_item.parent)
		.select(sales_order_item.qty, sales_order_item.amount, sales_order.name)
		.where(
			(sales_order_item.item_code.isin(item_codes))
			& (sales_order.docstatus == 1)
			& (sales_order.transaction_date >= add_days(nowdate(), -window_days))
		)
		.run(as_dict=True)
	)

	return {
		"window_days": window_days,
		"units_sold": sum(flt(row.qty) for row in rows),
		"order_count": len({row.name for row in rows}),
		"revenue": sum(flt(row.amount) for row in rows),
	}


TOP_PRODUCTS_LIMIT = 4


@frappe.whitelist()
def get_top_products(limit: int = TOP_PRODUCTS_LIMIT):
	"""Home screen bestsellers, one row per product template. A Sales Order Item's item_code is a single
	size, so this walks size -> variant -> configurator and sums in SQL; drafts count, as is_webshop_order does."""
	frappe.has_permission("Item", ptype="read", throw=True)

	# Delayed import: orders.py imports this module at import time, so a module-level import here
	# would cycle - same guard get_products() above already uses for get_reporting_currency.
	from ls_shop.api.admin.orders import get_reporting_currency, is_webshop_order

	sales_order = frappe.qb.DocType("Sales Order")
	sales_order_item = frappe.qb.DocType("Sales Order Item")
	color_size_item = frappe.qb.DocType("Color Size Item")
	variant = frappe.qb.DocType("Style Attribute Variant")
	configurator = frappe.qb.DocType("Style Attribute Configurator")
	revenue = Sum(sales_order_item.base_amount)

	rows = (
		frappe.qb.from_(sales_order_item)
		.join(sales_order)
		.on(sales_order.name == sales_order_item.parent)
		.join(color_size_item)
		.on(
			(color_size_item.item_code == sales_order_item.item_code)
			& (color_size_item.parenttype == "Style Attribute Variant")
		)
		.join(variant)
		.on(variant.name == color_size_item.parent)
		.join(configurator)
		.on(configurator.name == variant.configurator)
		.select(configurator.item_template, Sum(sales_order_item.qty), revenue)
		.where(is_webshop_order(sales_order))
		.groupby(configurator.item_template)
		.orderby(revenue, order=Order.desc)
		.limit(cint(limit) or TOP_PRODUCTS_LIMIT)
		.run()
	)
	currency = get_reporting_currency()
	if not rows:
		return {"products": [], "currency": currency}

	templates = [row[0] for row in rows]
	items_by_name = {
		row.name: row
		for row in frappe.get_all(
			"Item", filters={"name": ["in", templates]}, fields=["name", "item_name", "image"]
		)
	}

	configurators = frappe.get_all(
		"Style Attribute Configurator",
		filters={"item_template": ["in", templates]},
		fields=["name", "item_template"],
	)
	template_by_configurator = {row.name: row.item_template for row in configurators}
	template_variants = (
		frappe.get_all(
			"Style Attribute Variant",
			filters={"configurator": ["in", list(template_by_configurator)]},
			fields=["name", "configurator"],
		)
		if configurators
		else []
	)
	template_by_variant = {
		row.name: template_by_configurator.get(row.configurator) for row in template_variants
	}
	sizes = (
		frappe.get_all(
			"Color Size Item",
			filters={"parent": ["in", list(template_by_variant)], "parenttype": "Style Attribute Variant"},
			fields=["parent", "item_code"],
		)
		if template_by_variant
		else []
	)
	item_codes_by_template = {}
	for row in sizes:
		template = template_by_variant.get(row.parent)
		if template and row.item_code:
			item_codes_by_template.setdefault(template, []).append(row.item_code)
	all_item_codes = [code for codes in item_codes_by_template.values() for code in codes]
	stock_by_item_code = get_ecommerce_stock(all_item_codes)

	return {
		"products": [
			{
				"name": row[0],
				"title": items_by_name.get(row[0], {}).get("item_name") or row[0],
				"image": items_by_name.get(row[0], {}).get("image"),
				"units": cint(row[1]),
				"revenue": flt(row[2]),
				"stock": sum(
					stock_by_item_code.get(code, 0) for code in item_codes_by_template.get(row[0], [])
				),
			}
			for row in rows
		],
		"currency": currency,
	}


def get_item_templates_by_item_code(item_codes):
	"""One batched hop from a sellable size (Sales Order Item.item_code / Bin.item_code) up to its product
	template - the same size -> variant -> configurator join get_top_products does inline."""
	if not item_codes:
		return {}

	color_size_item = frappe.qb.DocType("Color Size Item")
	variant = frappe.qb.DocType("Style Attribute Variant")
	configurator = frappe.qb.DocType("Style Attribute Configurator")
	rows = (
		frappe.qb.from_(color_size_item)
		.join(variant)
		.on(variant.name == color_size_item.parent)
		.join(configurator)
		.on(configurator.name == variant.configurator)
		.select(color_size_item.item_code, configurator.item_template)
		.where(color_size_item.parenttype == "Style Attribute Variant")
		.where(color_size_item.item_code.isin(item_codes))
		.run()
	)
	return {row[0]: row[1] for row in rows}


def get_publish_blockers(images, sizes):
	blockers = []
	if not images:
		blockers.append(_("Add at least one image"))
	if not sizes:
		blockers.append(_("Add at least one size"))
	return blockers


@frappe.whitelist()
def get_collections(search_text: str | None = None):
	"""The collections a product can be filed under, for the create form's picker."""
	frappe.has_permission("Item Group", ptype="read", throw=True)

	filters = {}
	if search_text:
		filters["name"] = ("like", f"%{cstr(search_text)}%")

	# ponytail: first 100 matches only, paginate the picker if a store keeps more collections
	# than a searched dropdown can show
	return frappe.get_all("Item Group", filters=filters, order_by="name", pluck="name", limit=100)


@frappe.whitelist()
def list_collections(search: str | None = None, start: int = 0, page_length: int = PAGE_LENGTH):
	"""The Collections screen: one row per collection, with a real (not derived) product count. Collections
	are the leaf Item Groups; structural parents are excluded by nested-set shape (lft/rgt), not by name."""
	frappe.has_permission("Item Group", ptype="read", throw=True)

	start = cint(start)
	page_length = cint(page_length) or PAGE_LENGTH

	item_group = frappe.qb.DocType("Item Group")
	filters = item_group.rgt == item_group.lft + 1
	if search:
		filters = filters & item_group.name.like(f"%{cstr(search)}%")

	total = (frappe.qb.from_(item_group).select(Count(item_group.name)).where(filters)).run()[0][0]

	names = (
		frappe.qb.from_(item_group)
		.select(item_group.name)
		.where(filters)
		.orderby(item_group.name)
		.offset(start)
		.limit(page_length)
	).run(pluck=True)

	counts = get_collection_product_counts(names)

	return {
		"collections": [{"name": name, "count": counts.get(name, 0)} for name in names],
		"total": total,
	}


def get_collection_product_counts(collection_names):
	"""How many items sit in each collection, in one grouped query regardless of how many collections."""
	if not collection_names:
		return {}

	item = frappe.qb.DocType("Item")
	rows = (
		frappe.qb.from_(item)
		.select(item.item_group, Count(item.name).as_("count"))
		.where(item.item_group.isin(collection_names))
		.groupby(item.item_group)
	).run(as_dict=True)

	return {row.item_group: row.count for row in rows}


@frappe.whitelist(methods=["POST"])
def create_collection(title: str):
	"""A new collection, filed as a leaf under the same parent every other collection already uses."""
	frappe.has_permission("Item Group", ptype="create", throw=True)

	title = cstr(title).strip()
	if not title:
		frappe.throw(_("Enter a collection name"))
	if frappe.db.exists("Item Group", title):
		frappe.throw(_("Collection {0} already exists.").format(title))

	item_group = frappe.qb.DocType("Item Group")
	parent = (
		frappe.qb.from_(item_group)
		.select(item_group.parent_item_group)
		.where(item_group.rgt == item_group.lft + 1)
		.limit(1)
	).run()
	# A brand-new store with zero collections yet has no leaf to copy a parent from — file
	# straight under the tree root instead.
	parent_item_group = (
		parent[0][0] if parent else frappe.db.get_value("Item Group", {"parent_item_group": ""})
	)

	collection = frappe.new_doc("Item Group")
	collection.item_group_name = title
	collection.parent_item_group = parent_item_group
	# custom_displayname is a site customization (mandatory, shopper-facing) — every existing
	# collection just mirrors its name into it, so a new one does too.
	collection.custom_displayname = title
	collection.insert()

	return {"name": collection.name}


@frappe.whitelist(methods=["POST"])
def add_products_to_collection(item_templates: list | str, collection: str):
	"""File a selection of products under one collection, options included.
	The options are re-filed too - see save_variant_collections."""
	frappe.has_permission("Item", ptype="write", throw=True)

	item_templates = frappe.parse_json(item_templates)
	if not isinstance(item_templates, list) or not item_templates:
		frappe.throw(_("Select at least one product."))
	if len(item_templates) > BULK_PRODUCT_LIMIT:
		frappe.throw(_("Add at most {0} products to a collection at a time.").format(BULK_PRODUCT_LIMIT))

	item_group = get_collection(collection)

	updated = []
	for item_template in item_templates:
		# ponytail: one save per product so Item validation runs, move to a background job if a
		# store ever needs to file more than BULK_PRODUCT_LIMIT products in one go
		item = frappe.get_doc("Item", item_template)
		item.check_permission("write")
		item.item_group = item_group
		item.save()
		updated.append(item.name)

	save_variant_collections(updated)

	return {"updated": updated, "collection": item_group}


@frappe.whitelist()
def get_attribute_values(attribute: str):
	"""The colours and sizes this store already uses, so the create form suggests instead of retypes."""
	frappe.has_permission("Item Attribute", doc=attribute, ptype="read", throw=True)

	return frappe.get_all(
		"Item Attribute Value",
		filters={"parent": attribute, "parenttype": "Item Attribute"},
		order_by="idx asc",
		pluck="attribute_value",
	)


@frappe.whitelist()
def get_attributes():
	"""The Attributes screen: every Item Attribute with its values and a live usage count.
	Two queries however many attributes exist - one for value rows, one grouped for usage; never per attribute."""
	frappe.has_permission("Item Attribute", ptype="read", throw=True)

	attribute_names = frappe.get_all("Item Attribute", pluck="name", order_by="name asc")
	if not attribute_names:
		return []

	value_rows = frappe.get_all(
		"Item Attribute Value",
		filters={"parent": ["in", attribute_names], "parenttype": "Item Attribute"},
		fields=["parent", "attribute_value", "abbr"],
		order_by="parent asc, idx asc",
	)
	values_by_attribute = {}
	for row in value_rows:
		values_by_attribute.setdefault(row.parent, []).append(row.attribute_value)

	usage_by_attribute = get_attribute_usage_counts(attribute_names)

	return [
		{
			"name": name,
			"values": values_by_attribute.get(name, []),
			"used_by": usage_by_attribute.get(name, 0),
		}
		for name in attribute_names
	]


def get_attribute_usage_counts(attribute_names):
	"""Distinct product templates using each attribute, in one grouped query — not one per attribute."""
	item_variant_attribute = frappe.qb.DocType("Item Variant Attribute")
	item = frappe.qb.DocType("Item")

	rows = (
		frappe.qb.from_(item_variant_attribute)
		.join(item)
		.on(item.name == item_variant_attribute.parent)
		.select(item_variant_attribute.attribute, Count(item.variant_of).distinct().as_("used_by"))
		.where(item_variant_attribute.attribute.isin(attribute_names))
		.where(item.variant_of.isnotnull())
		.groupby(item_variant_attribute.attribute)
	).run(as_dict=True)

	return {row.attribute: row.used_by for row in rows}


def check_abbreviations_are_distinct(attribute_doc, abbreviation: str, skip_row_name: str | None = None):
	"""Refuse a colliding abbreviation up front: two values sharing one generate the same item code, and the
	variant insert dies with DuplicateEntryError. Case-insensitive, as Item Attribute.validate_duplication is."""
	taken = {
		cstr(row.abbr).casefold() for row in attribute_doc.item_attribute_values if row.name != skip_row_name
	}
	if cstr(abbreviation).casefold() in taken:
		frappe.throw(
			_("Abbreviation {0} is already used by another value on {1}.").format(
				abbreviation, attribute_doc.name
			)
		)


@frappe.whitelist(methods=["POST"])
def create_attribute(name: str, values: list | str | None = None):
	"""A new attribute, with as many starting values as the owner typed, comma separated.
	Abbreviations are always auto-generated here (make_unique_abbreviation), so a collision cannot occur."""
	frappe.has_permission("Item Attribute", ptype="create", throw=True)

	name = cstr(name).strip()
	if not name:
		frappe.throw(_("Enter an attribute name"))

	attribute = frappe.new_doc("Item Attribute")
	attribute.attribute_name = name

	taken = set()
	seen = set()
	for raw_value in cstr(values or "").split(","):
		value = raw_value.strip()
		if not value or value.casefold() in seen:
			continue
		seen.add(value.casefold())
		abbreviation = make_unique_abbreviation(value, taken)
		taken.add(abbreviation.casefold())
		attribute.append("item_attribute_values", {"attribute_value": value, "abbr": abbreviation})

	attribute.insert()

	return {"name": attribute.name}


@frappe.whitelist(methods=["POST"])
def add_attribute_value(attribute: str, value: str, abbreviation: str | None = None):
	"""Add one value to an existing attribute. An explicit abbreviation is refused on collision (see
	check_abbreviations_are_distinct); omit it and one is auto-generated, which cannot collide."""
	frappe.has_permission("Item Attribute", doc=attribute, ptype="write", throw=True)

	value = cstr(value).strip()
	if not value:
		frappe.throw(_("Enter a value"))

	attribute_doc = frappe.get_doc("Item Attribute", attribute)
	if any(row.attribute_value.casefold() == value.casefold() for row in attribute_doc.item_attribute_values):
		frappe.throw(_("{0} already has a value called {1}.").format(attribute, value))

	if abbreviation:
		abbreviation = cstr(abbreviation).strip().upper()
		check_abbreviations_are_distinct(attribute_doc, abbreviation)
	else:
		taken = {cstr(row.abbr).casefold() for row in attribute_doc.item_attribute_values}
		abbreviation = make_unique_abbreviation(value, taken)

	attribute_doc.append("item_attribute_values", {"attribute_value": value, "abbr": abbreviation})
	attribute_doc.save()

	return {
		"name": attribute_doc.name,
		"values": [row.attribute_value for row in attribute_doc.item_attribute_values],
	}


# A product that sells as a single item still needs both variant axes present: Color Size Item.size is
# reqd, checkout drops a line whose Item has no "Size" attribute row, and empty sizes unpublish a variant.
SIZE_ATTRIBUTE = "Size"
DEFAULT_OPTION_ATTRIBUTE = "Title"
DEFAULT_OPTION_VALUE = "Standard"
DEFAULT_SIZE_VALUE = "One Size"


@frappe.whitelist(methods=["POST"])
def create_product(
	title: str,
	collection: str,
	option_attribute: str | None = None,
	size_attribute: str | None = None,
	option_sizes: list | str | None = None,
	price: float | str | None = None,
	sale_price: float | str | None = None,
	option_abbreviations: dict | str | None = None,
	size_abbreviations: dict | str | None = None,
):
	"""Create a sellable product; company, warehouse, price list, UOM and naming series come from Lifestyle
	Settings. Both axes are always written whatever the caller omits - see the note above SIZE_ATTRIBUTE."""
	frappe.has_permission("Item", ptype="create", throw=True)

	title = cstr(title).strip()
	if not title:
		frappe.throw(_("Enter a product title"))

	# An Item is named after its title (autoname "field:item_code"), so a reserved "New Item" prefix and a
	# repeat title both surface from inside insert() as messages a shop owner cannot act on.
	if title.startswith("New Item"):
		frappe.throw(
			_(
				'A product title cannot start with "New Item" - Frappe reserves that wording for documents it has not saved yet. Try another title.'
			)
		)

	if frappe.db.exists("Item", title):
		frappe.throw(_("A product called {0} already exists. Give this one a different title.").format(title))

	# A book has neither a colour nor a size, so both axes fall back to a single hidden value - an owner who
	# named no options hangs on the fallback axis, not on whichever attribute the form had selected.
	option_rows = frappe.parse_json(option_sizes) if isinstance(option_sizes, str) else (option_sizes or [])
	option_attribute = (cstr(option_attribute).strip() if option_rows else "") or ensure_attribute_exists(
		DEFAULT_OPTION_ATTRIBUTE, DEFAULT_OPTION_VALUE, "STD"
	)
	size_attribute = cstr(size_attribute).strip() or SIZE_ATTRIBUTE
	# A store that has never sold a garment has no "Size" attribute, and the hidden size still
	# needs one to live on — otherwise a book is uncreatable on a fresh site.
	ensure_attribute_exists(SIZE_ATTRIBUTE, DEFAULT_SIZE_VALUE, "OS")

	# generate_variants() lowercases the attribute name into a "Color Size Item" fieldname, so any other
	# spelling fails deep inside variant generation with "Value missing for: Size".
	if cstr(size_attribute) != "Size":
		frappe.throw(
			_('The size option must use the attribute named exactly "Size" — {0} will not work.').format(
				size_attribute
			)
		)

	option_sizes = parse_option_sizes(option_sizes)

	if not frappe.db.exists("Item Group", collection):
		frappe.throw(_("Collection {0} does not exist. Create it first.").format(collection))

	option_sizes = resolve_option_sizes(
		option_attribute,
		size_attribute,
		option_sizes,
		option_abbreviations=frappe.parse_json(option_abbreviations)
		if isinstance(option_abbreviations, str)
		else option_abbreviations,
		size_abbreviations=frappe.parse_json(size_abbreviations)
		if isinstance(size_abbreviations, str)
		else size_abbreviations,
	)

	item_template = frappe.new_doc("Item")
	item_template.item_code = title
	item_template.item_name = title
	item_template.item_group = collection
	item_template.stock_uom = get_default_stock_uom()
	item_template.is_stock_item = 1
	item_template.has_variants = 1
	item_template.variant_based_on = "Item Attribute"
	item_template.append("attributes", {"attribute": option_attribute})
	item_template.append("attributes", {"attribute": size_attribute})
	item_template.insert()

	for option, sizes in option_sizes:
		for size in sizes:
			size_item = create_variant(item_template.name, {option_attribute: option, size_attribute: size})
			size_item.insert()

	configurator = frappe.new_doc("Style Attribute Configurator")
	configurator.item_template = item_template.name
	configurator.item_attribute = option_attribute
	configurator.insert()
	# after_insert only generates variants when the setting says so, and a product here needs them.
	if not frappe.db.exists("Style Attribute Variant", {"configurator": configurator.name}):
		configurator.generate_variants()

	if flt(price) > 0 or flt(sale_price) > 0:
		set_variant_prices(item_template.name, default_rate=price, sale_rate=sale_price)

	return {"name": item_template.name}


def parse_option_sizes(option_sizes: list | str):
	"""ERPNext compares attribute values case-insensitively, so two spellings of one colour
	are merged here or the second create_variant collides."""
	rows = frappe.parse_json(option_sizes) or []
	if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
		frappe.throw(_("Colours and sizes could not be read"))

	merged = {}
	for row in rows:
		option = cstr(row.get("option")).strip()
		if not option:
			continue

		sizes = merged.setdefault(option.casefold(), (option, []))[1]
		taken = {size.casefold() for size in sizes}
		for value in row.get("sizes") or []:
			size = cstr(value).strip()
			if size and size.casefold() not in taken:
				sizes.append(size)
				taken.add(size.casefold())

	if not merged:
		merged = {DEFAULT_OPTION_VALUE.casefold(): (DEFAULT_OPTION_VALUE, [])}

	# Every option sizeless is a book. Some sized and some not is a half-filled form, and still an
	# error - silently stamping "One Size" on the row the owner merely forgot would hide it.
	sizeless = [option for option, sizes in merged.values() if not sizes]
	if sizeless and len(sizeless) < len(merged):
		frappe.throw(_("Pick at least one size for {0}").format(sizeless[0]))

	for _option, sizes in merged.values():
		if not sizes:
			sizes.append(DEFAULT_SIZE_VALUE)

	return list(merged.values())


def resolve_option_sizes(
	option_attribute: str,
	size_attribute: str,
	option_sizes: list,
	option_abbreviations: dict | None = None,
	size_abbreviations: dict | None = None,
):
	"""Swap what the owner typed for the spelling the Item Attribute already holds."""
	typed_options = [option for option, _sizes in option_sizes]
	typed_sizes = []
	taken = set()
	for _option, sizes in option_sizes:
		for size in sizes:
			if size.casefold() not in taken:
				typed_sizes.append(size)
				taken.add(size.casefold())

	canonical_options = add_missing_attribute_values(option_attribute, typed_options, option_abbreviations)
	canonical_sizes = add_missing_attribute_values(size_attribute, typed_sizes, size_abbreviations)
	size_by_typed = dict(zip(typed_sizes, canonical_sizes, strict=True))

	return [
		(canonical_options[index], [size_by_typed[size] for size in sizes])
		for index, (_option, sizes) in enumerate(option_sizes)
	]


def add_missing_attribute_values(attribute: str, values: list, abbreviations: dict | None = None):
	"""Let the owner type a new colour without visiting the Item Attribute form. ERPNext compares attribute
	values case-insensitively, so "red" beside "Red" appends a duplicate."""
	abbreviations = abbreviations or {}
	attribute_doc = frappe.get_doc("Item Attribute", attribute)
	canonical_by_key = {
		cstr(row.attribute_value).casefold(): cstr(row.attribute_value)
		for row in attribute_doc.item_attribute_values
	}

	resolved = []
	taken = {cstr(row.abbr).casefold() for row in attribute_doc.item_attribute_values}
	added = False
	for value in values:
		canonical = canonical_by_key.get(cstr(value).casefold())
		if canonical:
			resolved.append(canonical)
			continue

		explicit_abbreviation = abbreviations.get(value)
		if explicit_abbreviation:
			abbreviation = cstr(explicit_abbreviation).strip().upper()
			check_abbreviations_are_distinct(attribute_doc, abbreviation)
		else:
			abbreviation = make_unique_abbreviation(value, taken)

		taken.add(abbreviation.casefold())
		canonical_by_key[cstr(value).casefold()] = value
		attribute_doc.append("item_attribute_values", {"attribute_value": value, "abbr": abbreviation})
		resolved.append(value)
		added = True

	if added:
		attribute_doc.save()

	return resolved


def ensure_attribute_exists(attribute_name: str, seed_value: str, abbreviation: str):
	"""An axis a product falls back to, created on first use. generate_variants() skips a product whose
	configurator axis is empty, leaving it with no storefront page at all."""
	if not frappe.db.exists("Item Attribute", attribute_name):
		attribute_doc = frappe.new_doc("Item Attribute")
		attribute_doc.attribute_name = attribute_name
		attribute_doc.append("item_attribute_values", {"attribute_value": seed_value, "abbr": abbreviation})
		attribute_doc.insert()

	return attribute_name


def make_unique_abbreviation(value: str, taken: set):
	base = "".join(part[0] for part in cstr(value).split() if part).upper() or "X"
	if base.casefold() not in taken:
		return base

	suffix = 2
	while f"{base}{suffix}".casefold() in taken:
		suffix += 1
	return f"{base}{suffix}"


def get_default_stock_uom():
	return frappe.db.get_single_value("Stock Settings", "stock_uom") or "Nos"


@frappe.whitelist(methods=["POST"])
def update_product(
	item_template: str,
	title: str | None = None,
	collection: str | None = None,
	description: str | None = None,
	disabled: int | str | None = None,
):
	frappe.has_permission("Item", doc=item_template, ptype="write", throw=True)

	item = frappe.get_doc("Item", item_template)
	if title is not None:
		# Item.validate backfills a blank item_name from item_code, so a cleared title silently survives.
		title = cstr(title).strip()
		if not title:
			frappe.throw(_("Title is required."))
		item.item_name = title
	if collection is not None:
		item.item_group = get_collection(collection)
	if description is not None:
		item.description = description
	if disabled is not None:
		item.disabled = cint(disabled)
	item.save()

	if collection is not None:
		save_variant_collections([item.name])

	return {"name": item.name}


def check_product_has_no_history(title: str, item_codes: list) -> None:
	"""Refuse a product any document still refers to, one query per doctype however many sizes it has.
	A cancelled order still carries its lines, so docstatus is deliberately not filtered on."""
	messages = {
		"Sales Order Item": _("{0} has been ordered before, so it cannot be deleted."),
		"Delivery Note Item": _("{0} has been shipped before, so it cannot be deleted."),
		"Sales Invoice Item": _("{0} has been invoiced before, so it cannot be deleted."),
		"Packing Slip Item": _("{0} is on a packing slip, so it cannot be deleted."),
		"Quotation Item": _("{0} has been quoted before, so it cannot be deleted."),
		"Material Request Item": _("{0} is on a material request, so it cannot be deleted."),
		"Stock Ledger Entry": _("{0} has stock movement against it, so it cannot be deleted."),
		"Storefront Analytics Event": _("{0} has been viewed by shoppers, so it cannot be deleted."),
	}
	for doctype in HISTORY_BLOCKERS:
		for item_code_chunk in create_batch(item_codes, IN_CLAUSE_CHUNK_SIZE):
			if frappe.get_all(doctype, filters={"item_code": ["in", item_code_chunk]}, limit=1):
				frappe.throw(
					f"{messages[doctype].format(title)} {_('Archive it instead.')}",
					title=_("This product has a history"),
				)


def check_product_chain_is_deletable(chain: dict, item_template: str | int) -> None:
	"""Ask the framework whether every document in the chain may go, before any of them does.
	frappe.delete_doc deletes attachments before it checks links, and the rollback restores SQL, not disk."""
	from frappe.model.delete_doc import get_linked_docs, raise_link_exists_exception

	documents = [
		*(("Style Attribute Variant", name) for name in chain["variants"]),
		*(("Style Attribute Configurator", name) for name in chain["configurators"]),
		*(("Item", item_code) for item_code in chain["item_codes"]),
		("Item", cstr(item_template)),
	]
	doomed = {(doctype, cstr(name)) for doctype, name in documents}

	for doctype, name in documents:
		# ponytail: one load per document because the framework's link reader takes a document, and
		# delete_doc loads each of them again anyway; batch it if a product ever carries enough
		# options that the double load shows up.
		document = frappe.get_doc(doctype, name)
		for link in get_linked_docs(document):
			reference = (link["reference_doctype"], cstr(link["reference_docname"]))
			if reference in doomed or link["reference_doctype"] in CLEARED_ON_ITEM_TRASH:
				continue
			raise_link_exists_exception(document, link["reference_doctype"], link["reference_docname"])


@frappe.whitelist(methods=["POST"])
def delete_product(item_template: str | int):
	"""Remove a product nothing refers to, options and sellable sizes included.
	A product with any history stays - see check_product_has_no_history."""
	frappe.has_permission("Item", doc=item_template, ptype="delete", throw=True)

	title = frappe.db.get_value("Item", item_template, "item_name")
	if title is None:
		frappe.throw(_("Product {0} not found").format(item_template))

	chain = get_product_chain(item_template)
	check_product_has_no_history(title, [cstr(item_template), *chain["item_codes"]])
	check_product_chain_is_deletable(chain, item_template)

	# Options first, then their configurators, then the sellable items, then the product itself -
	# each link is deleted before the row it points at.
	for variant_name in chain["variants"]:
		frappe.delete_doc("Style Attribute Variant", variant_name)
	for configurator in chain["configurators"]:
		frappe.delete_doc("Style Attribute Configurator", configurator)
	for item_code in chain["item_codes"]:
		frappe.delete_doc("Item", item_code)
	frappe.delete_doc("Item", item_template)

	return {"deleted": item_template}


@frappe.whitelist(methods=["POST"])
def set_restock_level(item_template: str | int, level: int | str):
	"""The stock level this product reads as low at, written to Item.safety_stock on every size.
	Deliberately not ERPNext's reorder/auto_indent - nothing here raises a purchase."""
	frappe.has_permission("Item", doc=item_template, ptype="write", throw=True)

	level = cint(level)
	if level < 0:
		frappe.throw(_("A restock level cannot be negative."))

	item_codes = get_product_chain(item_template)["item_codes"]
	if not item_codes:
		frappe.throw(_("This product has no sizes to watch yet."))

	frappe.db.set_value("Item", {"name": ["in", item_codes]}, "safety_stock", level)

	return {"item_codes": item_codes, "level": level}


@frappe.whitelist(methods=["POST"])
def set_variant_published(style_attribute_variant: str, publish: int | str):
	"""Publish or unpublish one option.

	The variant controller refuses to publish without images and sizes.
	"""
	variant = frappe.get_doc("Style Attribute Variant", style_attribute_variant)
	variant.check_permission("write")

	publish = cint(publish)
	if publish:
		blockers = get_publish_blockers(variant.images, variant.sizes)
		if blockers:
			frappe.throw(_("Cannot publish yet: {0}").format(", ".join(blockers)))

	variant.is_published = publish
	variant.save()

	return {"name": variant.name, "is_published": bool(variant.is_published)}


@frappe.whitelist(methods=["POST"])
def add_product_images(style_attribute_variant: str, file_urls: list | str):
	"""Attach already-uploaded files to an option, then report what still blocks publishing."""
	variant = frappe.get_doc("Style Attribute Variant", style_attribute_variant)
	variant.add_images(file_urls)
	variant.reload()

	return {
		"name": variant.name,
		"images": [row.image for row in variant.images],
		"blockers": get_publish_blockers(variant.images, variant.sizes),
	}


@frappe.whitelist(methods=["POST"])
def remove_product_image(style_attribute_variant: str, file_url: str):
	variant = frappe.get_doc("Style Attribute Variant", style_attribute_variant)
	variant.remove_image(file_url)
	variant.reload()

	return {
		"name": variant.name,
		"images": [row.image for row in variant.images],
		"blockers": get_publish_blockers(variant.images, variant.sizes),
	}


@frappe.whitelist(methods=["POST"])
def save_product_prices(style_attribute_variant: str, size_prices: list | str):
	"""Edit the per-size default and sale prices of one option."""
	variant = frappe.get_doc("Style Attribute Variant", style_attribute_variant)
	return variant.save_size_prices(size_prices)


@frappe.whitelist(methods=["POST"])
def set_variant_price(
	style_attribute_variant: str,
	default_rate: float | str | None = None,
	sale_rate: float | str | None = None,
):
	"""Reprice every size under one option in a single pass - the bulk form of save_size_prices, built on
	the same set_variant_prices() the create-product flow uses."""
	# set_variant_prices() reads a non-positive rate as "leave that price list alone" - the sentinel the
	# create-product flow needs, so an editor asking for zero is refused here rather than silently dropped.
	for rate in (default_rate, sale_rate):
		if rate is not None and flt(rate) <= 0:
			frappe.throw(_("Enter a price above zero. A price cannot be removed once it is set."))

	variant = frappe.get_doc("Style Attribute Variant", style_attribute_variant)
	variant.check_permission("write")

	return set_variant_prices(
		variant.item_style,
		default_rate=default_rate,
		sale_rate=sale_rate,
		overwrite_existing=1,
		style_attribute_variant_list=[style_attribute_variant],
	)


@frappe.whitelist(methods=["POST"])
def receive_product_stock(
	style_attribute_variant: str, received_quantities: dict | str, valuation_rates: dict | str | None = None
):
	"""Take stock in against one option - a submitted Material Receipt into the shop warehouse."""
	variant = frappe.get_doc("Style Attribute Variant", style_attribute_variant)
	return {"stock_entry": variant.receive_stock(received_quantities, valuation_rates)}


@frappe.whitelist(methods=["POST"])
def set_product_published(item_template: str, publish: int | str):
	"""Publish or unpublish every option of a product in one go.

	Options that are not ready are skipped rather than failing the whole request, and come back named.
	"""
	frappe.has_permission("Item", doc=item_template, ptype="write", throw=True)

	publish = cint(publish)
	configurators = frappe.get_all(
		"Style Attribute Configurator", filters={"item_template": item_template}, pluck="name"
	)
	if not configurators:
		return {"updated": [], "skipped": []}

	variants = frappe.get_all(
		"Style Attribute Variant",
		filters={"configurator": ["in", configurators]},
		fields=["name", "attribute_value", "display_name"],
	)
	variant_names = [row.name for row in variants]

	# Two queries for the whole set; loading each variant to count images and sizes is a read per row.
	ready = get_ready_variant_names(variant_names) if publish else set(variant_names)

	updated = []
	skipped = []
	for row in variants:
		label = row.attribute_value or row.display_name
		if row.name not in ready:
			skipped.append(label)
			continue

		# ponytail: one save per option so validation and route generation still run,
		# move to a background job if a product ever carries more than a few dozen options
		variant = frappe.get_doc("Style Attribute Variant", row.name)
		variant.is_published = publish
		variant.save()
		updated.append(label)

	return {"updated": updated, "skipped": skipped}


def get_ready_variant_names(variant_names):
	"""The variants that carry both an image and a size, so they are allowed to go live."""
	if not variant_names:
		return set()

	with_images = {
		row.parent
		for row in frappe.get_all(
			"Website Slideshow Item",
			filters={"parent": ["in", variant_names], "parenttype": "Style Attribute Variant"},
			fields=["parent"],
		)
	}
	with_sizes = {
		row.parent
		for row in frappe.get_all(
			"Color Size Item",
			filters={"parent": ["in", variant_names], "parenttype": "Style Attribute Variant"},
			fields=["parent"],
		)
	}
	return with_images & with_sizes


def get_unpublishable_options(limit: int = 5):
	"""Options that cannot go live yet, with the reason, across the whole catalogue.
	`limit=0` returns every one, so a caller showing a preview can still count the rest in one pass."""
	variants = frappe.get_all(
		"Style Attribute Variant",
		filters={"is_published": 0},
		fields=["name", "configurator", "attribute_value", "display_name"],
		order_by="modified desc",
	)
	if not variants:
		return []

	variant_names = [row.name for row in variants]
	sized_variants = {
		row.parent
		for row in frappe.get_all(
			"Color Size Item",
			filters={"parent": ["in", variant_names], "parenttype": "Style Attribute Variant"},
			fields=["parent"],
		)
	}
	imaged_variants = {
		row.parent
		for row in frappe.get_all(
			"Website Slideshow Item",
			filters={"parent": ["in", variant_names], "parenttype": "Style Attribute Variant"},
			fields=["parent"],
		)
	}

	templates_by_configurator = {
		row.name: row.item_template
		for row in frappe.get_all(
			"Style Attribute Configurator",
			filters={"name": ["in", list({row.configurator for row in variants if row.configurator})]},
			fields=["name", "item_template"],
		)
	}
	titles = {
		row.name: row.item_name
		for row in frappe.get_all(
			"Item",
			filters={"name": ["in", list(set(templates_by_configurator.values()))]},
			fields=["name", "item_name"],
		)
	}

	blocked = []
	for row in variants:
		# The blocker rule reads presence, not content, so membership sets stand in for the lists.
		blockers = get_publish_blockers(
			[1] if row.name in imaged_variants else [], [1] if row.name in sized_variants else []
		)
		if not blockers:
			continue

		template = templates_by_configurator.get(row.configurator)
		if not template:
			# An option whose configurator or template is gone has no product screen to link to.
			continue

		blocked.append(
			{
				"variant": row.name,
				"product": template,
				"title": titles.get(template) or template,
				"option": row.attribute_value or row.display_name,
				"blockers": blockers,
			}
		)
		if cint(limit) and len(blocked) >= cint(limit):
			break

	return blocked
