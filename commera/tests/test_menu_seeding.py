# Copyright (c) 2026, company@bwhstudios.com and Contributors
# See license.txt

"""The menu is a copy of the Item Group tree, taken once; afterwards the two trees are independent."""

from urllib.parse import quote

import frappe
from frappe.database.schema import add_column
from frappe.tests import IntegrationTestCase
from frappe.utils.nestedset import get_root_of

from commera.commera_ecommerce.doctype.commera_settings.navbar import navbar_manager
from commera.commera_ecommerce.doctype.ecommerce_category.ecommerce_category import (
	get_item_groups_by_entry,
	get_menu_tree,
)
from commera.patches import move_ecommerce_category_to_item_group_link as seeding_patch
from commera.patches import move_item_group_links_onto_the_menu_entry as link_migration
from commera.tests import delete_menu_entries
from commera.www.sitemap_segment import SEGMENT_CONFIG, get_segment_filters

PREFIX = "Test Seed"
# The shape the app briefly shipped between the single link and the table it is back on.
INTERIM_DOCTYPE = "Ecommerce Category Item Group Link"


def make_item_group(name, parent=None):
	return frappe.get_doc(
		{
			"doctype": "Item Group",
			"item_group_name": name,
			# commera makes the storefront display name mandatory on Item Group.
			"custom_displayname": name,
			"parent_item_group": parent or get_root_of("Item Group"),
			"is_group": 1,
		}
	).insert()


def add_legacy_column():
	"""Restore the dropped `item_group` column so the migration runs against a real one.
	Left in place afterwards: dropping it would be DDL on a shared test database.
	"""
	if "item_group" not in frappe.db.get_table_columns("Ecommerce Category"):
		add_column("Ecommerce Category", "item_group", "Link")
		# add_column leaves the cached column list stale, so the migration under test would read the
		# table as it was before the ALTER. Frappe's own db tests clear the key the same way.
		frappe.client_cache.delete_value("table_columns::tabEcommerce Category")


def purge_stale_fixtures():
	"""Sweep rows the end-of-class rollback cannot: DDL in the migration commits the open transaction in MariaDB."""
	delete_menu_entries({"name": ["like", f"{PREFIX}%"]})
	frappe.db.delete("Item Group", {"name": ["like", f"{PREFIX}%"]})


def find_node(nodes, name):
	for node in nodes:
		if node["name"] == name:
			return node
		found = find_node(node["children"], name)
		if found:
			return found
	return None


class TestMenuSeeding(IntegrationTestCase):
	def setUp(self):
		purge_stale_fixtures()
		# Unique per test: a sibling class commits mid-run, so a fixed name is a duplicate-key error next run.
		self.prefix = f"{PREFIX} {frappe.generate_hash(length=8)}"
		self.shoes = make_item_group(f"{self.prefix} Shoes").name
		self.sneakers = make_item_group(f"{self.prefix} Sneakers", self.shoes).name
		self.boots = make_item_group(f"{self.prefix} Boots", self.shoes).name

	def tearDown(self):
		purge_stale_fixtures()
		frappe.local.commera_storefront_menu = None

	def seeded_entries(self):
		"""The menu entries this test seeded, keyed by the item group each one links."""
		entries = frappe.get_all(
			"Ecommerce Category",
			filters={"category_name": ["like", f"{self.prefix}%"]},
			fields=["name", "parent_ecommerce_category", "is_group", "lft", "rgt"],
		)
		item_groups_by_entry = get_item_groups_by_entry([entry.name for entry in entries])
		return {
			item_groups_by_entry[entry.name][0]: entry
			for entry in entries
			if item_groups_by_entry.get(entry.name)
		}

	def item_group_snapshot(self):
		return frappe.get_all(
			"Item Group",
			filters={"name": ["like", f"{self.prefix}%"]},
			fields=["name", "parent_item_group", "is_group", "lft", "rgt", "modified"],
			order_by="name asc",
		)

	def test_seeding_copies_the_item_group_tree_shape(self):
		navbar_manager.seed_categories_from_item_groups(item_group=self.shoes)

		entries = self.seeded_entries()
		self.assertEqual(set(entries), {self.shoes, self.sneakers, self.boots})

		root = entries[self.shoes]
		self.assertFalse(root.parent_ecommerce_category)
		self.assertEqual(entries[self.sneakers].parent_ecommerce_category, root.name)
		self.assertEqual(entries[self.boots].parent_ecommerce_category, root.name)

		# A parent with children must be marked a group, or the editor renders it as a leaf.
		self.assertEqual(root.is_group, 1)

	def test_seeding_gives_every_entry_valid_tree_bounds(self):
		navbar_manager.seed_categories_from_item_groups(item_group=self.shoes)

		entries = self.seeded_entries()
		root = entries[self.shoes]
		# Bulk seeding suppresses per-row nested-set bookkeeping, so the bounds are what a regression leaves at 0/0.
		self.assertGreater(root.rgt, root.lft)
		for item_group in (self.sneakers, self.boots):
			child = entries[item_group]
			self.assertGreater(child.lft, root.lft)
			self.assertLess(child.rgt, root.rgt)

	def test_seeding_twice_adds_nothing(self):
		navbar_manager.seed_categories_from_item_groups(item_group=self.shoes)
		before = sorted(self.seeded_entries())

		navbar_manager.seed_categories_from_item_groups(item_group=self.shoes)

		self.assertEqual(sorted(self.seeded_entries()), before)

	def test_the_menu_and_the_catalogue_stay_independent(self):
		navbar_manager.seed_categories_from_item_groups(item_group=self.shoes)
		before = self.item_group_snapshot()
		sneakers_entry = self.seeded_entries()[self.sneakers].name

		navbar_manager.update_node(sneakers_entry, display_name=f"{self.prefix} Trainers")
		navbar_manager.delete_node(self.seeded_entries()[self.boots].name)

		self.assertEqual(before, self.item_group_snapshot())
		self.assertTrue(frappe.db.exists("Item Group", [self.boots]))

	def test_a_new_item_group_does_not_appear_in_the_menu_on_its_own(self):
		"""The copy is a starting point, not a live mirror — only a re-import brings new groups in."""
		navbar_manager.seed_categories_from_item_groups(item_group=self.shoes)

		sandals = make_item_group(f"{self.prefix} Sandals", self.shoes).name

		self.assertNotIn(sandals, self.seeded_entries())

	def test_install_seeds_the_menu_only_when_the_store_has_none(self):
		delete_menu_entries()

		navbar_manager.seed_menu_when_empty()
		self.assertIn(self.shoes, self.seeded_entries())

		# A shop owner who built their own menu must not have the catalogue poured back into it.
		delete_menu_entries()
		navbar_manager.create_node("", f"{self.prefix} Hand Built")

		navbar_manager.seed_menu_when_empty()
		self.assertNotIn(self.shoes, self.seeded_entries())

	def test_seeded_nested_entries_stay_out_of_the_sitemap(self):
		"""Seeding multiplies nested rows, and only a root carries a route — the rest emit no URL."""
		navbar_manager.seed_categories_from_item_groups(item_group=self.shoes)

		routable = frappe.get_all(
			"Ecommerce Category",
			filters={
				**get_segment_filters(SEGMENT_CONFIG["collections"]),
				"category_name": ["like", f"{self.prefix}%"],
			},
			pluck="name",
		)

		self.assertEqual(routable, [self.seeded_entries()[self.shoes].name])


def make_interim_child_doctype():
	"""Rebuild the interim child table so the migration runs against real rows, not a stand-in.
	`custom` keeps it in the database: a regular DocType would write a JSON file into the app folder.
	"""
	if frappe.db.exists("DocType", INTERIM_DOCTYPE):
		return

	frappe.get_doc(
		{
			"doctype": "DocType",
			"name": INTERIM_DOCTYPE,
			"module": "Commera Ecommerce",
			"custom": 1,
			"istable": 1,
			"fields": [
				{
					"fieldname": "item_group",
					"fieldtype": "Link",
					"label": "Item Group",
					"options": "Item Group",
				}
			],
			"permissions": [],
		}
	).insert()


def add_interim_link(category, item_group, idx):
	frappe.get_doc(
		{
			"doctype": INTERIM_DOCTYPE,
			"parent": category,
			"parenttype": "Ecommerce Category",
			"parentfield": "item_groups",
			"item_group": item_group,
			"idx": idx,
		}
	).insert()


class TestItemGroupLinkMigration(IntegrationTestCase):
	"""Every starting point converges on the entry's own `link_item_groups` table."""

	def setUp(self):
		purge_stale_fixtures()
		self.prefix = f"{PREFIX} {frappe.generate_hash(length=8)}"
		self.shirts = make_item_group(f"{self.prefix} Shirts").name
		self.belts = make_item_group(f"{self.prefix} Belts").name
		self.tab = navbar_manager.create_node("", f"{self.prefix} Menswear").name
		self.entry = navbar_manager.create_node(self.tab, f"{self.prefix} Tops", "Item Group").name
		add_legacy_column()

	def tearDown(self):
		if frappe.db.exists("DocType", INTERIM_DOCTYPE):
			frappe.delete_doc("DocType", INTERIM_DOCTYPE, ignore_permissions=True)
		purge_stale_fixtures()
		frappe.local.commera_storefront_menu = None

	def linked_item_groups(self):
		return get_item_groups_by_entry([self.entry]).get(self.entry, [])

	def set_legacy_column(self, item_group):
		category = frappe.qb.DocType("Ecommerce Category")
		(
			frappe.qb.update(category)
			.set(category.item_group, item_group)
			.where(category.name == self.entry)
			.run()
		)

	def get_legacy_column(self):
		category = frappe.qb.DocType("Ecommerce Category")
		return (
			frappe.qb.from_(category)
			.select(category.item_group)
			.where(category.name == self.entry)
			.run(pluck=True)[0]
		)

	def test_links_already_on_the_entry_are_left_where_they_are(self):
		"""A site that never left the original table has nothing to move — and nothing to lose."""
		navbar_manager.update_node(self.entry, link_type="Item Group", link_target=[self.shirts, self.belts])

		link_migration.execute()

		self.assertEqual(self.linked_item_groups(), [self.shirts, self.belts])

	def test_the_interim_table_lands_on_the_entry_and_is_dropped(self):
		make_interim_child_doctype()
		add_interim_link(self.entry, self.shirts, 1)
		add_interim_link(self.entry, self.belts, 2)

		link_migration.execute()

		self.assertEqual(self.linked_item_groups(), [self.shirts, self.belts])
		self.assertFalse(frappe.db.exists("DocType", INTERIM_DOCTYPE))
		# Deleting the DocType does not drop its table, and an orphan table survives every later migrate.
		self.assertFalse(frappe.db.table_exists(INTERIM_DOCTYPE))

	def test_the_column_link_lands_on_the_entry(self):
		self.set_legacy_column(self.shirts)

		link_migration.execute()

		self.assertEqual(self.linked_item_groups(), [self.shirts])
		self.assertIsNone(self.get_legacy_column())

	def test_the_interim_rows_win_over_a_stale_column(self):
		"""Both can be present, and the column is the older of the two."""
		make_interim_child_doctype()
		add_interim_link(self.entry, self.shirts, 1)
		self.set_legacy_column(self.belts)

		link_migration.execute()

		self.assertEqual(self.linked_item_groups(), [self.shirts])

	def test_the_migrated_menu_still_renders(self):
		make_interim_child_doctype()
		add_interim_link(self.entry, self.shirts, 1)
		add_interim_link(self.entry, self.belts, 2)

		link_migration.execute()

		node = find_node(get_menu_tree(), self.entry)
		self.assertEqual(node["item_groups"], [self.shirts, self.belts])
		self.assertIn(quote(f"{self.shirts},{self.belts}"), node["href"])

	def test_running_the_migration_twice_changes_nothing(self):
		make_interim_child_doctype()
		add_interim_link(self.entry, self.shirts, 1)
		self.set_legacy_column(self.belts)

		link_migration.execute()
		after_first_run = self.linked_item_groups()

		link_migration.execute()

		self.assertEqual(self.linked_item_groups(), after_first_run)

	def test_the_patch_that_used_to_drop_the_table_leaves_the_links_alone(self):
		"""It ran on some sites and not others, and the table it dropped is live again."""
		navbar_manager.update_node(self.entry, link_type="Item Group", link_target=[self.shirts, self.belts])

		seeding_patch.execute()

		self.assertEqual(self.linked_item_groups(), [self.shirts, self.belts])
		self.assertTrue(frappe.db.table_exists("Ecommerce Category Item Group"))
