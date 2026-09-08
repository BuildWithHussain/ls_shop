# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cstr
from frappe.website.utils import cleanup_page_name


class ShopWebPage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		content: DF.TextEditor
		content_ar: DF.TextEditor | None
		meta_description: DF.SmallText | None
		meta_title: DF.Data | None
		noindex: DF.Check
		og_image: DF.AttachImage | None
		published: DF.Check
		route: DF.Data | None
	# end: auto-generated types

	def before_save(self):
		if not self.route:
			# cleanup_page_name yields underscores for spaces; storefront slugs are hyphenated.
			self.route = cleanup_page_name(cstr(self.name)).replace("_", "-")

		if frappe.db.exists("Shop Web Page", {"route": self.route, "name": ("!=", self.name)}):
			frappe.throw(frappe._("Another page already uses the route {0}.").format(self.route))


def get_page_by_route(route):
	"""The page a visitor may see on this route, or None. No role holds `read`, so a shopper can never
	list drafts through frappe.client; this reads past permissions and `published` is the whole gate."""
	if not route:
		return None

	name = frappe.db.get_value("Shop Web Page", {"route": route}, "name")
	if not name:
		return None

	page = frappe.get_cached_doc("Shop Web Page", name)
	if not page.published and not frappe.has_permission("Shop Web Page", "write", doc=page):
		return None

	return page


def get_page_content(page):
	return (page.content_ar or page.content) if frappe.local.lang == "ar" else page.content
