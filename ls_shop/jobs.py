import frappe
from frappe.integrations.utils import (
	create_request_log,
)
from frappe.utils import add_to_date, get_url, now_datetime


def get_cc_email():
	return frappe.get_cached_value(
		"Lifestyle Settings", "Lifestyle Settings", "cc_email"
	)


def send_order_success_acknowledgement(doc, method):
	try:
		doc_args = doc.as_dict()
		order_confirmation_template_name = frappe.get_cached_value(
			"Lifestyle Settings",
			"Lifestyle Settings",
			"order_confirmation_email_template",
		)
		email_template = frappe.get_doc(
			"Email Template", order_confirmation_template_name
		)
		message = frappe.render_template(email_template.response_, doc_args)
		subject = frappe.render_template(email_template.subject, doc_args)

		emails = frappe.get_all(
			"Portal User", {"parent": doc.customer}, ["user"], limit=1
		)
		email = emails[0].get("user", "")
		frappe.sendmail(
			recipients=[email], subject=subject, message=message, cc=[get_cc_email()]
		)
	except Exception as e:
		create_request_log(
			data=doc_args,
			service_name="send_order_success_acknowledgement",
			output=e,
			status="Failed",
		)


def send_order_cancel_acknowledgement(doc, method):
	try:
		doc_args = doc.as_dict()
		order_confirmation_template_name = frappe.get_cached_value(
			"Lifestyle Settings",
			"Lifestyle Settings",
			"order_cancellation_email_template",
		)
		email_template = frappe.get_doc(
			"Email Template", order_confirmation_template_name
		)
		message = frappe.render_template(email_template.response_, doc_args)
		subject = frappe.render_template(email_template.subject, doc_args)

		emails = frappe.get_all(
			"Portal User", {"parent": doc.customer}, ["user"], limit=1
		)
		email = emails[0].get("user", "")
		frappe.sendmail(
			recipients=[email], subject=subject, message=message, cc=[get_cc_email()]
		)
	except Exception as e:
		create_request_log(
			data=doc_args,
			service_name="send_order_cancel_acknowledgement",
			output=e,
			status="Failed",
		)


def send_product_back_in_stock_email(doc, method):
	ecommerce_warehouse = frappe.get_cached_value(
		"Lifestyle Settings", "Lifestyle Settings", "ecommerce_warehouse"
	)
	if doc.warehouse != ecommerce_warehouse:
		return
	if doc.voucher_type == "Stock Entry":
		frappe.enqueue(
			send_product_in_stock_email_stock_entry,
			doc=doc,
			warehouse=ecommerce_warehouse,
		)

	if doc.voucher_type == "Purchase Receipt":
		frappe.enqueue(
			send_product_in_stock_email_purchase_receipt,
			doc=doc,
			warehouse=ecommerce_warehouse,
		)

	if doc.voucher_type == "Stock Reconciliation":
		frappe.enqueue(
			send_product_in_stock_email_stock_reconciliation,
			doc=doc,
			warehouse=ecommerce_warehouse,
		)


def send_product_in_stock_email_stock_entry(doc, warehouse):
	voucher = frappe.get_doc("Stock Entry", doc.voucher_no)

	if not voucher.stock_entry_type == "Material Receipt":
		return

	for item in voucher.items:
		if not item.t_warehouse == warehouse:
			continue
		notify_users_if_item_in_stock(item.item_code)


def send_product_in_stock_email_purchase_receipt(doc, warehouse):
	voucher = frappe.get_doc("Purchase Receipt", doc.voucher_no)

	if not voucher.set_warehouse == warehouse:
		return

	for item in voucher.items:
		notify_users_if_item_in_stock(item.item_code)


def send_product_in_stock_email_stock_reconciliation(doc, warehouse):
	voucher = frappe.get_doc("Stock Reconciliation", doc.voucher_no)

	for item in voucher.items:
		if not item.warehouse == warehouse:
			continue
		notify_users_if_item_in_stock(item.item_code)


def notify_users_if_item_in_stock(item_code):
	color_size_item = frappe.get_all(
		"Color Size Item",
		{"item_code": item_code, "parenttype": "Style Attribute Variant"},
		limit=1,
		pluck="parent",
	)
	if not color_size_item:
		return
	style_attribute_variant = frappe.get_cached_doc(
		"Style Attribute Variant",
		color_size_item[0],
		fields=["route", "is_published", "display_name"],
	)
	if not style_attribute_variant.is_published:
		return
	item_in_stock_template_name = frappe.get_cached_value(
		"Lifestyle Settings",
		"Lifestyle Settings",
		"item_in_stock_email_template",
	)
	email_template = frappe.get_doc("Email Template", item_in_stock_template_name)
	doc_args = {
		"item_code": style_attribute_variant.display_name,
		"company": "Lifestyle",
		"website_url": get_url(
			f"{frappe.local.lang}/products/{style_attribute_variant.route}"
		),
	}
	message = frappe.render_template(email_template.response_, doc_args)
	subject = frappe.render_template(email_template.subject, doc_args)

	user_subscriptions = frappe.get_all(
		"OOS Notify Subscription",
		filters={"item": item_code, "notified": False},
		pluck="user",
	)
	for user in user_subscriptions:
		try:
			frappe.sendmail(
				recipients=[user], subject=subject, message=message, now=True
			)
			frappe.db.set_value(
				"OOS Notify Subscription",
				{"item": item_code, "user": user},
				{"notified": True},
			)
		except Exception as e:
			frappe.log_error(
				title="Error sending Item in stock email",
				message=e,
				reference_doctype="OOS Notify Subscription",
				reference_name=user,
			)


def delete_notified_oos():
	frappe.db.delete("OOS Notify Subscription", {"notified": True})


def delete_old_draft_quotations():
	# Delete draft quotations older than 6 hours
	cutoff_time = add_to_date(now_datetime(), hours=-6)

	old_drafts = frappe.get_all(
		"Quotation",
		filters={
			"docstatus": 0,
			"creation": ("<", cutoff_time),
			"order_type": "Shopping Cart",
		},
		pluck="name",
	)
	for quotation in old_drafts:
		try:
			frappe.delete_doc("Quotation", quotation)
		except Exception as e:
			frappe.log_error(
				title=frappe._("Error in deleting the quotation {0}: {1}").format(
					quotation, e
				)
			)
