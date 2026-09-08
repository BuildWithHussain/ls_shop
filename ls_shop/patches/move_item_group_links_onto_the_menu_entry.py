import frappe

from ls_shop.lifestyle_shop_ecommerce.doctype.ecommerce_category.ecommerce_category import (
	ITEM_GROUP_LINK_DOCTYPE,
	add_item_group_links,
)
from ls_shop.utils import IN_CLAUSE_CHUNK_SIZE

PARENT_DOCTYPE = "Ecommerce Category"
INTERIM_DOCTYPE = "Ecommerce Category Item Group Link"
LEGACY_COLUMN = "item_group"


def execute():
	"""Land every item group a menu entry links on the entry's own `link_item_groups` table."""
	add_links_from_interim_table()
	add_links_from_legacy_column()
	drop_interim_table()


def add_links_from_interim_table():
	# Read through the table, not the DocType: migrate deletes a DocType whose JSON left the app.
	if not frappe.db.table_exists(INTERIM_DOCTYPE):
		return

	interim = frappe.qb.DocType(INTERIM_DOCTYPE)
	rows = (
		frappe.qb.from_(interim)
		.select(interim.parent, interim.item_group)
		.where(interim.parenttype == PARENT_DOCTYPE)
		.orderby(interim.parent)
		.orderby(interim.idx)
		.run(as_dict=True)
	)

	item_groups_by_entry = {}
	for row in rows:
		item_groups_by_entry.setdefault(row.parent, []).append(row.item_group)

	add_item_group_links(item_groups_by_entry)


def add_links_from_legacy_column():
	"""Carry the one link that used to sit in a column of its own.

	Read via the query builder: the field is gone from the DocType that `frappe.get_all` validates against.
	"""
	if LEGACY_COLUMN not in frappe.db.get_table_columns(PARENT_DOCTYPE):
		return

	category = frappe.qb.DocType(PARENT_DOCTYPE)
	entries = (
		frappe.qb.from_(category)
		.select(category.name, category.item_group)
		.where(category.item_group.notnull() & (category.item_group != ""))
		.run(as_dict=True)
	)
	if not entries:
		return

	add_item_group_links({entry.name: [entry.item_group] for entry in entries})
	# Clearing the column is what makes a second run a no-op: the rows it would copy are gone.
	clear_legacy_column([entry.name for entry in entries])
	frappe.clear_document_cache(PARENT_DOCTYPE)


def clear_legacy_column(names):
	category = frappe.qb.DocType(PARENT_DOCTYPE)
	for offset in range(0, len(names), IN_CLAUSE_CHUNK_SIZE):
		chunk = names[offset : offset + IN_CLAUSE_CHUNK_SIZE]
		frappe.qb.update(category).set(category.item_group, None).where(category.name.isin(chunk)).run()


def drop_interim_table():
	# Deleting the DocType does not take its table with it, so both have to be asked for.
	# The drop goes through the query builder: MariaDB and Postgres quote the identifier differently.
	if frappe.db.exists("DocType", INTERIM_DOCTYPE):
		frappe.delete_doc("DocType", INTERIM_DOCTYPE, ignore_permissions=True)

	if frappe.db.table_exists(INTERIM_DOCTYPE):
		frappe.db.sql_ddl(frappe.qb.drop_table(frappe.qb.DocType(INTERIM_DOCTYPE)).if_exists().get_sql())
