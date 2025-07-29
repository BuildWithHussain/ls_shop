# Copyright (c) 2025, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_url_to_form


class LifestyleSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from ls_shop.lifestyle_shop_ecommerce.doctype.item_group_map.item_group_map import (
			ItemGroupMap,
		)
		from ls_shop.lifestyle_shop_ecommerce.doctype.return_reason.return_reason import (
			ReturnReason,
		)

		attribute_name_field: DF.Data | None
		based_on_attribute: DF.Link | None
		cc_email: DF.Data | None
		charge_account_head: DF.Link | None
		cod_charge: DF.Currency
		cod_charge_applicable_below: DF.Currency
		cod_enabled: DF.Check
		create_variants_automatically_on_configurator_creation: DF.Check
		default_price_list: DF.Link | None
		ecommerce_item_group_mapping: DF.Table[ItemGroupMap]
		ecommerce_warehouse: DF.Link | None
		item_in_stock_email_template: DF.Link
		logo_url: DF.Data | None
		order_cancellation_email_template: DF.Link
		order_confirmation_email_template: DF.Link
		print_format: DF.Link | None
		reason_for_return: DF.Table[ReturnReason]
		return_period: DF.Int
		sale_price_list: DF.Link | None
		shipping_rule: DF.Link | None
		tabby_enabled: DF.Check
		telr_enabled: DF.Check
	# end: auto-generated types
	pass

	def validate(self):
		if not self.telr_enabled and not self.tabby_enabled and not self.cod_enabled:
			frappe.throw(
				frappe._(
					"At least one payment method (Telr, Tabby, or COD) must be enabled."
				)
			)

	def get_default_price_list(self):
		return (
			self.default_price_list
			if self.default_price_list
			else frappe.get_cached_value(
				"Webshop Settings", "Webshop Settings", "price_list"
			)
		)

	def get_sale_price_list(self):
		return (
			self.sale_price_list
			if self.sale_price_list
			else frappe.get_cached_value(
				"Webshop Settings", "Webshop Settings", "price_list"
			)
		)

	@frappe.whitelist()
	def enqueue_publish_all_variants(self, attribute: str):
		log = create_configurator_log()
		frappe.enqueue(
			"ls_shop.lifestyle_shop_ecommerce.doctype.lifestyle_settings.lifestyle_settings.generate_configurators_for_all_templates",
			queue="long",
			attribute=attribute,
			log_name=log.name,
		)
		link = get_url_to_form(
			"Bulk Style Attribute Configurator Creation Log", log.name
		)

		return frappe._(f"Creating configurators. <a href='{link}'>View Log</a>")

	@frappe.whitelist()
	def sync_item_group_mapping_to_ecommerce_items(self):
		for mapping in self.ecommerce_item_group_mapping:
			frappe.db.set_value(
				"Style Attribute Variant",
				{"item_group": mapping.original_item_group},
				"item_group",
				mapping.ecommerce_item_group,
			)


def generate_configurators_for_all_templates(attribute: str, log_name: str):
	item = frappe.qb.DocType("Item")
	configurator = frappe.qb.DocType("Style Attribute Configurator")

	query = (
		frappe.qb.from_(item)
		.left_join(configurator)
		.on(item.name == configurator.item_template)
		.select(item.name)
		.where(configurator.item_template.isnull() & item.has_variants)
	)
	results = query.run(as_dict=True)
	configurator_log = frappe.get_doc(
		"Bulk Style Attribute Configurator Creation Log", log_name
	)
	configurator_log.configurators = []

	for row in results:
		item_name = row.get("name")
		configurator = frappe.get_doc(
			{
				"doctype": "Style Attribute Configurator",
				"item_template": item_name,
				"item_attribute": attribute,
			}
		).insert(ignore_permissions=True)
		variants_generated = configurator.get_total_variants()
		frappe.db.commit()
		configurator_log.append(
			"configurators",
			{
				"style_attribute_configurator": configurator.name,
				"variants_created": variants_generated,
			},
		)
		configurator_log.save()


def create_configurator_log():
	return frappe.get_doc(
		{
			"doctype": "Bulk Style Attribute Configurator Creation Log",
		}
	).insert(ignore_permissions=True)
