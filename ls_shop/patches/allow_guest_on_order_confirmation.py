import frappe

from ls_shop.shop_themes.doctype.shop_theme_settings.shop_theme_settings import (
	LANG,
	clear_settings_cache,
)


def execute():
	"""Open the gateway return URL to a logged-out shopper."""
	# seed_default_routes only adds missing patterns, so an existing route keeps its seeded requires_auth.
	frappe.db.set_value(
		"Shop Themed Route",
		{"url_pattern": rf"^{LANG}/account/orders/confirmation$", "requires_auth": 1},
		"requires_auth",
		0,
		update_modified=False,
	)
	clear_settings_cache()
