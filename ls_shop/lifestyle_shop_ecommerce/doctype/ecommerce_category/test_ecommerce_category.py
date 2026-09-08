# Copyright (c) 2025, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from ls_shop.tests import delete_menu_entries

# Item Group.custom_displayname is mandatory here, so core's link-dependency loader cannot build its records.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Item Group", "Brand"]

PREFIX = "Test EC"


class TestEcommerceCategory(IntegrationTestCase):
	def setUp(self):
		self.tag = frappe.generate_hash(length=8)

	def tearDown(self):
		delete_menu_entries({"name": ["like", f"{PREFIX}%"]})

	def make_category(self, link_type=None, link_url=None):
		return frappe.get_doc(
			{
				"doctype": "Ecommerce Category",
				"category_name": f"{PREFIX} {self.tag}",
				"display_name": f"{PREFIX} {self.tag}",
				"enabled": 1,
				"link_type": link_type or "",
				"link_url": link_url,
			}
		).insert()

	def test_a_script_scheme_url_is_refused_on_a_direct_write(self):
		"""The navbar editor screens URLs, but a Desk form write or a REST insert never goes near it.

		Frappe's Jinja has autoescaping off and the menu writes `href` raw, so a `javascript:` entry is stored XSS.
		"""
		for unsafe_url in ("javascript:alert(1)", "data:text/html,<script>alert(1)</script>"):
			with self.subTest(url=unsafe_url), self.assertRaises(frappe.ValidationError):
				self.make_category("URL", unsafe_url)

	def test_an_http_url_and_a_relative_path_are_both_accepted(self):
		category = self.make_category("URL", "https://example.com/blog")
		self.assertEqual(category.link_url, "https://example.com/blog")

		category.link_url = "/en/products"
		category.save()
		self.assertEqual(category.link_url, "/en/products")

	def test_a_url_is_required_when_the_link_type_says_url(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_category("URL", "")

	def test_a_stale_url_is_dropped_when_the_link_type_moves_off_url(self):
		category = self.make_category("URL", "https://example.com/blog")

		category.link_type = ""
		category.save()

		self.assertIsNone(category.link_url)
