import frappe
from frappe import _


@frappe.whitelist()
def delete_user_address(address_id: str):
	"""
	Deletes a user address by its ID.
	"""
	if not address_id:
		frappe.throw(_("Address ID is required."))

	address_doc = frappe.get_doc("Address", address_id)

	if address_doc.owner != frappe.session.user:
		frappe.throw(_("Cannot delete address"))

	try:
		address_doc.flags.ignore_permissions = True
		address_doc.delete()
	except Exception:
		frappe.throw(_("Cannot delete address, it is in use"))
