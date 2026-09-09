import os

import frappe
import frappe.defaults
from frappe import _
from frappe.contacts.doctype.address.address import get_address_display
from frappe.contacts.doctype.contact.contact import get_contact_name
from frappe.utils import get_fullname
from frappe.utils.nestedset import get_root_of


def generate_otp():
	"""Generates a cryptographically secure random OTP"""

	return int.from_bytes(os.urandom(5), byteorder="big") % 900000 + 100000


def send_otp(email):
	"""Generate OTP and store it temporarily in Redis"""

	otp = generate_otp()
	frappe.cache.set_value(f"otp:{email}", otp, expires_in_sec=5 * 60)

	if frappe.conf.developer_mode:
		print(f"OTP for {email}: {otp}")
		return

	frappe.sendmail(recipients=email, subject="Your OTP", message=f"Your OTP: {otp}", now=True)


def _get_default_territory() -> str:
	return frappe.db.get_single_value("Selling Settings", "territory") or get_root_of("Territory")


def get_default_customer_group() -> str:
	"""Resolve a leaf Customer Group for storefront party creation."""
	# get_root_of() is wrong here: the Customer Group root is is_group=1 and Customer rejects a group.
	configured = frappe.db.get_single_value("Selling Settings", "customer_group") or frappe.db.get_default(
		"customer_group"
	)
	if configured and not frappe.db.get_value("Customer Group", configured, "is_group"):
		return configured

	leaf_group = frappe.get_all(
		"Customer Group", filters={"is_group": 0}, order_by="lft", limit=1, pluck="name"
	)
	return leaf_group[0] if leaf_group else ""


def _create_party_for_user(user: str):
	fullname = get_fullname(user) or user
	customer = frappe.new_doc("Customer")
	customer_group = get_default_customer_group()
	customer.update(
		{
			"customer_name": fullname,
			"customer_type": "Individual",
			"customer_group": customer_group,
			"territory": _get_default_territory(),
		}
	)
	customer.append("portal_users", {"user": user})
	customer.flags.ignore_mandatory = True
	customer.insert(ignore_permissions=True)

	contact = frappe.new_doc("Contact")
	contact.update({"first_name": fullname, "email_ids": [{"email_id": user, "is_primary": 1}]})
	contact.append("links", {"link_doctype": "Customer", "link_name": customer.name})
	contact.flags.ignore_mandatory = True
	contact.insert(ignore_permissions=True)

	return customer


def get_party(user=None):
	if not user:
		user = frappe.session.user

	if user == "Guest":
		raise frappe.PermissionError

	contact_name = get_contact_name(user)
	if contact_name:
		contact = frappe.get_cached_doc("Contact", contact_name)
		link = next(
			(l for l in contact.links if l.link_doctype in {"Customer", "Supplier"}),
			None,
		)
		if link:
			party_doc = frappe.get_cached_doc(link.link_doctype, link.link_name)
			if not frappe.db.exists("Portal User", {"parent": party_doc.name, "user": user}):
				party_doc.append("portal_users", {"user": user})
				party_doc.flags.ignore_permissions = True
				party_doc.flags.ignore_mandatory = True
				party_doc.save()
			return party_doc

	if portal_party := frappe.db.get_value("Portal User", {"user": user}, "parent"):
		if frappe.db.exists("Customer", portal_party):
			return frappe.get_cached_doc("Customer", portal_party)

	return _create_party_for_user(user)


def _get_cart_quotation(party=None):
	if not party:
		party = get_party()

	quotation = frappe.get_all(
		"Quotation",
		fields=["name"],
		filters={
			"party_name": party.name,
			"contact_email": frappe.session.user,
			"order_type": "Shopping Cart",
			"docstatus": 0,
		},
		order_by="modified desc",
		limit_page_length=1,
		pluck="name",
	)

	if quotation:
		return frappe.get_cached_doc("Quotation", quotation[0])
	lifestyle_settings = frappe.get_cached_doc("Lifestyle Settings")
	company = lifestyle_settings.get("company") or frappe.get_cached_value(
		"Global Defaults", "Global Defaults", "default_company"
	)
	quotation_doc = frappe.new_doc("Quotation")
	quotation_doc.quotation_to = party.doctype
	quotation_doc.company = company
	quotation_doc.order_type = "Shopping Cart"
	quotation_doc.party_name = party.name
	quotation_doc.contact_person = frappe.db.get_value("Contact", {"email_id": frappe.session.user})
	quotation_doc.contact_email = frappe.session.user
	quotation_doc.flags.ignore_permissions = True
	quotation_doc.run_method("set_missing_values")
	if sale_price_list := frappe.get_cached_value(
		"Lifestyle Settings", "Lifestyle Settings", "sale_price_list"
	):
		quotation_doc.selling_price_list = sale_price_list
	return quotation_doc


def get_address_docs(party=None):
	if not party:
		party = get_party()
	if not party:
		return []

	address_names = frappe.get_all(
		"Dynamic Link",
		filters={
			"parenttype": "Address",
			"link_doctype": party.doctype,
			"link_name": party.name,
		},
		pluck="parent",
	)

	if not address_names:
		return []

	addresses = frappe.get_all(
		"Address",
		filters={"name": ("in", address_names)},
		fields=[
			"name",
			"address_title",
			"address_type",
			"address_line1",
			"address_line2",
			"city",
			"state",
			"country",
			"pincode",
			"phone",
			"email_id",
		],
	)

	for address in addresses:
		address["display"] = get_address_display(address)

	return addresses
