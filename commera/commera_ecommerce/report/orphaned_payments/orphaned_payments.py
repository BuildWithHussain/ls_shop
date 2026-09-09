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
	payment_entry = DocType("Payment Entry")
	payment_entry_reference = DocType("Payment Entry Reference")
	gateway_payment_request = DocType("Gateway Payment Request")

	query = (
		qb.from_(payment_entry)
		.left_join(payment_entry_reference)
		.on(payment_entry_reference.parent == payment_entry.name)
		.left_join(gateway_payment_request)
		.on(gateway_payment_request.order_ref == payment_entry.reference_no)
		.select(
			payment_entry.name,
			payment_entry.paid_amount,
			payment_entry.mode_of_payment,
			payment_entry.posting_date,
			payment_entry.docstatus,
			gateway_payment_request.status.as_("gateway_status"),
		)
		.where(
			((payment_entry.docstatus == 1) & (payment_entry_reference.name.isnull()))
			| ((payment_entry.docstatus == 2) & (gateway_payment_request.status != "Refunded"))
		)
	)

	return [
		{
			"payment_entry": payment.name,
			"paid_amount": payment.paid_amount,
			"payment_mode": payment.mode_of_payment,
			"posting_date": payment.posting_date,
			"cancelled": payment.docstatus == 2,
			"refunded": payment.gateway_status == "Refunded",
		}
		for payment in query.run(as_dict=True)
	]
