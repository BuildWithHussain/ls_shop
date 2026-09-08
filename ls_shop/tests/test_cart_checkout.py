# Copyright (c) 2026, company@bwhstudios.com and Contributors
# The storefront checkout writes as the shopper, who has no Account read; see payments.save_cart_quotation.

import frappe
from frappe.tests import IntegrationTestCase

from ls_shop.api.cart import get_detail_for_cart_items, get_stock_shortfalls, validate_stock_available
from ls_shop.api.checkout import apply_shipping_rule
from ls_shop.api.payments import generate_quotation_for_cart, update_quotation_address
from ls_shop.core import _get_cart_quotation

COUNTRY = "Saudi Arabia"
IN_STOCK_QTY = 4.0
DEFAULT_RATE = 120.0
SALE_RATE = 90.0


class TestCartCheckout(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		lifestyle_settings = frappe.get_cached_doc("Lifestyle Settings")
		cls.default_price_list = lifestyle_settings.get_default_price_list()
		cls.sale_price_list = lifestyle_settings.get_sale_price_list()
		cls.warehouse = lifestyle_settings.ecommerce_warehouse

	def setUp(self):
		self.addCleanup(frappe.set_user, "Administrator")
		self.shopper = self.create_shopper()
		self.discounted_item = self.create_item(sale_rate=SALE_RATE)
		self.full_price_item = self.create_item(sale_rate=None)

	# -- fixtures ---------------------------------------------------------------------------------

	def create_shopper(self) -> str:
		"""A storefront signup: a Website User holding only the Customer role, so no Account read."""
		email = f"zz-shopper-{frappe.generate_hash(length=8)}@example.com"
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "ZZ Shopper",
				"last_name": "Checkout",
				"send_welcome_email": 0,
				"user_type": "Website User",
			}
		)
		user.append("roles", {"role": "Customer"})
		user.insert(ignore_permissions=True)
		return email

	def create_item(self, sale_rate: float | None) -> str:
		item_code = f"ZZ-CART-{frappe.generate_hash(length=8)}"
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": "ZZ Cart Item",
				"item_group": frappe.get_all("Item Group", {"is_group": 0}, pluck="name", limit=1)[0],
				"stock_uom": "Nos",
				"is_stock_item": 1,
			}
		).insert(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": item_code,
				"price_list": self.default_price_list,
				"price_list_rate": DEFAULT_RATE,
			}
		).insert(ignore_permissions=True)
		if sale_rate is not None:
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"item_code": item_code,
					"price_list": self.sale_price_list,
					"price_list_rate": sale_rate,
				}
			).insert(ignore_permissions=True)

		# Bin is how ls_shop.utils.get_available_stocks reads sellable qty; erpnext creates it the same way.
		frappe.get_doc(
			{
				"doctype": "Bin",
				"item_code": item_code,
				"warehouse": self.warehouse,
				"actual_qty": IN_STOCK_QTY,
			}
		).insert(ignore_permissions=True)
		return item_code

	def cart_line(self, item_code: str, qty: float) -> dict:
		return {"item": {"display_name": "ZZ Cart Item"}, "variant": {"item_code": item_code}, "qty": qty}

	def address_payload(self) -> dict:
		return {
			"billing_address": {
				"full_address": "1 Billing Street",
				"city": "Riyadh",
				"country": COUNTRY,
				"phone_number": "+966500000001",
				"email": self.shopper,
				"first_name": "ZZ",
				"last_name": "Shopper",
			},
			"shipping_same_as_billing": True,
		}

	# -- the blocker: every cart write happens in the shopper's own session -------------------------

	def test_shopper_cannot_read_accounts(self):
		"""Guards the tests below: without this the elevated save would be proving nothing."""
		frappe.set_user(self.shopper)
		self.assertFalse(frappe.has_permission("Account", "read"))

	def test_shopper_generates_a_quotation_for_their_cart(self):
		frappe.set_user(self.shopper)

		quotation = generate_quotation_for_cart({"items": [self.cart_line(self.discounted_item, 2)]})

		self.assertEqual(quotation.docstatus, 0)
		self.assertEqual([(row.item_code, row.qty) for row in quotation.items], [(self.discounted_item, 2)])
		self.assertEqual(quotation.contact_email, self.shopper)

	def test_shopper_saves_their_checkout_address(self):
		frappe.set_user(self.shopper)
		generate_quotation_for_cart({"items": [self.cart_line(self.discounted_item, 1)]})

		update_quotation_address(self.address_payload())

		quotation = _get_cart_quotation()
		self.assertTrue(quotation.customer_address)
		self.assertEqual(quotation.shipping_address_name, quotation.customer_address)

	def test_shopper_applies_the_shipping_rule(self):
		frappe.set_user(self.shopper)
		generate_quotation_for_cart({"items": [self.cart_line(self.discounted_item, 1)]})

		apply_shipping_rule()

		self.assertEqual(_get_cart_quotation().docstatus, 0)

	def test_the_shopper_session_survives_the_elevated_save(self):
		"""set_user() mutates local.session in place; a restore that round-trips it logs the shopper out."""
		frappe.set_user(self.shopper)
		session_before = frappe.local.session.copy()

		generate_quotation_for_cart({"items": [self.cart_line(self.discounted_item, 1)]})

		self.assertEqual(frappe.session.user, self.shopper)
		self.assertEqual(frappe.local.session, session_before)

	# -- stock ------------------------------------------------------------------------------------

	def test_a_cart_beyond_available_stock_is_refused(self):
		frappe.set_user(self.shopper)

		with self.assertRaises(frappe.ValidationError):
			generate_quotation_for_cart({"items": [self.cart_line(self.discounted_item, 9999)]})

		self.assertFalse(frappe.get_all("Quotation", {"contact_email": self.shopper, "docstatus": 0}))

	def test_a_cart_within_available_stock_is_accepted(self):
		frappe.set_user(self.shopper)
		validate_stock_available([self.cart_line(self.discounted_item, IN_STOCK_QTY)])

		self.assertEqual(get_stock_shortfalls([self.cart_line(self.discounted_item, IN_STOCK_QTY)]), [])

	def test_the_shortfall_names_the_item_and_both_quantities(self):
		shortfalls = get_stock_shortfalls([self.cart_line(self.discounted_item, 9)])

		self.assertEqual(shortfalls, ["ZZ Cart Item - Requested: 9, In Stock: 4"])

	# -- pricing ----------------------------------------------------------------------------------

	def test_an_item_with_no_sale_row_falls_back_to_the_default_price(self):
		detail = get_detail_for_cart_items([self.cart_line(self.full_price_item, 1)])

		self.assertEqual(detail["stock_data"][self.full_price_item]["sale_price"], DEFAULT_RATE)
		self.assertEqual(detail["stock_data"][self.full_price_item]["default_price"], DEFAULT_RATE)

	def test_an_item_with_a_sale_row_keeps_its_sale_price(self):
		detail = get_detail_for_cart_items([self.cart_line(self.discounted_item, 1)])

		self.assertEqual(detail["stock_data"][self.discounted_item]["sale_price"], SALE_RATE)
		self.assertEqual(detail["stock_data"][self.discounted_item]["default_price"], DEFAULT_RATE)
