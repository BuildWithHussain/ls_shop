import re
from functools import lru_cache
from urllib.parse import quote

import frappe
from erpnext.selling.doctype.customer.customer import (
	get_nested_links as _get_nested_links,
)
from frappe.geo.country_info import get_all
from frappe.query_builder import Case, DocType
from frappe.query_builder.functions import Count, Min, Sum
from frappe.utils import add_days, create_batch, cstr, flt, get_datetime, now_datetime
from frappe.utils.data import strip_html
from pypika import Order

from commera.core import get_address_docs, get_party

# Ceiling for any IN (...) list this app sends to MariaDB/Postgres.
IN_CLAUSE_CHUNK_SIZE = 1000


def get_address_lines(address_display):
	"""ERPNext builds address_display as HTML; the dashboard renders plain text, so <br> tags leak."""
	if not address_display:
		return None

	lines = [
		strip_html(part).strip()
		for part in re.split(r"<br\s*/?>", cstr(address_display), flags=re.IGNORECASE)
	]
	return "\n".join(line for line in lines if line) or None


def validate_document_access(doctype: str, name: str):
	"""Return the document only if the session owns it, or holds read permission on it."""
	# Sales Order names are sequential, so the id in the payload is all that guards someone else's order.
	document = frappe.get_doc(doctype, name)
	if document.owner != frappe.session.user and not document.has_permission("read"):
		raise frappe.PermissionError
	return document


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


def get_product_list(filters=None, product_list=None, page=1, page_length=30, sort_by="default"):
	"""Storefront product grid: FTS-ranked when a rankable term is searched, frappe.qb otherwise."""
	from commera.search import query as search_query
	from commera.search.engine_cache import get_search_engine

	if product_list is not None or search_query.use_qb_fallback(filters):
		return get_product_list_qb(filters, product_list, page, page_length, sort_by)

	ranked_names = get_search_engine().search_products(filters, page, page_length, sort_by)
	if not ranked_names:
		return []

	# Hydrate through the qb select for one card shape, then restore rank: frappe.qb orders by name.
	cards_by_name = {
		card["name"]: card
		for card in get_product_list_qb(product_list=ranked_names, page_length=len(ranked_names))
	}
	return [cards_by_name[name] for name in ranked_names if name in cards_by_name]


def get_product_list_qb(filters=None, product_list=None, page=1, page_length=30, sort_by="default"):
	"""Retained frappe.qb product grid — browse, pinned lists, and the Arabic/short-term search fallback."""

	query = get_product_base_query(filters, product_list)
	style_attribute_variant = DocType("Style Attribute Variant")
	website_slideshow_item = DocType("Website Slideshow Item")
	color_size_item = DocType("Color Size Item")
	item_price_default = DocType("Item Price").as_("ip_default")
	item_price_sale = DocType("Item Price").as_("ip_sale")
	item = DocType("Item")
	has_custom_name_ar = frappe.db.has_column("Item", "custom_item_name_ar")

	discount_expr = (
		Case()
		.when(
			Min(item_price_default.price_list_rate) > 0,
			(
				(Min(item_price_default.price_list_rate) - Min(item_price_sale.price_list_rate))
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
			style_attribute_variant.attribute_value,
			style_attribute_variant.attribute_name.as_("color"),
			style_attribute_variant.item_group,
			style_attribute_variant.modified,
			item.brand,
			item.item_name,
			item.is_stock_item,
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
	return shape_product_cards(query.run(as_dict=True))


def shape_product_cards(cards):
	"""Give every product card the one storefront card shape, whichever grid built it."""
	from commera.search.record_builder import sizes_for_variants
	from commera.search.sqlite_product_search import SqliteProductSearch

	if not cards:
		return cards

	unsized = [card["name"] for card in cards if card.get("sizes") is None]
	sizes_by_variant = sizes_for_variants(unsized) if unsized else {}

	for card in cards:
		if card.get("sizes") is None:
			card["sizes"] = sizes_by_variant.get(card["name"], [])
		for column in SqliteProductSearch.PRODUCT_DETAIL_COLUMNS:
			if column != "doc_id":
				card.setdefault(column, None)
		# Mirrors record_builder.aggregate_prices so both grids agree on the price they filter and sort by.
		if card["effective_price"] is None:
			card["effective_price"] = (
				card["sale_price"] if card["sale_price"] is not None else (card["default_price"] or 0)
			)
		if card["has_discount"] is None:
			card["has_discount"] = 1 if flt(card["discount_percent"]) else 0
		# frappe.qb returns a datetime where the index holds a string, and the card is json.dumps'd into HTML.
		card["modified"] = cstr(card["modified"]) if card["modified"] else None
	return cards


def attach_live_prices(cards):
	"""Overlay the live Item Price onto index-hydrated cards."""
	# Item Price edits fire no Style Attribute Variant event, so the indexed price lags until the rebuild.
	from commera.search.record_builder import aggregate_prices, rates_by_item_code

	if not cards:
		return cards

	settings = frappe.get_cached_doc("Lifestyle Settings")
	item_codes = list(
		{size["item_code"] for card in cards for size in (card.get("sizes") or []) if size.get("item_code")}
	)
	default_rate, sale_rate, sale_upto = rates_by_item_code(
		item_codes, settings.default_price_list, settings.sale_price_list
	)

	for card in cards:
		codes = [size["item_code"] for size in (card.get("sizes") or []) if size.get("item_code")]
		card.update(aggregate_prices(codes, default_rate, sale_rate, sale_upto))
	return cards


def get_total_product_count(filters=None, product_list=None):
	"""Total products for the grid's pagination controls — from SQLite unless frappe.qb owns the grid."""
	from commera.search import query as search_query
	from commera.search.engine_cache import get_search_engine

	if product_list is None and not search_query.use_qb_fallback(filters):
		return get_search_engine().search_count(filters)
	return get_product_count_qb(filters, product_list)


def get_product_count_qb(filters=None, product_list=None):
	"""Retained frappe.qb total count — used under the frappe.qb fallback and for pinned product lists."""

	query = get_product_base_query(filters, product_list)
	style_attribute_variant = DocType("Style Attribute Variant")
	query = query.select(Count(style_attribute_variant.name).distinct().as_("total_count"))
	result = query.run(as_dict=True)
	return result[0]["total_count"] if result else 0


def get_product_base_query(filters=None, product_list=None):
	lifestyle_settings = frappe.get_cached_doc("Lifestyle Settings")
	default_price_list = lifestyle_settings.default_price_list
	sale_price_list = lifestyle_settings.sale_price_list
	style_attribute_variant = DocType("Style Attribute Variant")
	website_slideshow_item = DocType("Website Slideshow Item")
	color_size_item = DocType("Color Size Item")
	item_price_default = DocType("Item Price").as_("ip_default")
	item_price_sale = DocType("Item Price").as_("ip_sale")
	item = DocType("Item")

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
	if product_list:
		query = query.where(style_attribute_variant.name.isin(product_list))
	else:
		query = query.where(style_attribute_variant.is_published == 1)

	if filters:
		if filters.get("has_discount"):
			query = query.where(item_price_default.price_list_rate > item_price_sale.price_list_rate)
		if filters.get("subcategory"):
			query = query.where(style_attribute_variant.item_group.isin(filters["subcategory"]))
		if filters.get("colors"):
			query = query.where(style_attribute_variant.attribute_name.isin(filters["colors"]))
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
				search_condition |= style_attribute_variant.item_group.isin(child_categories)

			if search.lower().startswith("men"):
				exclusion_condition = (~style_attribute_variant.display_name.like("%women%")) & (
					~style_attribute_variant.item_group.like("%women%")
				)
				search_condition = search_condition & exclusion_condition

			query = query.where(search_condition)
	return query


def get_delivery_configuration():
	shoe_arena_settings = frappe.get_cached_doc("Lifestyle Settings")
	if not shoe_arena_settings.shipping_rule:
		return 0, 0
	shipping_rule = frappe.get_cached_doc("Shipping Rule", shoe_arena_settings.shipping_rule)
	if not shipping_rule or not shipping_rule.conditions:
		return 0, 0
	condition = shipping_rule.conditions[0]
	return condition.shipping_amount, condition.to_value


# The leading space is historical and live orders carry it: strip before comparing, never remove it.
COD_CHARGE_DESCRIPTION = " Cash on Delivery Charges"


def get_cod_configuration():
	shoe_arena_settings = frappe.get_cached_doc("Lifestyle Settings")
	return (
		shoe_arena_settings.cod_charge_applicable_below,
		shoe_arena_settings.cod_charge,
	)


def format_theme_css():
	# jinja's safe globals return documents as plain dicts, so controller methods are unreachable from templates
	return frappe.get_cached_doc("Lifestyle Settings", "Lifestyle Settings").generate_theme_css()


def get_currency_symbol():
	currency = frappe.get_cached_value("Global Defaults", "Global Defaults", "default_currency")
	# Riyal has no glyph in the fonts the themes ship, so SAR alone borrows the icon font.
	if currency == "SAR":
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
						f"Phone: {address.get('phone')}" if address.get("phone") else "",
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


def get_login_url_for_current_page() -> str:
	"""Login link that lands the shopper back on the page that refused them, query string intact."""
	# The login page reads `redirect-to` off its own query string: unencoded, it truncates at the first `&`.
	request = getattr(frappe.local, "request", None)
	# werkzeug always appends the separator to full_path, even with nothing after it.
	return_to = request.full_path.removesuffix("?") if request else "/"
	return f"/login?redirect-to={quote(return_to, safe='')}"


def get_current_page():
	query_params = frappe.form_dict
	page = int(query_params.get("page", "1"))
	return page


def can_return(order_name, return_period_days):
	"""Check if the order is still within the return period."""

	invoices = frappe.get_all("Sales Invoice", {"sales_order": order_name}, ["name", "creation"], limit=1)
	if not invoices:
		return False
	invoice_creation_date = invoices[0].creation
	creation = get_datetime(invoice_creation_date)
	return_deadline = add_days(creation, int(return_period_days))
	return now_datetime() <= return_deadline


def get_available_stock(item_code, warehouse):
	return get_available_stocks([item_code], warehouse)[cstr(item_code)]


def get_available_stocks(item_codes, warehouse):
	"""Sellable qty per item code — two grouped queries for the whole list, not two per item."""
	if not warehouse:
		warehouse = "website_warehouse"
	if not item_codes:
		return {}

	item_codes = [cstr(item_code) for item_code in item_codes]
	bin_doctype = frappe.qb.DocType("Bin")
	bin_by_item_code = {}
	for item_code_chunk in create_batch(item_codes, IN_CLAUSE_CHUNK_SIZE):
		bin_rows = (
			frappe.qb.from_(bin_doctype)
			.select(bin_doctype.item_code, bin_doctype.actual_qty, bin_doctype.reserved_qty)
			.where((bin_doctype.item_code.isin(item_code_chunk)) & (bin_doctype.warehouse == warehouse))
		).run(as_dict=True)
		bin_by_item_code.update({cstr(row.item_code): row for row in bin_rows})

	pos_reserved_by_item_code = get_pos_reserved_qtys(item_codes, warehouse)

	stock_by_item_code = {}
	for item_code in item_codes:
		bin_data = bin_by_item_code.get(item_code)
		if not bin_data:
			stock_by_item_code[item_code] = {"stock_qty": 0, "in_stock": 0}
			continue
		actual_qty = (
			flt(bin_data.actual_qty)
			- flt(bin_data.reserved_qty)
			- flt(pos_reserved_by_item_code.get(item_code))
		)
		stock_by_item_code[item_code] = {"stock_qty": actual_qty, "in_stock": int(actual_qty > 0)}
	return stock_by_item_code


def get_discount_percent(default_price, sale_price):
	"""Calculate the discount percentage."""
	# A missing sale price is "not on sale", not "100% off" — only a real row may discount to zero.
	if not default_price or sale_price is None or sale_price >= default_price:
		return 0
	return ((default_price - sale_price) / default_price) * 100


def get_pos_reserved_qty(item_code, warehouse):
	return get_pos_reserved_qtys([item_code], warehouse).get(cstr(item_code), 0)


def get_pos_reserved_qtys(item_codes, warehouse):
	if not item_codes:
		return {}

	p_inv = frappe.qb.DocType("POS Invoice")
	p_item = frappe.qb.DocType("POS Invoice Item")

	reserved_by_item_code = {}
	for item_code_chunk in create_batch(list(item_codes), IN_CLAUSE_CHUNK_SIZE):
		rows = (
			frappe.qb.from_(p_inv)
			.from_(p_item)
			.select(p_item.item_code, Sum(p_item.stock_qty).as_("stock_qty"))
			.where(
				(p_inv.name == p_item.parent)
				& (p_inv.status.isin(["Paid", "Return"]))
				& (p_item.docstatus == 1)
				& (p_item.item_code.isin(item_code_chunk))
				& (p_item.warehouse == warehouse)
			)
			.groupby(p_item.item_code)
		).run(as_dict=True)
		reserved_by_item_code.update({cstr(row.item_code): flt(row.stock_qty) for row in rows})

	return reserved_by_item_code


def update_so_status_from_related_doc(doc, method):
	sales_orders = set()

	if doc.doctype == "Sales Order":
		frappe.enqueue(
			"commera.utils.update_sales_order_ecommerce_status",
			sales_order_name=doc.name,
			enqueue_after_commit=True,
		)

	elif doc.doctype == "Sales Invoice":
		sales_orders.update([d.sales_order for d in doc.items if d.sales_order])

	elif doc.doctype == "Delivery Note":
		sales_orders.update([d.against_sales_order for d in doc.items if d.against_sales_order])

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
			"commera.utils.update_sales_order_ecommerce_status",
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
		dn_exists = frappe.db.exists("Delivery Note Item", {"against_sales_order": sales_order.name})
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
		invoice_exists = frappe.db.exists("Sales Invoice Item", {"sales_order": sales_order.name})

		if invoice_exists:
			new_status = "Delivered"
		elif shipment_exists:
			new_status = "Shipped"
		elif dn_exists:
			new_status = "Preparing for Shipment"
		else:
			new_status = "Order Received"

	frappe.db.set_value("Sales Order", sales_order.name, "custom_ecommerce_status", new_status)
