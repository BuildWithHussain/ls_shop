# Copyright (c) 2026, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.caching import request_cache

WEBSITE_SETTINGS = "Website Settings"
LEGACY_SETTINGS = "Lifestyle Settings"

BUNDLED_LOGO = "/assets/ls_shop/images/meta/commera-mark.svg"
BUNDLED_FOOTER_LOGO = "/assets/ls_shop/images/meta/commera-mark.svg"
BUNDLED_FAVICON = "/assets/ls_shop/images/meta/favicon-32x32.png"

# Website Settings labels `banner_image` "Brand Image" - that is the storefront's header logo.
BRAND_ASSET_FIELDS = {
	"logo": ("banner_image", "brand_logo"),
	"footer_logo": ("footer_logo", "footer_logo"),
	"favicon": ("favicon", "favicon"),
}


# request_cache, not site_cache: site_cache is per-worker, so a save leaves other workers on a stale logo.
@request_cache
def get_configured_brand_assets() -> dict:
	"""Only what the shop owner actually set; each value is "" when neither doctype carries one."""
	website_settings = frappe.get_cached_doc(WEBSITE_SETTINGS)
	legacy_settings = frappe.get_cached_doc(LEGACY_SETTINGS)

	return {
		asset: website_settings.get(website_field) or legacy_settings.get(legacy_field) or ""
		for asset, (website_field, legacy_field) in BRAND_ASSET_FIELDS.items()
	}


def get_brand_assets():
	"""What a template paints: never empty, every asset falls through to a bundled default."""
	configured = get_configured_brand_assets()

	return frappe._dict(
		logo=configured["logo"] or BUNDLED_LOGO,
		footer_logo=configured["footer_logo"] or configured["logo"] or BUNDLED_FOOTER_LOGO,
		favicon=configured["favicon"] or BUNDLED_FAVICON,
	)
