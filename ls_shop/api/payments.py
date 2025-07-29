from enum import StrEnum

import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.pricing_rule.utils import validate_coupon_code
from erpnext.selling.doctype.quotation.quotation import _make_sales_order
from frappe.utils import getdate
from webshop.webshop.shopping_cart.cart import (
	_get_cart_quotation,
	get_cart_quotation,
)

from ls_shop.utils import get_cod_configuration


class PaymentMode(StrEnum):
	TELR = "telr"
	TABBY = "tabby"
	COD = "cod"


@frappe.whitelist()
def initiate_checkout_with_mode(payment_mode: PaymentMode):
	lifestyle_settings = frappe.get_cached_doc("Lifestyle Settings")
	if payment_mode not in set(PaymentMode) or not lifestyle_settings.get(
		f"{payment_mode}_enabled"
	):
		frappe.throw(frappe._("Please select a valid payment mode."))

	quotation = _get_cart_quotation()
	update_delivery_charges(quotation)
	customer_contact = frappe.db.get_value(
		"Contact",
		quotation.contact_person,
		["email_id", "first_name", "last_name"],
		as_dict=True,
	)

	customer_phone = frappe.db.get_value(
		"Contact Phone",
		{"parent": quotation.contact_person, "parenttype": "Contact", "idx": 1},
		"phone",
	)
	payment_request = None
	if payment_mode == PaymentMode.TELR:
		payment_request = frappe.get_doc(
			{
				"doctype": "Telr Payment Request",
				"amount": quotation.rounded_total,
				"currency_code": "SAR"
				if frappe.conf.developer_mode
				else quotation.currency,
				"ref_doctype": quotation.doctype,
				"ref_docname": quotation.name,
				"customer_ref": quotation.party_name,
				"customer_phone": customer_phone,
				"customer_forenames": customer_contact.first_name,
				"customer_surname": customer_contact.last_name,
				"customer_email": customer_contact.email_id,
				"customer_address": quotation.customer_address,
			}
		).insert()  # TODO: check for permissions with a normal user

	if payment_mode == PaymentMode.TABBY:
		payment_request = frappe.get_doc(
			{
				"doctype": "Tabby Payment Request",
				"amount": quotation.rounded_total,
				"currency_code": "SAR"
				if frappe.conf.developer_mode
				else quotation.currency,
				"ref_doctype": quotation.doctype,
				"ref_docname": quotation.name,
				"customer_ref": quotation.party_name,
				"customer_phone": customer_phone,
				"customer_name": quotation.customer_name,
				"customer_email": customer_contact.email_id,
				"customer_address": quotation.customer_address,
			}
		).insert(ignore_permissions=True)

	return {"payment_request": payment_request}


@frappe.whitelist()
def generate_quotation_for_cart(cart: dict):
	if len(cart.get("items", [])) < 1:
		frappe.throw(frappe._("Can't checkout with empty cart"))
	cart_quotation = get_quotation_for_cart(cart)
	remove_coupon_code()
	return cart_quotation


def get_quotation_for_cart(cart: dict):
	unsaved_quotation_doc = _get_cart_quotation()
	sale_price_list = frappe.get_cached_value(
		"Lifestyle Settings", "Lifestyle Settings", "sale_price_list"
	)
	ecommerce_warehouse = frappe.get_cached_value(
		"Lifestyle Settings", "Lifestyle Settings", "ecommerce_warehouse"
	)
	unsaved_quotation_doc.selling_price_list = sale_price_list
	unsaved_quotation_doc.items = []
	for item in cart["items"]:
		unsaved_quotation_doc.append(
			"items",
			{
				"item_code": item["variant"]["item_code"],
				"qty": item["qty"],
				"warehouse": ecommerce_warehouse,
			},
		)
	unsaved_quotation_doc.flags.ignore_permissions = True
	unsaved_quotation_doc.save()
	# Remove any existing coupon code
	_remove_coupon_code(unsaved_quotation_doc)
	set_charges(unsaved_quotation_doc)
	return unsaved_quotation_doc.save()


def set_charges(quotation):
	shipping_rule = frappe.get_cached_value(
		"Lifestyle Settings", "Lifestyle Settings", "shipping_rule"
	)
	if shipping_rule:
		quotation.shipping_rule = shipping_rule
		quotation.run_method("apply_shipping_rule")
		quotation.run_method("calculate_taxes_and_totals")


def set_cod_charges(quotation):
	cod_charges_applicable_below, cod_charge = get_cod_configuration()
	account_head = frappe.get_cached_value(
		"Lifestyle Settings", "Lifestyle Settings", "charge_account_head"
	)
	if not cod_charges_applicable_below or not cod_charge:
		return
	if cod_charges_applicable_below < quotation.rounded_total:
		return
	if not account_head:
		frappe.throw("Please select a valid account for cod charges.")

	cod_charge = {
		"doctype": "Sales Taxes and Charges",
		"description": " Cash on Delivery Charges",
		"charge_type": "Actual",
		"account_head": account_head,
		"tax_amount": cod_charge,
	}
	quotation.append("taxes", cod_charge)
	quotation.calculate_taxes_and_totals()
	quotation.flags.ignore_permissions = True
	quotation.save()


@frappe.whitelist()
def update_quotation_address(address: dict):
	quotation = _get_cart_quotation()
	update_quotation_payment_terms_due_date(quotation)
	# Handle Store Pickup
	if address.get("is_store_pickup", False):
		quotation.custom_store = address.get("store_pickup_warehouse", "")
		quotation.custom_is_store_pickup = True
		quotation.save(ignore_permissions=True)

		return {
			"message": "Addresses updated successfully",
			"success": True,
		}
	quotation.custom_is_store_pickup = False
	quotation.custom_store = ""

	if address.get("billing_address", {}).get("is_saved"):
		billing_address_name = address.get("billing_address", {}).get("address_id")
	else:  # New Billing Address
		billing_address_doc = add_billing_address(quotation.party_name, address)
		billing_address_name = billing_address_doc.name

	quotation.customer_address = billing_address_name  # Link billing address

	# Handle Shipping Address
	if address.get("shipping_same_as_billing"):  # Use correct key for matching
		shipping_address_name = billing_address_name
	elif address.get("shipping_address", {}).get("is_saved"):
		shipping_address_name = address.get("shipping_address", {}).get("address_id")
	else:  # New Shipping Address
		shipping_address_doc = add_shipping_address(quotation.party_name, address)
		shipping_address_name = shipping_address_doc.name

	quotation.shipping_address_name = shipping_address_name  # Link shipping address

	# Handle Contact (Add Phone Number)
	contact = frappe.get_doc("Contact", quotation.contact_person)
	existing_phones = {entry.phone for entry in contact.phone_nos}

	# Add Billing Phone if not in existing contact
	billing_phone = address.get("billing_address", {}).get("phone_number")
	if billing_phone and billing_phone not in existing_phones:
		contact.append("phone_nos", {"phone": billing_phone})

	# Add Shipping Phone if not in existing contact
	shipping_phone = address.get("shipping_address", {}).get("phone_number")
	if shipping_phone and shipping_phone not in existing_phones:
		contact.append("phone_nos", {"phone": shipping_phone})

	contact.save(ignore_permissions=True)
	quotation.save(ignore_permissions=True)

	return {
		"message": "Addresses updated successfully",
		"success": True,
	}


@frappe.whitelist()
def confirm_payment(payment_mode: PaymentMode, reference_id: str):
	if payment_mode == payment_mode.COD:
		submit_quotation_and_create_order(reference_id, payment_mode)
		return {"status": "Paid"}

	if payment_mode == PaymentMode.TELR:
		payment_request = frappe.get_doc("Telr Payment Request", int(reference_id))
		payment_request.sync_status()

		if payment_request.status == "Paid":
			quote_name = payment_request.ref_docname
			submit_quotation_and_create_order(
				quote_name, payment_mode, payment_request.telr_order_ref
			)
		return payment_request

	if payment_mode == PaymentMode.TABBY:
		payment_request = frappe.get_doc(
			"Tabby Payment Request", {"tabby_payment_id": reference_id}
		)
		payment_request.sync_status()

		if payment_request.status == "AUTHORIZED":
			quote_name = payment_request.ref_docname
			payment_request.capture_payment()
			submit_quotation_and_create_order(
				quote_name, payment_mode, payment_request.tabby_order_ref
			)

		return payment_request


def submit_quotation_and_create_order(
	quote_name: str, payment_mode: PaymentMode, payment_reference: str = ""
):
	session_user = frappe.session.user
	quotation_doc = frappe.get_doc("Quotation", quote_name)
	if payment_mode == payment_mode.COD:
		set_cod_charges(quotation_doc)
	quotation_doc.flags.ignore_permissions = True
	quotation_doc.submit()

	so = _make_sales_order(quote_name, ignore_permissions=True)
	so.custom_ecommerce_payment_mode = (
		payment_mode.title()
		if not payment_mode == payment_mode.COD
		else payment_mode.upper()
	)
	so.flags.ignore_permissions = True
	so.insert()

	if payment_mode != payment_mode.COD:
		so.submit()
		payment_request_doctype = (
			"Telr Payment Request"
			if payment_mode == PaymentMode.TELR
			else "Tabby Payment Request"
		)
		payment_order_ref_field = (
			"telr_order_ref" if payment_mode == PaymentMode.TELR else "tabby_order_ref"
		)
		payment_request = frappe.get_doc(
			payment_request_doctype, {payment_order_ref_field: payment_reference}
		)
		payment_request.flags.ignore_permissions = True
		payment_request.ref_docname = so.name
		payment_request.ref_doctype = "Sales Order"
		payment_request.save()
		frappe.set_user("Administrator")
		pe = get_payment_entry(
			"Sales Order", so.name, reference_date=frappe.utils.today()
		)
		pe.flags.ignore_permissions = True
		pe.mode_of_payment = payment_mode.title()
		pe.reference_no = payment_reference
		pe.insert().submit()
	frappe.session.user = session_user


@frappe.whitelist()
def apply_coupon_code(applied_code):
	quotation = True
	if not applied_code:
		frappe.throw(frappe._("Please enter a coupon code"))
	coupon_name = frappe.db.get_value(
		"Coupon Code", {"coupon_code": applied_code}, "name"
	)
	if not coupon_name:
		frappe.throw(frappe._("Please enter a valid coupon code"))
	validate_coupon_code(coupon_name)
	quotation = _get_cart_quotation()
	quotation.coupon_code = coupon_name
	quotation.flags.ignore_permissions = True
	quotation.save()
	return {"success": True, "message": frappe._("Coupon code applied successfully")}


@frappe.whitelist()
def remove_coupon_code():
	quotation = _get_cart_quotation()
	_remove_coupon_code(quotation)


def _remove_coupon_code(quotation):
	quotation.coupon_code = ""
	quotation.items = [item for item in quotation.items if not item.get("is_free_item")]
	for item in quotation.items:
		item.discount_percentage = 0
		item.discount_amount = 0
		item.distributed_discount_amount = 0
		item.rate = item.price_list_rate
	quotation.flags.ignore_permissions = True
	quotation.calculate_taxes_and_totals()
	quotation.save()
	quotation.discount_amount = 0
	quotation.save()


def add_billing_address(party_name, address):
	address_doc = frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": f"Shop Billing Address - {party_name}",
			"address_type": "Billing",
			"city": address.get("billing_address", {}).get("city"),
			"country": address.get("billing_address", {}).get("country"),
			"address_line1": address.get("billing_address", {}).get("full_address"),
			"address_line2": address.get("billing_address", {}).get("landmark"),
			"pincode": address.get("billing_address", {}).get("po_box"),
			"phone": address.get("billing_address", {}).get("phone_number"),
			"email_id": address.get("billing_address", {}).get("email"),
			"first_name": address.get("billing_address", {}).get("first_name"),
			"last_name": address.get("billing_address", {}).get("last_name"),
		}
	).insert(ignore_permissions=True)
	return address_doc


def add_shipping_address(party_name, address):
	address_doc = frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": f"Shop Shipping Address - {party_name}",
			"address_type": "Shipping",
			"city": address.get("shipping_address", {}).get("city"),
			"country": address.get("shipping_address", {}).get("country"),
			"address_line1": address.get("shipping_address", {}).get("full_address"),
			"address_line2": address.get("shipping_address", {}).get("landmark"),
			"pincode": address.get("shipping_address", {}).get("po_box"),
			"phone": address.get("shipping_address", {}).get("phone_number"),
			"email_id": address.get("shipping_address", {}).get("email"),
			"first_name": address.get("shipping_address", {}).get("first_name"),
			"last_name": address.get("shipping_address", {}).get("last_name"),
		}
	).insert(ignore_permissions=True)
	return address_doc


def update_quotation_payment_terms_due_date(quotation):
	today = getdate()
	for term in quotation.get("payment_schedule", []):
		if term.due_date and term.due_date < today:
			term.due_date = today


def update_delivery_charges(quotation):
	if quotation.custom_is_store_pickup:
		quotation.shipping_rule = None
		quotation.taxes = []
		quotation.calculate_taxes_and_totals()
		quotation.save(ignore_permissions=True)
	else:
		set_charges(quotation)
		quotation.save(ignore_permissions=True)
