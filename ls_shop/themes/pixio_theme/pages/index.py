import frappe

from ls_shop.utils import get_product_list
from ls_shop.www import index

# The picks tables Pixio's homepage sections render, keyed by their settings fieldname.
PICKS_FIELDS = ("best_picks", "deal_picks", "featured_picks")


def get_context(context):
	index.get_context(context)
	settings = frappe.get_cached_doc("Pixio Theme Settings")
	context.picked_products = {field: get_picked_products(settings.get(field)) for field in PICKS_FIELDS}
	return context


def get_picked_products(rows):
	"""Hydrate one pinned-variant table into storefront product cards."""
	variants = [row.item_variant for row in rows]
	if not variants:
		return []

	return get_product_list(product_list=variants, page_length=len(variants))
