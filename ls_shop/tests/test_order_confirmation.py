# Copyright (c) 2026, ivend and Contributors
# The gateway return URL: the one account page reachable with no session, after the money is taken.

import frappe
from frappe.tests import IntegrationTestCase
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from ls_shop.shop_themes.theme_resolver import load_page_controller
from ls_shop.www.account.orders import confirmation as www_confirmation

CONFIRMATION_PATH = "/en/account/orders/confirmation"
QUERY_STRING = "reference_id=cs_test_0001&payment_mode=Razorpay"
EXPECTED_LOGIN_URL = (
	"/login?redirect-to=%2Fen%2Faccount%2Forders%2Fconfirmation"
	"%3Freference_id%3Dcs_test_0001%26payment_mode%3DRazorpay"
)


def get_theme_confirmation_controller():
	theme_dir = frappe.get_app_path("ls_shop", "themes", "pixio_theme")
	return load_page_controller([theme_dir], "pages/account/orders/confirmation.html")


class TestOrderConfirmationForSignedOutShopper(IntegrationTestCase):
	def setUp(self):
		self.saved_request = getattr(frappe.local, "request", None)
		self.addCleanup(self.restore_request)
		self.addCleanup(frappe.set_user, frappe.session.user)

	def restore_request(self):
		frappe.local.request = self.saved_request

	def run_context(self, get_context, query_string=QUERY_STRING):
		# A real werkzeug request: the login URL is built from request.full_path, whose trailing separator is stripped.
		frappe.local.request = Request(
			EnvironBuilder(path=CONFIRMATION_PATH, query_string=query_string).get_environ()
		)
		context = frappe._dict()
		get_context(context)
		return context

	def test_the_www_page_offers_a_login_back_to_the_same_url(self):
		frappe.set_user("Guest")
		context = self.run_context(www_confirmation.get_context)
		self.assertEqual(context.login_url, EXPECTED_LOGIN_URL)

	def test_the_themed_page_offers_a_login_back_to_the_same_url(self):
		"""The themed copy is what the renderer serves; patching only www is invisible in a browser."""
		frappe.set_user("Guest")
		context = self.run_context(get_theme_confirmation_controller().get_context)
		self.assertEqual(context.login_url, EXPECTED_LOGIN_URL)
		# Nothing may be looked up for a shopper with no session.
		self.assertIsNone(context.get("order"))

	def test_the_reference_survives_the_round_trip_intact(self):
		"""An unencoded return URL loses everything from its first `&`, taking payment_mode with it."""
		frappe.set_user("Guest")
		login_url = self.run_context(www_confirmation.get_context).login_url

		# Read back the way the login page reads it: off its own query string.
		return_to = Request(EnvironBuilder(path=login_url).get_environ()).args["redirect-to"]
		self.assertEqual(return_to, f"{CONFIRMATION_PATH}?{QUERY_STRING}")

	def test_a_signed_in_shopper_is_never_asked_to_log_in(self):
		self.assertIsNone(self.run_context(www_confirmation.get_context).get("login_url"))
		self.assertIsNone(self.run_context(get_theme_confirmation_controller().get_context).get("login_url"))
