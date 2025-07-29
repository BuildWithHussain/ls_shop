# Copyright (c) 2025, company@bwhstudios.com and contributors
# For license information, please see license.txt

import xml.etree.ElementTree as ET

import frappe
from frappe.model.document import Document

from ls_shop.lifestyle_shop_ecommerce.doctype.telr_settings.telr_settings import TelrSettings


class TelrPaymentRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		currency_code: DF.Link | None
		customer_address: DF.Link | None
		customer_email: DF.Data | None
		customer_forenames: DF.Data | None
		customer_phone: DF.Data | None
		customer_ref: DF.Data | None
		customer_surname: DF.Data | None
		name: DF.Int | None
		payment_method: DF.Data | None
		ref_docname: DF.DynamicLink | None
		ref_doctype: DF.Link | None
		refund_amount: DF.Currency
		status: DF.Literal[
			"Pending",
			"Paid",
			"Not Paid",
			"Cancelled",
			"Expired",
			"Partially Refunded",
			"Refunded",
		]
		telr_order_ref: DF.Data | None
		telr_order_url: DF.Data | None
		transaction_class: DF.Data | None
		transaction_reference: DF.Data | None
	# end: auto-generated types

	def before_save(self):
		if not self.telr_order_ref:
			self.create_order_on_telr()

	def create_order_on_telr(self):
		telr_settings = frappe.get_cached_doc("Telr Settings")

		address = None
		if self.customer_address:
			address_doc = frappe.get_cached_doc("Address", self.customer_address)
			address = {
				"line1": address_doc.address_line1,
				"city": address_doc.city,
				"country": address_doc.country,
			}

		telr_order = telr_settings.create_session(
			self.amount,
			internal_reference_id=str(self.name),
			currency_code=self.currency_code,
			customer_details={
				"ref": self.customer_ref or "",
				"email": self.customer_email or "",
				"phone": self.customer_phone or "",
				"name": {
					"forenames": self.customer_forenames or "",
					"surname": self.customer_surname or "",
				},
				"address": address,
			},
		)

		self.telr_order_ref = telr_order["order"]["ref"]
		self.telr_order_url = telr_order["order"]["url"]

	@frappe.whitelist()
	def sync_status(self):
		telr_settings: TelrSettings = frappe.get_cached_doc("Telr Settings")
		telr_order = telr_settings.get_order_for_check(self.telr_order_ref)

		if order := telr_order.get("order"):
			status = order["status"].get("text")
			self.status = status
			self.payment_method = order.get("paymethod")

			if transaction := order.get("transaction"):
				self.transaction_reference = transaction["ref"]
				self.transaction_class = transaction["class"]
		if self.refund_amount:
			if self.amount > self.refund_amount:
				self.status = "Partially Refunded"
			elif self.amount == self.refund_amount:
				self.status = "Refunded"

		self.save()

	@frappe.whitelist()
	def refund(self, amount: float | None = None):
		self.sync_status()
		if not amount:
			amount = self.amount - self.refund_amount
		telr_settings: TelrSettings = frappe.get_cached_doc("Telr Settings")
		refund_response = telr_settings.refund_order(self.transaction_reference, amount)
		# Parse the XML response to check refund status
		root = ET.fromstring(refund_response.text)
		auth = root.find("auth")

		status = auth.find("status").text if auth is not None else None
		if status == "A":
			self.refund_amount = self.refund_amount + amount
			self.save()
			self.sync_status()
		else:
			frappe.throw(frappe._("Refund failed: Please try again later."))


def refund_payment_for_payment_entry(doc, event=None):
	if doc.mode_of_payment != "Telr" or doc.payment_type != "Pay":
		return
	payment_amount = doc.paid_amount

	frappe.get_doc("Telr Payment Request", {"telr_order_ref": doc.reference_no}).refund(
		payment_amount
	)
