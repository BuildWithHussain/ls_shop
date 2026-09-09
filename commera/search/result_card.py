import frappe

RESULT_CARD_CATALOG = {
	"name": "Name",
	"image": "Image",
	"price": "Price",
	"brand": "Brand",
	"color": "Color",
	"item_group": "Item Group",
	"sizes": "Sizes",
}

MANDATORY_RESULT_FIELDS = ("name", "image", "price")

DEFAULT_RESULT_FIELDS = ("image", "name", "color", "price")

MIN_RESULT_FIELDS, MAX_RESULT_FIELDS = 3, 8


def get_search_result_fields():
	"""Enabled result-card fields from Lifestyle Settings, or the default layout when unconfigured."""
	settings = frappe.get_cached_doc("Lifestyle Settings")
	enabled = [
		row.field
		for row in (settings.search_result_fields or [])
		if row.show and row.field in RESULT_CARD_CATALOG
	]
	return enabled or list(DEFAULT_RESULT_FIELDS)
