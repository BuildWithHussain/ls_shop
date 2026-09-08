# Copyright (c) 2026, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe

from ls_shop.branding import BRAND_ASSET_FIELDS, LEGACY_SETTINGS, WEBSITE_SETTINGS


def execute():
	"""Seed Website Settings from the legacy Lifestyle Settings branding fields."""
	legacy_settings = frappe.get_cached_doc(LEGACY_SETTINGS)
	website_settings = frappe.get_doc(WEBSITE_SETTINGS)

	copied_fields = []
	for website_field, legacy_field in BRAND_ASSET_FIELDS.values():
		legacy_value = legacy_settings.get(legacy_field)
		if not legacy_value or website_settings.get(website_field):
			continue
		website_settings.set(website_field, legacy_value)
		copied_fields.append(website_field)

	if not copied_fields:
		return

	website_settings.save()
	print(f"Copied brand assets to Website Settings: {', '.join(copied_fields)}")
