# Copyright (c) 2026, company@bwhstudios.com and contributors
# For license information, please see license.txt

"""Renders a theme's home page for the theme editor's iframe.
Defaults to the live theme; `?theme=` frames an installed theme that is not live yet."""

import frappe
from frappe.utils import escape_html

from ls_shop.shop_themes.chrome_preview import TRACKING_BLANKED_BLOCKS, render_page_preview

HOME_TEMPLATE = "pages/index.html"

no_cache = True

PREVIEW_LANGUAGES = ("en", "ar")


def get_context(context):
	frappe.has_permission("Shop Theme Settings", "write", throw=True)

	theme = requested_theme()

	lang = frappe.form_dict.get("lang")
	if lang not in PREVIEW_LANGUAGES:
		lang = frappe.local.lang or "en"

	# The themed page reads its language off frappe.lang, so the ?lang switch must move it here.
	frappe.local.lang = lang

	rendered = render_page_preview(HOME_TEMPLATE, TRACKING_BLANKED_BLOCKS, theme_name=theme)
	if rendered:
		context.rendered_html = rendered
		return

	# No theme to render, or one that ships no home page: the pane says so rather than framing a 404.
	context.rendered_html = f"""<!DOCTYPE html>
<html lang="{escape_html(lang)}">
<head>
<meta charset="UTF-8">
<link rel="stylesheet" href="/assets/ls_shop/css/tailwind.css">
</head>
<body class="grid min-h-screen place-items-center bg-gray-50 p-6 text-center text-gray-500">
<p>{escape_html(no_preview_message(theme))}</p>
</body>
</html>"""


def requested_theme():
	"""The installed theme the pane asked for, or None to fall back to the live one."""
	theme = frappe.form_dict.get("theme")
	if not theme or not frappe.db.exists("Shop Theme", theme):
		return None

	return theme


def no_preview_message(theme):
	if theme:
		return frappe._("{0} has no home page to preview.").format(theme)

	return frappe._("The live theme has no home page to preview.")
