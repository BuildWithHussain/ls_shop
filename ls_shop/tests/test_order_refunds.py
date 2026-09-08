# Copyright (c) 2026, company@bwhstudios.com and Contributors
# Refunds are the money path: these run the real capture chain (Sales Order -> Sales Invoice ->
# Payment Entry) rather than hand-building a Payment Entry, because the bug under test was that the
# refund lookup never matched what that chain actually writes.

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils.data import flt
from frappe.utils.file_lock import release_document_locks

from ls_shop.api.orders import (
	create_refund_payment_entry,
	get_order_payments,
	get_sales_order_refund_status,
)
from ls_shop.api.payments import create_sales_invoice
from ls_shop.tests.test_admin_orders import COMPANY, make_test_sales_order

GATEWAY = "ZZ Refund Gateway"
CASH_ACCOUNT = "Cash - LSD"


class TestOrderRefunds(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.ensure_mode_of_payment()

	@classmethod
	def tearDownClass(cls):
		super().tearDownClass()
		# The Mode of Payment is created outside the per-test rollback, so it has to be swept up here.
		frappe.db.rollback()
		frappe.delete_doc("Mode of Payment", GATEWAY, ignore_missing=True, force=True)
		frappe.db.commit()

	@classmethod
	def ensure_mode_of_payment(cls):
		"""bwh_payments only mirrors a payout when the mode of payment is named after the gateway."""
		if not frappe.db.exists("Mode of Payment", GATEWAY):
			frappe.get_doc(
				{"doctype": "Mode of Payment", "mode_of_payment": GATEWAY, "enabled": 1, "type": "Bank"}
			).insert(ignore_permissions=True)

		# get_default_bank_cash_account refuses to post a Payment Entry without this row.
		mode_of_payment = frappe.get_doc("Mode of Payment", GATEWAY)
		if not any(row.company == COMPANY for row in mode_of_payment.accounts):
			mode_of_payment.append("accounts", {"company": COMPANY, "default_account": CASH_ACCOUNT})
			mode_of_payment.save(ignore_permissions=True)
		frappe.db.commit()

	def make_paid_order(self):
		"""An order billed and captured the way checkout does it, gateway session and all."""
		sales_order = make_test_sales_order()
		sales_order.db_set("custom_ecommerce_payment_mode", GATEWAY, update_modified=False)
		self.gateway_reference = f"zz_session_{frappe.generate_hash(length=10)}"
		create_sales_invoice(sales_order, GATEWAY, flt(sales_order.grand_total), self.gateway_reference)
		return sales_order.reload()

	def make_cod_order(self):
		sales_order = make_test_sales_order()
		sales_order.db_set("custom_ecommerce_payment_mode", "COD", update_modified=False)
		return sales_order.reload()

	def test_a_prepaid_order_is_refundable(self):
		"""The regression: the capture is booked against the Sales Invoice, so a Payment Entry
		Reference lookup keyed on "Sales Order" found nothing and reported every order unrefundable."""
		sales_order = self.make_paid_order()

		self.assertEqual(
			frappe.get_all(
				"Payment Entry Reference",
				filters={"reference_doctype": "Sales Order", "reference_name": sales_order.name},
			),
			[],
			"the old lookup should still match nothing - that is the bug",
		)

		status = get_sales_order_refund_status(sales_order.name)

		self.assertTrue(status["can_refund"])
		self.assertIsNone(status["reason"])
		self.assertAlmostEqual(status["refundable_amount"], flt(sales_order.grand_total))
		self.assertEqual(status["currency"], sales_order.currency)

	def test_the_capture_is_found_through_the_sales_invoice(self):
		sales_order = self.make_paid_order()

		payments = get_order_payments(sales_order.name)

		self.assertEqual(len(payments), 1)
		self.assertEqual(payments[0].reference_no, self.gateway_reference)
		self.assertEqual(payments[0].mode_of_payment, GATEWAY)

	def test_a_cod_order_reports_a_reason_instead_of_raising(self):
		sales_order = self.make_cod_order()

		status = get_sales_order_refund_status(sales_order.name)

		self.assertFalse(status["can_refund"])
		self.assertIn("delivery", status["reason"].lower())
		self.assertEqual(status["refundable_amount"], 0.0)

	def test_an_unpaid_order_reports_a_reason_instead_of_raising(self):
		sales_order = make_test_sales_order()
		sales_order.db_set("custom_ecommerce_payment_mode", GATEWAY, update_modified=False)

		status = get_sales_order_refund_status(sales_order.name)

		self.assertFalse(status["can_refund"])
		self.assertIn("no payment", status["reason"].lower())

	def test_a_full_refund_creates_a_matching_pay_payment_entry(self):
		sales_order = self.make_paid_order()

		refund = frappe.get_doc("Payment Entry", create_refund_payment_entry(sales_order.name))

		self.assertEqual(refund.payment_type, "Pay")
		self.assertEqual(refund.docstatus, 1)
		self.assertAlmostEqual(flt(refund.paid_amount), flt(sales_order.grand_total))
		# Both are load-bearing for bwh_payments.refund_on_payment_entry, which will not mirror the
		# payout to the gateway unless the reference_no and the mode of payment both match.
		self.assertEqual(refund.reference_no, self.gateway_reference)
		self.assertEqual(refund.mode_of_payment, GATEWAY)

	def test_refunding_more_than_was_paid_is_refused(self):
		sales_order = self.make_paid_order()

		with self.assertRaises(frappe.ValidationError):
			create_refund_payment_entry(sales_order.name, amount=flt(sales_order.grand_total) + 0.01)

	def test_a_second_refund_after_a_full_refund_is_refused(self):
		sales_order = self.make_paid_order()
		create_refund_payment_entry(sales_order.name)
		# A real second refund arrives in a separate request, whose commit released the first one's
		# lock; this test never commits, so it has to stand in for that.
		release_document_locks()

		status = get_sales_order_refund_status(sales_order.name)
		self.assertFalse(status["can_refund"])
		self.assertIn("already", status["reason"].lower())

		with self.assertRaises(frappe.ValidationError):
			create_refund_payment_entry(sales_order.name)

	def test_a_partial_refund_leaves_the_balance_refundable(self):
		sales_order = self.make_paid_order()
		grand_total = flt(sales_order.grand_total)
		create_refund_payment_entry(sales_order.name, amount=grand_total / 2)

		status = get_sales_order_refund_status(sales_order.name)

		self.assertTrue(status["can_refund"])
		self.assertAlmostEqual(status["refundable_amount"], grand_total / 2)
		self.assertAlmostEqual(status["amount_refunded"], grand_total / 2)

	def test_a_refund_on_another_order_is_not_counted(self):
		"""Two orders paid through the same gateway carry different sessions; matching on the mode of
		payment alone would let one order's payout make another look refunded."""
		refunded_order = self.make_paid_order()
		create_refund_payment_entry(refunded_order.name)
		other_order = self.make_paid_order()

		status = get_sales_order_refund_status(other_order.name)

		self.assertTrue(status["can_refund"])
		self.assertEqual(status["amount_refunded"], 0.0)
