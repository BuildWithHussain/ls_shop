# Copyright (c) 2025, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class StyleAttributeConfigurator(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from ls_shop.lifestyle_shop_ecommerce.doctype.recommended_variant.recommended_variant import (
			RecommendedVariant,
		)

		item_attribute: DF.Link
		item_template: DF.Link
		recommended_items: DF.Table[RecommendedVariant]
	# end: auto-generated types

	def after_insert(self):
		settings = frappe.get_cached_doc("Lifestyle Settings")

		if settings.create_variants_automatically_on_configurator_creation:
			self.generate_variants()

	@frappe.whitelist()
	def generate_variants(self):
		# Fetch all variant attributes for the template item
		all_attributes = frappe.db.get_all(
			"Item Variant Attribute",
			filters={"parenttype": "Item", "variant_of": self.item_template},
			fields=["attribute", "attribute_value", "parent"],
		)

		# Group attributes by parent item
		grouped_by_parent_items = {}
		attribute_name_field = frappe.get_cached_value(
			"Lifestyle Settings", "Lifestyle Settings", "attribute_name_field"
		)
		for item in all_attributes:
			grouped_by_parent_items.setdefault(item.parent, []).append(item)

		# Create the result dictionary organized by the specified attribute
		result = {}
		for parent, variant_attributes in grouped_by_parent_items.items():
			# Find the value of the specified attribute (e.g., color) for this item
			color_value = next(
				(
					attr["attribute_value"]
					for attr in variant_attributes
					if attr["attribute"] == self.item_attribute
				),
				None,
			)
			attribute_name = next(
				(
					attr["attribute_value"]
					for attr in variant_attributes
					if attr["attribute"] == attribute_name_field
				),
				color_value,
			)

			if color_value:
				# Create a dictionary of other attributes for this item
				item_info = {"item_code": parent}
				for attr in variant_attributes:
					if attr["attribute"] != self.item_attribute:
						item_info[attr["attribute"].lower()] = attr["attribute_value"]

				# Add to the result dictionary
				if color_value not in result:
					result[color_value] = {
						"attribute_name": attribute_name,
						"items": [],
					}
				result[color_value]["items"].append(item_info)
		for color, variants in result.items():
			item_template_name = frappe.get_value(
				"Item", self.item_template, "item_name"
			)
			if not item_template_name:
				item_template_name = self.item_template
			try:
				frappe.get_doc(
					{
						"doctype": "Style Attribute Variant",
						"display_name": f"{item_template_name}",
						"configurator": self.name,
						"attribute_value": color,
						"attribute_name": variants["attribute_name"],
						"sizes": variants["items"],
						"is_published": False,
					}
				).insert()
			except frappe.exceptions.DuplicateEntryError:
				pass

	def get_total_variants(self):
		return frappe.db.count("Style Attribute Variant", {"configurator": self.name})
