# Copyright (c) 2026, company@bwhstudios.com and Contributors
# See license.txt

"""The dashboard Pages API, and the footer picker that offers those pages as links."""

import frappe
from frappe.tests import IntegrationTestCase

from commera.api.admin.pages import delete_page, get_page, get_pages, save_page
from commera.lifestyle_shop_ecommerce.doctype.lifestyle_settings.footer.footer_preview import (
	get_footer_editor_data,
)
from commera.tests.test_order_access import make_website_user

PREFIX = "ZZ Test Page"


class TestAdminPages(IntegrationTestCase):
	def setUp(self):
		self.addCleanup(frappe.set_user, "Administrator")
		self.addCleanup(frappe.db.rollback)

	def make_page(self, suffix="", **fields):
		title = f"{PREFIX} {suffix or frappe.generate_hash(length=6)}"
		return save_page(title=title, content="<p>hello</p>", **fields)

	def find_page(self, pages, name):
		return next((row for row in pages if row["name"] == name), None)

	def test_get_pages_returns_the_url_the_dashboard_renders(self):
		created = self.make_page(route="zz-about-us")

		listing = get_pages()
		row = self.find_page(listing["pages"], created["name"])

		self.assertEqual(row["url"], "/en/page/zz-about-us")
		self.assertEqual(row["route"], "zz-about-us")
		self.assertEqual(row["published"], 1)
		self.assertEqual(listing["total"], len(listing["pages"]))
		self.assertIn("modified", row)

	def test_get_pages_search_matches_title_and_route(self):
		created = self.make_page("Searchable", route="zz-searchable-route")

		self.assertIsNotNone(self.find_page(get_pages(search="Searchable")["pages"], created["name"]))
		self.assertIsNotNone(self.find_page(get_pages(search="searchable-route")["pages"], created["name"]))
		self.assertIsNone(
			self.find_page(get_pages(search=frappe.generate_hash(length=10))["pages"], created["name"])
		)

	def test_save_page_creates_updates_then_renames_keeping_the_route(self):
		created = self.make_page("Original", route="zz-original")
		self.assertEqual(created["url"], "/en/page/zz-original")

		updated = save_page(
			name=created["name"],
			content="<p>edited</p>",
			meta_title="ZZ Meta",
			meta_description="ZZ description",
			noindex=1,
			published=0,
		)
		self.assertEqual(updated["name"], created["name"])
		self.assertEqual(updated["content"], "<p>edited</p>")
		self.assertEqual(updated["meta_title"], "ZZ Meta")
		self.assertEqual(updated["noindex"], 1)
		self.assertEqual(updated["published"], 0)

		renamed = save_page(name=created["name"], title=f"{PREFIX} Renamed")
		self.assertEqual(renamed["name"], f"{PREFIX} Renamed")
		# The live link must survive the retitle: the route is what was published, not the title.
		self.assertEqual(renamed["route"], "zz-original")
		self.assertEqual(renamed["url"], "/en/page/zz-original")
		self.assertEqual(renamed["content"], "<p>edited</p>")
		self.assertFalse(frappe.db.exists("Shop Web Page", created["name"]))
		self.assertIsNone(self.find_page(get_pages()["pages"], created["name"]))

	def test_save_page_ignores_fields_outside_the_editable_set(self):
		created = save_page(
			title=f"{PREFIX} {frappe.generate_hash(length=6)}",
			content="<p>hello</p>",
			owner="Guest",
			docstatus=2,
		)

		page = frappe.get_doc("Shop Web Page", created["name"])
		self.assertEqual(page.owner, "Administrator")
		self.assertEqual(page.docstatus, 0)

	def test_save_page_without_a_title_throws(self):
		with self.assertRaises(frappe.ValidationError):
			save_page(content="<p>hello</p>")

	def test_delete_page(self):
		created = self.make_page("Doomed")

		delete_page(created["name"])

		self.assertFalse(frappe.db.exists("Shop Web Page", created["name"]))
		with self.assertRaises(frappe.DoesNotExistError):
			get_page(created["name"])

	def test_a_website_user_cannot_write_or_delete(self):
		created = self.make_page("Guarded")
		frappe.set_user(make_website_user())

		with self.assertRaises(frappe.PermissionError):
			save_page(name=created["name"], content="<p>tampered</p>")
		with self.assertRaises(frappe.PermissionError):
			delete_page(created["name"])

	def test_a_guest_cannot_write_or_delete(self):
		created = self.make_page("Guest Guarded")
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			save_page(name=created["name"], content="<p>tampered</p>")
		with self.assertRaises(frappe.PermissionError):
			delete_page(created["name"])


class TestFooterPagePicker(IntegrationTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_the_picker_offers_shop_web_pages_and_no_web_page_docs(self):
		published = save_page(title=f"{PREFIX} Footer Linked", content="<p>hi</p>", route="zz-footer-linked")
		save_page(
			title=f"{PREFIX} Footer Draft",
			content="<p>hi</p>",
			route="zz-footer-draft",
			published=0,
		)
		web_page = frappe.get_doc(
			{
				"doctype": "Web Page",
				"title": f"{PREFIX} Core Web Page",
				"route": "zz-core-web-page",
				"published": 1,
			}
		).insert(ignore_permissions=True)

		pages = get_footer_editor_data()["pages"]
		routes = [row["route"] for row in pages]

		self.assertIn("/en/page/zz-footer-linked", routes)
		# Unpublished pages are not offered, and a core Web Page renders outside the storefront theme.
		self.assertNotIn("/en/page/zz-footer-draft", routes)
		self.assertNotIn(web_page.route, routes)
		self.assertNotIn(web_page.name, [row["name"] for row in pages])

		self.assertIn("/en/products", routes)
		self.assertEqual(
			next(row["name"] for row in pages if row["route"] == "/en/page/zz-footer-linked"),
			published["name"],
		)
