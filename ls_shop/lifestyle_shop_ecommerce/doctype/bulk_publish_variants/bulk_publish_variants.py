# Copyright (c) 2025, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder import DocType


class BulkPublishVariants(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		brand: DF.Link | None
		dcs: DF.Data | None
		item_code: DF.Data | None
		season_code: DF.Data | None
		vendor_code: DF.Data | None
	# end: auto-generated types
	pass

	@frappe.whitelist()
	def bulk_toggle_publish(
		self,
		publish: bool = True,
		style_attribute_variant_list: list[str] | None = None,
	):
		style_attribute_variant = DocType("Style Attribute Variant")
		color_size_item = DocType("Color Size Item")
		website_slideshow_item = DocType("Website Slideshow Item")
		child_item = DocType("Item").as_("child_item")
		style_item = DocType("Item").as_("style_item")
		item_attr = DocType("Item Variant Attribute")

		query = (
			frappe.qb.from_(style_attribute_variant)
			.inner_join(color_size_item)
			.on(color_size_item.parent == style_attribute_variant.name)
			.inner_join(website_slideshow_item)
			.on(website_slideshow_item.parent == style_attribute_variant.name)
			.left_join(child_item)
			.on(child_item.name == color_size_item.item_code)
			.left_join(style_item)
			.on(style_item.name == style_attribute_variant.item_style)
			.left_join(item_attr)
			.on(item_attr.parent == child_item.name)
		)
		if style_attribute_variant_list:
			query = query.where(
				style_attribute_variant.name.isin(style_attribute_variant_list)
			)
		if self.vendor_code:
			query = query.where(
				(style_item.custom_vendor_code == self.vendor_code)
				| (child_item.custom_vendor_code == self.vendor_code)
			)
		if self.dcs:
			query = query.where(
				(style_item.custom_dcs == self.dcs)
				| (child_item.custom_dcs == self.dcs)
			)
		if self.brand:
			query = query.where(
				(style_item.brand == self.brand) | (child_item.brand == self.brand)
			)
		if self.item_code:
			query = query.where(
				(style_item.name == self.item_code)
				| (style_item.name == self.item_code)
			)
		if self.season_code:
			query = query.where(
				(item_attr.attribute == "Season")
				& (item_attr.attribute_value == self.season_code)
			)

		query = query.select(style_attribute_variant.name)
		query = query.distinct()
		variants = query.run(as_dict=True)
		variant_names = [v["name"] for v in variants]
		total_count = 0
		if variant_names:
			condition = {"name": ["in", variant_names], "is_published": not publish}
			total_count = frappe.db.count("Style Attribute Variant", condition)
			frappe.db.set_value(
				"Style Attribute Variant",
				{"name": ["in", variant_names]},
				{"is_published": publish},
			)

		return {"updated_count": total_count, "total_matched": len(variant_names)}
