# Copyright (c) 2026, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.data import cint, cstr, flt

PAGE_LENGTH = 50
LOW_STOCK_THRESHOLD = 5


@frappe.whitelist()
def get_inventory(
	availability: str | None = None, search: str | None = None, start: int = 0, page_length: int = PAGE_LENGTH
):
	"""Every sellable size and what is left of it."""
	frappe.has_permission("Item", ptype="read", throw=True)

	# Imported here rather than at module level: catalog.py has no import back to inventory.py
	# today, but keeping the cycle-risk local matches the same guard catalog.get_products uses.
	from ls_shop.api.admin.catalog import get_size_stock

	variants = frappe.get_all(
		"Style Attribute Variant",
		fields=["name", "attribute_value", "display_name", "item_style", "is_published"],
	)
	if not variants:
		return {"rows": [], "total": 0, "low_stock_threshold": LOW_STOCK_THRESHOLD}

	variant_by_name = {row.name: row for row in variants}
	sizes = frappe.get_all(
		"Color Size Item",
		filters={"parent": ["in", list(variant_by_name)], "parenttype": "Style Attribute Variant"},
		fields=["parent", "size", "item_code"],
	)
	item_codes = [row.item_code for row in sizes if row.item_code]
	if not item_codes:
		return {"rows": [], "total": 0, "low_stock_threshold": LOW_STOCK_THRESHOLD}

	titles = {
		row.name: row.item_name
		for row in frappe.get_all(
			"Item",
			filters={"name": ["in", list({row.item_style for row in variants if row.item_style})]},
			fields=["name", "item_name"],
		)
	}
	# get_size_stock (catalog.py) already reads Bin actual_qty + reserved_qty in one batched
	# query - reused rather than re-querying Bin a second way for the same numbers.
	stock_by_item_code = get_size_stock(item_codes)
	# Item.safety_stock is the per-product level set from the product screen (catalog.set_restock_level);
	# where a size carries one it decides what "Low" means for that row instead of the store default.
	low_level_by_item_code = {
		cstr(row.name): cint(row.safety_stock)
		for row in frappe.get_all(
			"Item", filters={"name": ["in", item_codes]}, fields=["name", "safety_stock"]
		)
	}

	# A dashboard-created variant never sets an Item.image, so the row falls back to its first
	# option photo - same source and batching catalog.get_products uses for the same reason.
	first_image_by_variant = {}
	for row in frappe.get_all(
		"Website Slideshow Item",
		filters={"parent": ["in", list(variant_by_name)], "parenttype": "Style Attribute Variant"},
		fields=["parent", "image"],
		order_by="idx asc",
	):
		first_image_by_variant.setdefault(row.parent, row.image)

	rows = []
	for size in sizes:
		if not size.item_code:
			continue

		variant = variant_by_name.get(size.parent)
		if not variant:
			continue

		stock = stock_by_item_code.get(cstr(size.item_code), {})
		quantity = stock.get("stock", 0)
		stored_level = low_level_by_item_code.get(cstr(size.item_code), 0)
		low_level = stored_level if stored_level > 0 else LOW_STOCK_THRESHOLD
		rows.append(
			{
				"item_code": size.item_code,
				"product": titles.get(variant.item_style) or variant.item_style,
				"product_name": variant.item_style,
				"option": variant.attribute_value or variant.display_name,
				"variant": variant.name,
				"size": size.size,
				"image": first_image_by_variant.get(variant.name),
				"stock": quantity,
				"committed": stock.get("committed", 0),
				"is_published": bool(variant.is_published),
				"low_stock_level": low_level,
				"availability": describe_availability(quantity, low_level),
			}
		)

	if availability in ("out", "low"):
		rows = [
			row for row in rows if row["availability"] == ("Out of stock" if availability == "out" else "Low")
		]
	if search:
		needle = cstr(search).casefold()
		rows = [
			row
			for row in rows
			if needle in cstr(row["product"]).casefold() or needle in cstr(row["item_code"]).casefold()
		]

	rows.sort(key=lambda row: (row["stock"], cstr(row["product"])))

	start = cint(start)
	page_length = cint(page_length) or PAGE_LENGTH
	return {
		"rows": rows[start : start + page_length],
		"total": len(rows),
		"low_stock_threshold": LOW_STOCK_THRESHOLD,
	}


def describe_availability(quantity, low_level: int = LOW_STOCK_THRESHOLD):
	if quantity <= 0:
		return "Out of stock"
	if quantity <= low_level:
		return "Low"
	return "In stock"


def get_ecommerce_warehouse():
	return frappe.get_cached_value("Lifestyle Settings", "Lifestyle Settings", "ecommerce_warehouse")


@frappe.whitelist(methods=["POST"])
def receive_stock(received_quantities: dict | str):
	"""Take stock in across any mix of products in one receipt."""
	received_quantities = frappe.parse_json(received_quantities)
	if not isinstance(received_quantities, dict):
		frappe.throw(_("received_quantities must map item codes to quantities"))

	wanted = {
		cstr(code): flt(quantity) for code, quantity in received_quantities.items() if flt(quantity) > 0
	}
	if not wanted:
		frappe.throw(_("Enter a quantity for at least one item"))

	rows = frappe.get_all(
		"Color Size Item",
		filters={"item_code": ["in", list(wanted)], "parenttype": "Style Attribute Variant"},
		fields=["item_code", "parent"],
	)
	quantities_by_variant = {}
	for row in rows:
		quantities_by_variant.setdefault(row.parent, {})[cstr(row.item_code)] = wanted[cstr(row.item_code)]

	unknown = sorted(set(wanted) - {cstr(row.item_code) for row in rows})
	if unknown:
		frappe.throw(_("Not a sellable size: {0}").format(", ".join(unknown)))

	stock_entries = []
	for variant_name, quantities in quantities_by_variant.items():
		variant = frappe.get_doc("Style Attribute Variant", variant_name)
		stock_entries.append(variant.receive_stock(quantities))

	return {"stock_entries": stock_entries}


# ls_shop keeps no adjustment-with-reason ledger of its own - a "set to X" or reason-coded
# adjustment op does not exist here, only the additive receive_stock() above. Rather than
# fabricate a ledger, get_stock_movements() below reads the real one ERPNext already keeps for
# every stock-affecting document (Stock Ledger Entry), scoped to the shop's own warehouse.
STOCK_ENTRY_REASON_LABELS = {
	"Material Receipt": "Received",
	"Material Issue": "Removed",
	"Material Transfer": "Transferred",
}
VOUCHER_TYPE_REASON_LABELS = {
	"Delivery Note": "Sold",
	"Sales Invoice": "Sold",
	"Stock Reconciliation": "Stock count",
	"Purchase Receipt": "Received",
}


@frappe.whitelist()
def get_stock_movements(start: int = 0, page_length: int = PAGE_LENGTH):
	"""Every stock movement against the shop's own warehouse, newest first. Read-only."""
	# Gated the same way get_inventory() is, on Item read - Stock Ledger Entry's own permission
	# is narrower than the role the dashboard runs under actually needs for this read.
	frappe.has_permission("Item", ptype="read", throw=True)

	warehouse = get_ecommerce_warehouse()
	if not warehouse:
		return {"rows": [], "total": 0}

	filters = {"warehouse": warehouse, "is_cancelled": 0}
	total = frappe.db.count("Stock Ledger Entry", filters)

	entries = frappe.get_all(
		"Stock Ledger Entry",
		filters=filters,
		fields=[
			"name",
			"posting_date",
			"posting_time",
			"item_code",
			"actual_qty",
			"voucher_type",
			"voucher_no",
			"owner",
		],
		order_by="posting_date desc, posting_time desc, creation desc",
		start=cint(start),
		page_length=cint(page_length) or PAGE_LENGTH,
	)
	if not entries:
		return {"rows": [], "total": total}

	item_codes = list({cstr(row.item_code) for row in entries})
	product_by_item_code = get_product_titles(item_codes)
	reason_by_voucher = get_movement_reasons(entries)
	full_name_by_user = get_user_full_names([row.owner for row in entries])

	rows = []
	for row in entries:
		item_code = cstr(row.item_code)
		rows.append(
			{
				"name": row.name,
				"date": row.posting_date,
				"sku": item_code,
				"product": product_by_item_code.get(item_code, item_code),
				"delta": flt(row.actual_qty),
				"reason": reason_by_voucher.get((row.voucher_type, row.voucher_no), row.voucher_type),
				"by": full_name_by_user.get(row.owner, row.owner),
			}
		)

	return {"rows": rows, "total": total}


def get_product_titles(item_codes):
	"""The parent product's title for a set of sizes - one batched hop through Color Size Item
	and Style Attribute Variant to Item.item_name, same join shape get_inventory() uses."""
	sizes = frappe.get_all(
		"Color Size Item",
		filters={"item_code": ["in", item_codes], "parenttype": "Style Attribute Variant"},
		fields=["item_code", "parent"],
	)
	if not sizes:
		return {}

	variants = frappe.get_all(
		"Style Attribute Variant",
		filters={"name": ["in", list({row.parent for row in sizes})]},
		fields=["name", "item_style"],
	)
	item_style_by_variant = {row.name: row.item_style for row in variants}

	item_styles = list({item_style for item_style in item_style_by_variant.values() if item_style})
	titles = (
		{
			row.name: row.item_name
			for row in frappe.get_all("Item", filters={"name": ["in", item_styles]}, fields=["name", "item_name"])
		}
		if item_styles
		else {}
	)

	product_by_item_code = {}
	for row in sizes:
		item_style = item_style_by_variant.get(row.parent)
		product_by_item_code[cstr(row.item_code)] = titles.get(item_style) or item_style
	return product_by_item_code


def get_movement_reasons(entries):
	"""A human reason per (voucher_type, voucher_no) - only Stock Entry needs a second lookup,
	to tell a receipt from an issue; every other voucher type reads off VOUCHER_TYPE_REASON_LABELS."""
	stock_entry_names = list({row.voucher_no for row in entries if row.voucher_type == "Stock Entry"})
	stock_entry_type_by_name = (
		{
			row.name: row.stock_entry_type
			for row in frappe.get_all(
				"Stock Entry", filters={"name": ["in", stock_entry_names]}, fields=["name", "stock_entry_type"]
			)
		}
		if stock_entry_names
		else {}
	)

	reasons = {}
	for row in entries:
		key = (row.voucher_type, row.voucher_no)
		if row.voucher_type == "Stock Entry":
			stock_entry_type = stock_entry_type_by_name.get(row.voucher_no)
			reasons[key] = STOCK_ENTRY_REASON_LABELS.get(stock_entry_type, stock_entry_type or row.voucher_type)
		else:
			reasons[key] = VOUCHER_TYPE_REASON_LABELS.get(row.voucher_type, row.voucher_type)
	return reasons


def get_user_full_names(owners):
	names = list({owner for owner in owners if owner})
	if not names:
		return {}
	return {
		row.name: row.full_name
		for row in frappe.get_all("User", filters={"name": ["in", names]}, fields=["name", "full_name"])
	}
