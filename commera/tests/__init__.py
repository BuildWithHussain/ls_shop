# Copyright (c) 2026, company@bwhstudios.com and Contributors
# See license.txt

"""Fixture helpers shared across the app's test suites."""

import frappe

from commera.commera_ecommerce.doctype.ecommerce_category.ecommerce_category import (
	ITEM_GROUP_LINK_DOCTYPE,
)
from commera.install import TEST_ITEM_GROUP
from commera.utils import IN_CLAUSE_CHUNK_SIZE


def delete_menu_entries(filters=None):
	"""Delete menu entries along with the item-group links hanging off them.

	`frappe.db.delete` never touches child rows, and an orphan link re-attaches to the next same-named entry.
	"""
	names = frappe.get_all("Ecommerce Category", filters=filters, pluck="name")
	for offset in range(0, len(names), IN_CLAUSE_CHUNK_SIZE):
		frappe.db.delete(
			ITEM_GROUP_LINK_DOCTYPE,
			{
				"parenttype": "Ecommerce Category",
				"parent": ["in", names[offset : offset + IN_CLAUSE_CHUNK_SIZE]],
			},
		)
	frappe.db.delete("Ecommerce Category", filters)


def get_test_item() -> str:
	"""A plain sellable item to hang fixtures off: a bare CI site ships none, and `Item[0]` throws."""
	item_code = "ZZ Test Item"
	if not frappe.db.exists("Item", item_code):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group": TEST_ITEM_GROUP,
				"stock_uom": "Nos",
				"is_stock_item": 0,
			}
		).insert(ignore_permissions=True)

	return item_code


def get_test_configurator() -> str:
	"""The configurator every Style Attribute Variant fixture points at, created on first ask."""
	attribute = "ZZ Test Attribute"
	if not frappe.db.exists("Item Attribute", attribute):
		frappe.get_doc(
			{
				"doctype": "Item Attribute",
				"attribute_name": attribute,
				"item_attribute_values": [{"attribute_value": "ZZ Value", "abbr": "ZZV"}],
			}
		).insert(ignore_permissions=True)

	name = f"{get_test_item()} {attribute}"
	if not frappe.db.exists("Style Attribute Configurator", name):
		frappe.get_doc(
			{
				"doctype": "Style Attribute Configurator",
				"item_template": get_test_item(),
				"item_attribute": attribute,
			}
		).insert(ignore_permissions=True)

	return name
