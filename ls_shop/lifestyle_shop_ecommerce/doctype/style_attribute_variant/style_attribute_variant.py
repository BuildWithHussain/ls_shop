# Copyright (c) 2025, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.website.utils import cleanup_page_name


class StyleAttributeVariant(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from frappe.website.doctype.website_slideshow_item.website_slideshow_item import (
			WebsiteSlideshowItem,
		)

		from ls_shop.lifestyle_shop_ecommerce.doctype.color_size_item.color_size_item import (
			ColorSizeItem,
		)

		attribute_name: DF.Data | None
		attribute_value: DF.Data
		configurator: DF.Link
		display_name: DF.Data
		images: DF.Table[WebsiteSlideshowItem]
		is_published: DF.Check
		item_group: DF.Link | None
		item_style: DF.Link
		route: DF.Data | None
		sizes: DF.Table[ColorSizeItem]

	# end: auto-generated types
	def validate(self):
		self.unpublish_if_incomplete_data()

	def before_save(self):
		if not self.route:
			self.route = self.scrub(self.name)
		self.update_item_group()

	def scrub(self, text):
		return cleanup_page_name(text).replace("_", "-")

	def update_item_group(self):
		if not self.item_group:
			self.item_group = frappe.db.get_value(
				"Item", self.item_style, "item_group", cache=True
			)
			item_group_mapping = frappe.get_cached_doc(
				"Lifestyle Settings"
			).ecommerce_item_group_mapping
			for mapping in item_group_mapping:
				if mapping.original_item_group == self.item_group:
					self.item_group = mapping.ecommerce_item_group
					break

	def unpublish_if_incomplete_data(self):
		if not self.is_published:
			return
		if not self.images or not self.sizes:
			self.is_published = False
			if not self.images and not self.sizes:
				frappe.msgprint(frappe._("Cannot publish without Images and Sizes"))
			elif not self.images:
				frappe.msgprint(frappe._("Cannot publish without Images"))
			else:
				frappe.msgprint(frappe._("Cannot publish without Sizes"))
