import os

import frappe

from ls_shop.shop_themes.doctype.shop_theme.shop_theme import (
	get_render_theme_context,
	is_within_directory,
)


def shop_theme_asset_url(path):
	"""Resolve a public asset against the theme inheritance chain, child first.
	Name is app-prefixed: jinja hook methods share one global dict by function name and the last app wins.
	"""
	theme_context = get_render_theme_context()
	if not theme_context["theme_name"]:
		return ""

	relative_path = path.lstrip("/")
	apps = theme_context["apps"]

	for name in theme_context["names"]:
		app = apps[name]
		slug = frappe.scrub(name)
		theme_public_dir = os.path.join(frappe.get_app_path(app), "public", "themes", slug)
		asset_path = os.path.join(theme_public_dir, relative_path)
		if is_within_directory(theme_public_dir, asset_path) and os.path.isfile(asset_path):
			return f"/assets/{app}/themes/{slug}/{relative_path}"

	# Nothing in the chain ships it: fall back to the ACTIVE theme's URL so the 404 names this theme.
	active_name = theme_context["names"][0]
	active_app = apps[active_name]
	return f"/assets/{active_app}/themes/{frappe.scrub(active_name)}/{relative_path}"


def shop_theme_config():
	"""The active theme's settings Single, for reading FIELDS off in a template.
	Never call a controller method on it from a template: jinja's SafeDoc wrapper resolves methods to None.
	"""
	theme_context = get_render_theme_context()
	settings_doctype = theme_context.get("settings_doctype")
	if not settings_doctype:
		return frappe._dict()

	return frappe.get_cached_doc(settings_doctype)
