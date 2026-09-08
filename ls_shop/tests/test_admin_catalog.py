# Copyright (c) 2026, company@bwhstudios.com and Contributors
# Tests for the whole-product operations in api/admin/catalog.py: what delete_product refuses and
# what a refusal costs, and whether filing a product under a collection moves the storefront too.

import os

import frappe

from ls_shop.api.admin.catalog import (
	add_products_to_collection,
	create_product,
	delete_product,
	get_product_chain,
	update_product,
)
from ls_shop.tests.test_product_onboarding import ProductOnboardingTestCase


class DeleteProductTestCase(ProductOnboardingTestCase):
	def setUp(self):
		super().setUp()
		self.colour_attribute = self.make_named_attribute("Colour", ["Crimson", "Teal"])
		self.written_files = []

	def tearDown(self):
		# The DB rolls back with the test; the bytes under public/files do not.
		for path in self.written_files:
			if os.path.exists(path):
				os.remove(path)
		super().tearDown()

	def make_named_attribute(self, label, values):
		attribute = frappe.new_doc("Item Attribute")
		attribute.attribute_name = f"Deletion {label} {self.suffix}"
		for value in values:
			attribute.append("item_attribute_values", {"attribute_value": value, "abbr": value[:3].upper()})
		attribute.insert()
		return attribute.name

	def add_product(self):
		return create_product(
			title=f"Deletion Product {frappe.generate_hash(length=6).upper()}",
			collection=self.item_group,
			option_attribute=self.colour_attribute,
			size_attribute="Size",
			option_sizes=[{"option": "Crimson", "sizes": ["S", "M"]}],
		)["name"]

	def add_photo(self, variant_name):
		"""A real file on disk, attached the way the dashboard attaches one, so a delete that ran
		too early would take the bytes with it."""
		file_doc = frappe.new_doc("File")
		file_doc.file_name = f"deletion-{frappe.generate_hash(length=8)}.txt"
		# Identical content would be deduplicated onto one file_url and one set of bytes.
		file_doc.content = frappe.generate_hash(length=32)
		file_doc.is_private = 0
		file_doc.attached_to_doctype = "Style Attribute Variant"
		file_doc.attached_to_name = variant_name
		file_doc.insert()
		self.written_files.append(file_doc.get_full_path())

		frappe.get_doc("Style Attribute Variant", variant_name).add_images([file_doc.file_url])
		return file_doc

	def order_item(self, item_code):
		"""A Sales Order Item row against the size, which is what makes a product historical. Written
		as a child row on its own so the test needs no customer, company or fiscal year."""
		frappe.get_doc(
			{
				"doctype": "Sales Order Item",
				"parenttype": "Sales Order",
				"parentfield": "items",
				"parent": f"ZZ-DELETION-ORDER-{frappe.generate_hash(length=8)}",
				"item_code": item_code,
				"item_name": item_code,
				"qty": 1,
				"rate": 10,
				"uom": "Nos",
				"conversion_factor": 1,
				"delivery_date": frappe.utils.nowdate(),
			}
		).db_insert()


class TestDeleteProduct(DeleteProductTestCase):
	def test_a_never_touched_product_leaves_nothing_behind(self):
		item_template = self.add_product()
		chain = get_product_chain(item_template)
		self.assertTrue(chain["variants"])
		self.assertTrue(chain["item_codes"])

		delete_product(item_template)

		self.assertFalse(frappe.db.exists("Item", item_template))
		for item_code in chain["item_codes"]:
			self.assertFalse(frappe.db.exists("Item", item_code))
		for variant_name in chain["variants"]:
			self.assertFalse(frappe.db.exists("Style Attribute Variant", variant_name))
		for configurator in chain["configurators"]:
			self.assertFalse(frappe.db.exists("Style Attribute Configurator", configurator))
		self.assertFalse(
			frappe.db.exists(
				"Color Size Item",
				{"parent": ["in", chain["variants"]], "parenttype": "Style Attribute Variant"},
			)
		)

	def test_an_ordered_product_is_refused_with_its_photos_untouched(self):
		"""The refusal has to fire before anything is destroyed. delete_doc runs on_trash and the
		attachment sweep BEFORE it checks links, and a rolled-back delete does not put the bytes back."""
		item_template = self.add_product()
		chain = get_product_chain(item_template)
		photo = self.add_photo(chain["variants"][0])
		self.order_item(chain["item_codes"][0])

		with self.assertRaises(frappe.ValidationError) as refusal:
			delete_product(item_template)

		self.assertIn("ordered", str(refusal.exception))
		self.assertIn("Archive", str(refusal.exception))
		self.assertTrue(frappe.db.exists("Item", item_template))
		self.assertTrue(frappe.db.exists("File", photo.name))
		self.assertTrue(os.path.exists(photo.get_full_path()))

	def test_a_viewed_product_is_refused_in_words_rather_than_as_a_link_error(self):
		"""Storefront Analytics Event.item_code is a plain Link to Item that hooks.py does not ignore on
		delete, so a merely-viewed product is link-blocked - and raw LinkExistsError explains nothing."""
		item_template = self.add_product()
		chain = get_product_chain(item_template)
		photo = self.add_photo(chain["variants"][0])
		frappe.get_doc(
			{
				"doctype": "Storefront Analytics Event",
				"event": "view_item",
				"session_id": frappe.generate_hash(length=10),
				"item_code": chain["item_codes"][0],
			}
		).insert(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError) as refusal:
			delete_product(item_template)

		# Asserted first: this is the case that used to reach the delete loop, so it is the one that
		# proves the photos outlive a refusal - the ordered case was always caught before anything ran.
		self.assertTrue(os.path.exists(photo.get_full_path()))
		self.assertTrue(frappe.db.exists("File", photo.name))
		self.assertNotIsInstance(refusal.exception, frappe.LinkExistsError)
		self.assertIn("viewed", str(refusal.exception))
		self.assertIn("Archive", str(refusal.exception))
		self.assertTrue(frappe.db.exists("Item", item_template))


class TestProductCollection(DeleteProductTestCase):
	"""Style Attribute Variant carries its own item_group, and that copy - not Item.item_group - is what
	the storefront category pages and the search index read."""

	def setUp(self):
		super().setUp()
		self.item_template = self.add_product()
		self.other_collection = self.make_item_group()

	def make_item_group(self):
		item_group = frappe.new_doc("Item Group")
		item_group.item_group_name = f"Deletion Group {frappe.generate_hash(length=6).upper()}"
		item_group.parent_item_group = "All Item Groups"
		item_group.is_group = 0
		item_group.custom_displayname = item_group.item_group_name
		item_group.insert()
		return item_group.name

	def get_variant_collections(self):
		return frappe.get_all(
			"Style Attribute Variant",
			filters={"name": ["in", get_product_chain(self.item_template)["variants"]]},
			pluck="item_group",
		)

	def test_a_bulk_move_takes_the_options_with_it(self):
		add_products_to_collection([self.item_template], self.other_collection)

		self.assertEqual(frappe.db.get_value("Item", self.item_template, "item_group"), self.other_collection)
		self.assertEqual(set(self.get_variant_collections()), {self.other_collection})

	def test_the_product_screen_moves_the_options_the_same_way(self):
		update_product(self.item_template, collection=self.other_collection)

		self.assertEqual(set(self.get_variant_collections()), {self.other_collection})

	def test_both_writers_refuse_a_collection_that_holds_other_collections(self):
		"""One answer to "is this a valid collection?": update_product used to accept a structural
		parent that add_products_to_collection refused."""
		for move in (
			lambda: add_products_to_collection([self.item_template], "All Item Groups"),
			lambda: update_product(self.item_template, collection="All Item Groups"),
		):
			with self.assertRaises(frappe.ValidationError):
				move()
