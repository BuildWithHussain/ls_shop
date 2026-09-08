import frappe
from frappe.utils.jinja import get_jenv, guess_is_path

from ls_shop.shop_themes.doctype.shop_theme.shop_theme import get_theme_context, resolve_active_theme
from ls_shop.shop_themes.theme_resolver import get_theme_environment


def render_themed_template(template, context=None, theme_name=None):
	"""Render a template through the active theme's loader outside a request.

	Resolves from settings only, never ?preview_theme. `template` is a path or a template string.
	"""
	theme_context = get_theme_context(theme_name or resolve_active_theme())
	if not theme_context["dirs"]:
		# Callers pass a repo path or an admin-authored template; render_template sandboxes either.
		return frappe.render_template(template, context)  # nosemgrep: frappe-ssti

	theme_env = get_theme_environment(get_jenv(), theme_context["dirs"])

	if guess_is_path(template):
		compiled = theme_env.get_template(template)
	else:
		if ".__" in template:
			frappe.throw(frappe._("Illegal template"))
		compiled = theme_env.from_string(template)

	return compiled.render(context or {})
