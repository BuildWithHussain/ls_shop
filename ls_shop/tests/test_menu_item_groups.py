# Copyright (c) 2026, company@bwhstudios.com and Contributors
# See license.txt

"""A menu entry links any number of item groups, always as a list and never null."""

from urllib.parse import unquote

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils.nestedset import get_root_of

from ls_shop.lifestyle_shop_ecommerce.doctype.ecommerce_category.ecommerce_category import get_menu_tree
from ls_shop.lifestyle_shop_ecommerce.doctype.lifestyle_settings.navbar import navbar_manager
from ls_shop.shop_data import get_category_facets
from ls_shop.tests import delete_menu_entries

PREFIX = "Test MIG"


def find_node(nodes, name):
	for node in nodes:
		if node["name"] == name:
			return node
		found = find_node(node["children"], name)
		if found:
			return found
	return None


class TestMenuItemGroups(IntegrationTestCase):
	def setUp(self):
		self.tag = frappe.generate_hash(length=8)
		self.shirts = self.make_item_group(f"{PREFIX} Shirts {self.tag}")
		self.denim = self.make_item_group(f"{PREFIX} Denim {self.tag}")
		self.tab = navbar_manager.create_node("", f"{PREFIX} Sale {self.tag}").name
		frappe.local.ls_shop_storefront_menu = None

	def tearDown(self):
		delete_menu_entries({"name": ["like", f"{PREFIX}%"]})
		frappe.db.delete("Item Group", {"name": ["like", f"{PREFIX}%"]})
		frappe.local.ls_shop_storefront_menu = None

	def make_item_group(self, name):
		return (
			frappe.get_doc(
				{
					"doctype": "Item Group",
					"item_group_name": name,
					# ls_shop makes the storefront display name mandatory on Item Group.
					"custom_displayname": name,
					"parent_item_group": get_root_of("Item Group"),
					"is_group": 0,
				}
			)
			.insert()
			.name
		)

	def add_entry(self, label, link_target):
		menu = navbar_manager.add_node(self.tab, label, "Item Group", link_target)["menu"]
		return next(node for node in find_node(menu, self.tab)["children"] if node["label"] == label)

	def test_an_entry_serialises_every_group_it_links_in_editor_order(self):
		entry = self.add_entry(f"{PREFIX} Both", [self.denim, self.shirts])

		self.assertEqual(entry["item_groups"], [self.denim, self.shirts])

	def test_an_entry_that_links_nothing_serialises_an_empty_list(self):
		"""The editor reads the length before anything else, so a null here breaks the whole page."""
		heading = self.add_entry(f"{PREFIX} Heading", None)

		self.assertEqual(heading["item_groups"], [])
		self.assertEqual(find_node(get_menu_tree(), self.tab)["item_groups"], [])

	def test_the_groups_survive_a_round_trip_through_the_editor(self):
		entry = self.add_entry(f"{PREFIX} Both", [self.shirts, self.denim])

		menu = navbar_manager.update_node(entry["name"], link_type="Item Group", link_target=[self.denim])[
			"menu"
		]

		self.assertEqual(find_node(menu, entry["name"])["item_groups"], [self.denim])

	def test_a_form_encoded_request_carries_the_list_as_text(self):
		"""`frappe.call` posts JSON, but a form-encoded request delivers the array as a string."""
		entry = self.add_entry(f"{PREFIX} Encoded", frappe.as_json([self.shirts, self.denim]))

		self.assertEqual(entry["item_groups"], [self.shirts, self.denim])

	def test_switching_the_link_type_clears_the_groups(self):
		entry = self.add_entry(f"{PREFIX} Both", [self.shirts, self.denim])

		menu = navbar_manager.update_node(entry["name"], link_type="URL", link_target="https://example.com")[
			"menu"
		]

		self.assertEqual(find_node(menu, entry["name"])["item_groups"], [])

	def test_the_listing_link_filters_on_every_group(self):
		entry = self.add_entry(f"{PREFIX} Both", [self.shirts, self.denim])

		subcategory = unquote(entry["href"].split("subcategory=")[1])

		self.assertEqual(subcategory.split(","), [self.shirts, self.denim])

	def test_the_sidebar_facet_carries_every_group(self):
		self.add_entry(f"{PREFIX} Both", [self.shirts, self.denim])
		frappe.local.ls_shop_storefront_menu = None

		facets = get_category_facets("")[f"{PREFIX} Sale {self.tag}"]

		self.assertEqual([facet["item_groups"] for facet in facets], [[self.shirts, self.denim]])
