from contextlib import contextmanager

import frappe
from bwh_payments.bwh_payments.utils import resolve_payment_mode
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.pricing_rule.utils import validate_coupon_code
from frappe import _
from frappe.utils import getdate
from frappe.utils.data import flt

from commera.analytics.events import log_purchase, set_attribution_fields
from commera.api.cart import validate_stock_available
from commera.api.shipping import (
	clear_delivery_option,
	copy_delivery_option_to_order,
	reprice_selected_option,
)
from commera.core import _get_cart_quotation
from commera.utils import COD_CHARGE_DESCRIPTION, get_cod_configuration

# ERPNext moved its transaction mappers to a sibling `mapper` module; both layouts are in the wild.
try:
	from erpnext.selling.doctype.quotation.mapper import _make_sales_order
except ImportError:
	from erpnext.selling.doctype.quotation.quotation import _make_sales_order

try:
	from erpnext.selling.doctype.sales_order.mapper import make_sales_invoice
except ImportError:
	from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

COD_PAYMENT_MODE = "COD"


def is_cod(payment_mode: str | None) -> bool:
	return (payment_mode or "").strip().casefold() == COD_PAYMENT_MODE.casefold()


def get_charge_amount(quotation) -> float:
	# rounded_total is 0 when rounding is disabled on the document; grand_total is the billed figure then.
	return flt(quotation.rounded_total) or flt(quotation.grand_total)


def get_open_gateway_payment_request(quotation_name: str) -> str | None:
	"""The Gateway Payment Request still holding this cart, if the shopper has a checkout in flight."""
	return frappe.db.get_value(
		"Gateway Payment Request",
		{
			"ref_doctype": "Quotation",
			"ref_docname": quotation_name,
			"status": ["in", ("Pending", "Paid")],
		},
		"name",
	)


def validate_cart_is_not_in_checkout(quotation_name: str):
	"""Refuse to edit a cart that a gateway session is already priced against."""
	# ponytail: an abandoned checkout keeps the cart locked until the gateway expires the session and a
	# status sync moves it off Pending; give the shopper a "cancel this payment" action if that bites.
	if not quotation_name or not get_open_gateway_payment_request(quotation_name):
		return

	frappe.throw(
		_("A payment is already in progress for this order. Finish or cancel it before changing your cart."),
		title=_("Checkout In Progress"),
	)


def get_confirmation_url(reference_id: str, payment_mode: str | None = None) -> str:
	url = f"/{frappe.local.lang}/account/orders/confirmation?reference_id={reference_id}"
	if payment_mode:
		url = f"{url}&payment_mode={payment_mode}"
	return url


@frappe.whitelist()
def initiate_checkout_with_mode(payment_mode: str):
	quotation = _get_cart_quotation()
	validate_cart_is_not_in_checkout(quotation.name)
	update_delivery_charges(quotation)

	if is_cod(payment_mode):
		if not frappe.db.get_single_value("Commera Settings", "cod_enabled"):
			frappe.throw(_("Cash on delivery is not available."))
		return {"order_url": get_confirmation_url(quotation.name, payment_mode=COD_PAYMENT_MODE)}

	gateway = resolve_payment_mode(payment_mode)
	if not gateway:
		frappe.throw(_("Please select a valid payment mode."))

	customer_contact = (
		frappe.db.get_value(
			"Contact",
			quotation.contact_person,
			["email_id", "first_name", "last_name"],
			as_dict=True,
		)
		or frappe._dict()
	)
	customer_phone = frappe.db.get_value(
		"Contact Phone",
		{"parent": quotation.contact_person, "parenttype": "Contact", "idx": 1},
		"phone",
	)

	payment_request = frappe.get_doc(
		{
			"doctype": "Gateway Payment Request",
			"gateway": gateway,
			"amount": get_charge_amount(quotation),
			"currency_code": quotation.currency,
			"company": quotation.company,
			"ref_doctype": quotation.doctype,
			"ref_docname": quotation.name,
			"customer_ref": quotation.party_name,
			"customer_phone": customer_phone,
			"customer_forenames": customer_contact.first_name,
			"customer_surname": customer_contact.last_name,
			"customer_email": customer_contact.email_id,
			"customer_address": quotation.customer_address,
		}
	).insert(ignore_permissions=True)

	return {"order_url": payment_request.order_url}


def gateway_mode_of_payment(gateway: str) -> str:
	mode_of_payment = frappe.db.get_value("Mode of Payment", (gateway or "").strip(), "name")
	if not mode_of_payment:
		frappe.throw(_("No Mode of Payment found matching gateway {0}").format(frappe.bold(gateway)))
	return mode_of_payment


@contextmanager
def system_user_session():
	"""Place the accounting documents as Administrator, then hand the session back.

	ERPNext's get_party_account checks frappe.has_permission directly, so no ignore_permissions reaches it.
	"""
	# frappe.set_user() mutates frappe.local.session in place, stamping "sid" with the username and wiping
	# local.session.data, so restore the snapshot verbatim rather than calling it again for the shopper.
	live_session_snapshot = frappe.local.session.copy()
	try:
		# Audited: the docstring above and the snapshot restore below are why this is safe.
		frappe.set_user("Administrator")  # nosemgrep: frappe-semgrep-rules.rules.security.frappe-setuser
		yield
	finally:
		frappe.local.session.update(live_session_snapshot)
		frappe.local.cache = {}
		frappe.local.role_permissions = {}
		frappe.local.user_perms = None


def save_cart_quotation(quotation):
	"""Persist the shopper's own cart, elevated. Saving resolves the receivable account, and ERPNext's
	account_perm_check calls frappe.has_permission("Account") directly - no ignore_permissions reaches it."""
	with system_user_session():
		quotation.flags.ignore_permissions = True
		return quotation.save()


def stamp_order_owner(sales_order, shopper: str) -> None:
	"""Hand the order back to the shopper who bought it: insert() runs as Administrator (see
	system_user_session), and every post-purchase screen gates on owner == frappe.session.user."""
	if not shopper or shopper == sales_order.owner:
		return
	sales_order.db_set("owner", shopper, update_modified=False)


def place_order(quotation, payment_mode: str, gateway_amount=None, gateway_reference=None):
	"""Submit the cart and bill it. Called once per payment; the Quotation docstatus enforces that."""
	shopper = frappe.session.user
	with system_user_session():
		fix_payment_schedule_dates(quotation)
		quotation.flags.ignore_permissions = True
		quotation.submit()

		sales_order = _make_sales_order(quotation.name, ignore_permissions=True)
		sales_order.custom_ecommerce_payment_mode = payment_mode
		copy_delivery_option_to_order(quotation.name, sales_order)
		fix_payment_schedule_dates(sales_order)
		set_attribution_fields(sales_order)
		sales_order.flags.ignore_permissions = True
		sales_order.insert()
		sales_order.submit()

		if flt(gateway_amount) > 0:
			create_sales_invoice(sales_order, payment_mode, flt(gateway_amount), gateway_reference)

	# Outside the switch: log_purchase stamps frappe.session.user, so Administrator would own every purchase.
	stamp_order_owner(sales_order, shopper)
	log_purchase(sales_order)
	return sales_order


def create_sales_invoice(sales_order, payment_mode: str, paid_amount: float, reference_no: str | None):
	sales_invoice = make_sales_invoice(sales_order.name, ignore_permissions=True)
	sales_invoice.flags.ignore_permissions = True
	sales_invoice.insert()
	sales_invoice.submit()
	create_payment_entry(sales_invoice, payment_mode, paid_amount, reference_no)
	return sales_invoice


def create_payment_entry(sales_invoice, payment_mode: str, paid_amount: float, reference_no: str | None):
	# Never allocate more than the invoice owes, whatever the gateway reported.
	allocated = min(flt(paid_amount), flt(sales_invoice.outstanding_amount))
	if allocated <= 0:
		return None

	payment_entry = get_payment_entry("Sales Invoice", sales_invoice.name, party_amount=allocated)
	payment_entry.mode_of_payment = gateway_mode_of_payment(payment_mode)
	if reference_no:
		# Load-bearing: bwh_payments matches a refund Payment Entry back to its gateway session on this.
		payment_entry.reference_no = reference_no
		payment_entry.reference_date = getdate()

	bank = get_default_bank_cash_account(
		sales_invoice.company, "Cash", mode_of_payment=payment_entry.mode_of_payment
	)
	if bank:
		payment_entry.paid_to = bank.account
		payment_entry.paid_to_account_currency = bank.account_currency

	payment_entry.flags.ignore_permissions = True
	payment_entry.insert()
	payment_entry.submit()
	return payment_entry


def fix_payment_schedule_dates(doc):
	today = getdate()
	for term in doc.get("payment_schedule", []):
		if term.due_date and term.due_date < today:
			term.due_date = today


@frappe.whitelist()
def generate_quotation_for_cart(cart: dict):
	cart = frappe.parse_json(cart)
	if len(cart.get("items", [])) < 1:
		frappe.throw(_("Can't checkout with empty cart"))
	validate_stock_available(cart["items"])
	quotation = _get_cart_quotation()
	validate_cart_is_not_in_checkout(quotation.name)
	cart_quotation = get_quotation_for_cart(cart, quotation)
	remove_coupon_code()
	return cart_quotation


def get_quotation_for_cart(cart: dict, unsaved_quotation_doc):
	sale_price_list = frappe.get_cached_value("Commera Settings", "Commera Settings", "sale_price_list")
	ecommerce_warehouse = frappe.get_cached_value(
		"Commera Settings", "Commera Settings", "ecommerce_warehouse"
	)
	unsaved_quotation_doc.selling_price_list = sale_price_list
	set_attribution_fields(unsaved_quotation_doc)
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
	save_cart_quotation(unsaved_quotation_doc)
	_remove_coupon_code(unsaved_quotation_doc)
	set_charges(unsaved_quotation_doc)
	return save_cart_quotation(unsaved_quotation_doc)


def set_charges(quotation):
	shipping_rule = frappe.get_cached_value("Commera Settings", "Commera Settings", "shipping_rule")
	if shipping_rule:
		quotation.shipping_rule = shipping_rule
		quotation.run_method("apply_shipping_rule")
		quotation.run_method("calculate_taxes_and_totals")


def set_cod_charges(quotation):
	cod_charges_applicable_below, cod_charge = get_cod_configuration()
	account_head = frappe.get_cached_value("Commera Settings", "Commera Settings", "charge_account_head")
	if not cod_charges_applicable_below or not cod_charge:
		return
	if flt(cod_charges_applicable_below) < flt(quotation.rounded_total):
		return
	if not account_head:
		frappe.throw(_("Please select a valid account for cod charges."))

	cod_charge = {
		"doctype": "Sales Taxes and Charges",
		"description": COD_CHARGE_DESCRIPTION,
		"charge_type": "Actual",
		"account_head": account_head,
		"tax_amount": cod_charge,
		# ERPNext's validate_inclusive_tax refuses an inclusive Actual charge; pinned against a site default of 1.
		"included_in_print_rate": 0,
	}
	quotation.append("taxes", cod_charge)
	quotation.calculate_taxes_and_totals()
	quotation.flags.ignore_permissions = True
	quotation.save()


@frappe.whitelist()
def update_quotation_address(address: dict):
	quotation = _get_cart_quotation()
	validate_cart_is_not_in_checkout(quotation.name)
	update_quotation_payment_terms_due_date(quotation)
	if address.get("is_store_pickup", False):
		quotation.custom_store = address.get("store_pickup_warehouse", "")
		quotation.custom_is_store_pickup = True
		# A delivery option picked before store pickup would otherwise still be charged at payment time.
		clear_delivery_option(quotation)
		save_cart_quotation(quotation)

		return {"message": _("Addresses updated successfully")}
	quotation.custom_is_store_pickup = False
	quotation.custom_store = ""

	if address.get("billing_address", {}).get("is_saved"):
		billing_address_name = address.get("billing_address", {}).get("address_id")
	else:
		billing_address_doc = add_billing_address(quotation.party_name, address)
		billing_address_name = billing_address_doc.name

	quotation.customer_address = billing_address_name

	if address.get("shipping_same_as_billing"):
		shipping_address_name = billing_address_name
	elif address.get("shipping_address", {}).get("is_saved"):
		shipping_address_name = address.get("shipping_address", {}).get("address_id")
	else:
		shipping_address_doc = add_shipping_address(quotation.party_name, address)
		shipping_address_name = shipping_address_doc.name

	quotation.shipping_address_name = shipping_address_name

	contact = frappe.get_doc("Contact", quotation.contact_person)
	existing_phones = {entry.phone for entry in contact.phone_nos}

	billing_phone = address.get("billing_address", {}).get("phone_number")
	if billing_phone and billing_phone not in existing_phones:
		contact.append("phone_nos", {"phone": billing_phone})

	shipping_phone = address.get("shipping_address", {}).get("phone_number")
	if shipping_phone and shipping_phone not in existing_phones:
		contact.append("phone_nos", {"phone": shipping_phone})

	contact.save(ignore_permissions=True)
	save_cart_quotation(quotation)

	return {"message": _("Addresses updated successfully")}


@frappe.whitelist()
def confirm_payment(reference_id: str, payment_mode: str | None = None):
	"""Resolve the outcome of a checkout the shopper has just come back from.

	`reference_id` is a Gateway Payment Request (name or gateway session id), or the Quotation for COD.
	"""
	payment_request = get_gateway_payment_request(reference_id)
	if payment_request:
		validate_reference_owner(payment_request.ref_doctype, payment_request.ref_docname)
		if is_cod(payment_mode):
			# payment_mode is attacker-controlled: without this, &payment_mode=COD double-books a paid cart.
			frappe.throw(_("A card payment is already in progress for this order."))
		if payment_request.status == "Pending":
			payment_request.sync_status()
		return {"status": payment_request.status, **purchase_summary(payment_request)}

	validate_reference_owner("Quotation", reference_id)
	if frappe.db.get_value("Quotation", reference_id, "docstatus") == 1:
		return {"status": "Paid", **quotation_purchase_summary(reference_id)}

	if not is_cod(payment_mode):
		frappe.throw(_("No payment record found for this order."))
	if not frappe.db.get_single_value("Commera Settings", "cod_enabled"):
		frappe.throw(_("Cash on delivery is not available."))

	sales_order = place_cod_order(reference_id)
	return {"status": "Paid", **sales_order_purchase_summary(sales_order)}


def get_gateway_payment_request(reference_id: str):
	"""Look a request up by gateway session id, then by our own name, then by the Quotation it opened against.

	The Quotation fallback is what stops the COD branch running on a cart with a live gateway session.
	"""
	name = frappe.db.get_value("Gateway Payment Request", {"order_ref": reference_id}, "name")
	name = name or frappe.db.get_value("Gateway Payment Request", reference_id, "name")
	name = name or get_open_gateway_payment_request(reference_id)
	return frappe.get_doc("Gateway Payment Request", name) if name else None


def validate_reference_owner(doctype: str, docname: str):
	# Scoped to the cart's own contact, so a forged reference simply finds nothing.
	if not frappe.db.exists(doctype, {"name": docname, "contact_email": frappe.session.user}):
		raise frappe.PermissionError


def purchase_summary(payment_request):
	if payment_request.ref_doctype == "Sales Order":
		return sales_order_purchase_summary(frappe.get_doc("Sales Order", payment_request.ref_docname))
	return quotation_purchase_summary(payment_request.ref_docname)


def sales_order_purchase_summary(sales_order):
	# order_name must match events.log_purchase's order_id, or Meta will not dedupe the two Purchase hits.
	if not sales_order:
		return {}
	return {
		"order_name": sales_order.name,
		"grand_total": sales_order.grand_total,
		"currency": sales_order.currency,
	}


def quotation_purchase_summary(quotation_name: str):
	sales_order = frappe.db.get_value(
		"Sales Order Item", {"prevdoc_docname": quotation_name, "docstatus": 1}, "parent"
	)
	if sales_order:
		return sales_order_purchase_summary(frappe.get_doc("Sales Order", sales_order))

	quotation = frappe.db.get_value("Quotation", quotation_name, ["grand_total", "currency"], as_dict=True)
	return {
		"order_name": quotation_name,
		"grand_total": quotation.grand_total if quotation else 0,
		"currency": quotation.currency if quotation else None,
	}


def place_cod_order(quotation_name: str):
	shopper = frappe.session.user
	with system_user_session():
		quotation = frappe.get_doc("Quotation", quotation_name)
		set_cod_charges(quotation)
		quotation.flags.ignore_permissions = True
		quotation.submit()

		sales_order = _make_sales_order(quotation_name, ignore_permissions=True)
		sales_order.custom_ecommerce_payment_mode = COD_PAYMENT_MODE
		set_attribution_fields(sales_order)
		sales_order.flags.ignore_permissions = True
		sales_order.insert()

	# COD orders count as purchases even while the Sales Order stays draft.
	stamp_order_owner(sales_order, shopper)
	log_purchase(sales_order)
	return sales_order


@frappe.whitelist()
def apply_coupon_code(applied_code: str):
	if not applied_code:
		frappe.throw(_("Please enter a coupon code"))
	coupon_name = frappe.db.get_value("Coupon Code", {"coupon_code": applied_code}, "name")
	if not coupon_name:
		frappe.throw(_("Please enter a valid coupon code"))
	validate_coupon_code(coupon_name)
	quotation = _get_cart_quotation()
	validate_cart_is_not_in_checkout(quotation.name)
	quotation.coupon_code = coupon_name
	save_cart_quotation(quotation)
	return {"message": _("Coupon code applied successfully")}


@frappe.whitelist()
def remove_coupon_code():
	quotation = _get_cart_quotation()
	validate_cart_is_not_in_checkout(quotation.name)
	_remove_coupon_code(quotation)


def _remove_coupon_code(quotation):
	quotation.coupon_code = ""
	quotation.items = [item for item in quotation.items if not item.get("is_free_item")]
	for item in quotation.items:
		item.discount_percentage = 0
		item.discount_amount = 0
		item.distributed_discount_amount = 0
		item.rate = item.price_list_rate
	quotation.calculate_taxes_and_totals()
	save_cart_quotation(quotation)
	quotation.discount_amount = 0
	save_cart_quotation(quotation)


def add_billing_address(party_name, address):
	if not party_name:
		frappe.throw(_("Cannot save an address without a customer"))

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
	)
	# ERPNext resolves a transaction address through Dynamic Link; unlinked addresses are refused.
	address_doc.append("links", {"link_doctype": "Customer", "link_name": party_name})
	address_doc.insert(ignore_permissions=True)
	return address_doc


def add_shipping_address(party_name, address):
	if not party_name:
		frappe.throw(_("Cannot save an address without a customer"))

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
	)
	# ERPNext resolves a transaction address through Dynamic Link; unlinked addresses are refused.
	address_doc.append("links", {"link_doctype": "Customer", "link_name": party_name})
	address_doc.insert(ignore_permissions=True)
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
		save_cart_quotation(quotation)
		return

	# With no option chosen — or bwh_shipping absent — the flat Shipping Rule applies instead.
	if not reprice_selected_option(quotation):
		set_charges(quotation)
	save_cart_quotation(quotation)
