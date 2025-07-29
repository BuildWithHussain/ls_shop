# Copyright (c) 2025, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb
from frappe.query_builder import DocType


def execute(filters=None):
	columns, data = get_columns(), get_data()
	return columns, data


def get_columns():
	columns = [
		{
			"label": _("Payment Entry"),
			"fieldname": "payment_entry",
			"fieldtype": "Link",
			"options": "Payment Entry",
			"width": 200,
		},
		{
			"label": _("Paid Amount"),
			"fieldname": "paid_amount",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Payment Mode"),
			"fieldname": "payment_mode",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": _("Cancelled"),
			"fieldname": "cancelled",
			"fieldtype": "Bool",
			"width": 120,
		},
		{
			"label": _("Refunded"),
			"fieldname": "refunded",
			"fieldtype": "Bool",
			"width": 120,
		},
	]
	return columns


def get_data():
	data = []
	PaymentEntry = DocType("Payment Entry")
	PaymentEntryReference = DocType("Payment Entry Reference")
	Telr_payment_request = DocType("Telr Payment Request")
	tabby_payment_request = DocType("Tabby Payment Request")

	orphaned_payments = (
		qb.from_(PaymentEntry)
		.left_join(PaymentEntryReference)
		.on(PaymentEntryReference.parent == PaymentEntry.name)
		.left_join(Telr_payment_request)
		.on(Telr_payment_request.telr_order_ref == PaymentEntry.reference_no)
		.left_join(tabby_payment_request)
		.on(tabby_payment_request.tabby_order_ref == PaymentEntry.reference_no)
		.select(
			PaymentEntry.name,
			PaymentEntry.paid_amount,
			PaymentEntry.mode_of_payment,
			PaymentEntry.posting_date,
			PaymentEntry.docstatus,
			Telr_payment_request.status.as_("telr_status"),
			tabby_payment_request.status.as_("tabby_status"),
		)
		.where(
			((PaymentEntry.docstatus == 1) & (PaymentEntryReference.name.isnull()))
			| (
				(PaymentEntry.docstatus == 2)
				& (Telr_payment_request.status != "Refunded")
			)
			| (
				(PaymentEntry.docstatus == 2)
				& (tabby_payment_request.status != "REFUND")
			)
		)
	).run(as_dict=True)
	for payment in orphaned_payments:
		data.append(
			{
				"payment_entry": payment.name,
				"paid_amount": payment.paid_amount,
				"payment_mode": payment.mode_of_payment,
				"posting_date": payment.posting_date,
				"cancelled": payment.docstatus == 2,
				"refunded": (
					payment.telr_status == "Refunded"
					or payment.tabby_status == "REFUND"
				),
			}
		)
	return data
