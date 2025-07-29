import frappe
from frappe.utils import flt


@frappe.whitelist()
def cancel_order(order_id: str):
	# check if can cancel
	order_doc = frappe.get_doc("Sales Order", order_id)
	validate_can_cancel(order_doc)
	if order_doc.custom_ecommerce_payment_mode != "COD":
		create_refund_payment_entry(order_id)

	order_doc.flags.ignore_permissions = True
	if order_doc.docstatus == 1:
		order_doc.cancel()
	elif order_doc.docstatus == 0:
		order_doc.submit()
		order_doc.reload()  # Ensure the document state is updated
		order_doc.cancel()


@frappe.whitelist()
def create_refund_payment_entry(order_id: str, amount: float | None = None):
	payment_entry = frappe.get_all(
		"Payment Entry Reference",
		filters={"reference_doctype": "Sales Order", "reference_name": order_id},
		fields=["parent"],
		limit=1,
	)

	if not payment_entry:
		frappe.throw(frappe._("No Payment Entry found for this Sales Order."))

	payment_entry_doc = frappe.get_doc("Payment Entry", payment_entry[0].parent)
	session_user = frappe.session.user
	frappe.set_user("Administrator")

	new_payment_entry = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": "Pay",
			"mode_of_payment": payment_entry_doc.mode_of_payment,
			"party_type": payment_entry_doc.party_type,
			"party": payment_entry_doc.party,
			"paid_from": payment_entry_doc.paid_to,
			"paid_to": payment_entry_doc.paid_from,  # Make sure refund flows back
			"paid_amount": amount if amount else payment_entry_doc.paid_amount,
			"received_amount": payment_entry_doc.paid_amount,
			"reference_no": payment_entry_doc.reference_no,
			"reference_date": frappe.utils.nowdate(),
			"remarks": f"Refund for Sales Order {order_id}",
		}
	)
	new_payment_entry.insert(ignore_permissions=True)
	new_payment_entry.submit()
	frappe.session.user = session_user
	return new_payment_entry.name


def validate_can_cancel(order_doc):
	if order_doc.docstatus > 1:
		frappe.throw(frappe._("Order already cancelled!"))

	# If already shipped, can't
	if order_doc.status == "To Bill":
		frappe.throw(frappe._("Order already shipped!"))

	# If already completed, can't
	if order_doc.status == "Completed":
		frappe.throw(frappe._("Order already delivered!"))

	if order_doc.owner != frappe.session.user:
		frappe.throw(frappe._("Action not allowed"))


@frappe.whitelist()
def get_sales_order_refund_status(order_id: str):
	order = frappe.get_doc("Sales Order", order_id)
	if order.custom_ecommerce_payment_mode == "COD":
		return {"can_refund": False}

	payment_entry = frappe.get_all(
		"Payment Entry Reference",
		filters={"reference_doctype": "Sales Order", "reference_name": order_id},
		fields=["parent"],
		limit=1,
	)
	if not payment_entry:
		return {"can_refund": False}
	payment_entry_doc = frappe.get_doc("Payment Entry", payment_entry[0].parent)

	refund_payment_entries = frappe.get_all(
		"Payment Entry",
		filters={
			"payment_type": "Pay",
			"reference_no": payment_entry_doc.reference_no,
		},
		fields=["paid_amount"],
	)

	total_refunded = sum(flt(pe.paid_amount) for pe in refund_payment_entries)

	if total_refunded >= order.rounded_total:
		return {
			"can_refund": False,
		}

	# Determine refundable balance
	only_charges = total_refunded >= order.net_total
	refundable_amount = order.rounded_total - total_refunded

	return {
		"can_refund": True,
		"only_charges": only_charges,
		"amount_refunded": total_refunded,
		"refundable_amount": refundable_amount,
	}
