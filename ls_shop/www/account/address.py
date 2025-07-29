import frappe

from ls_shop.utils import get_addresses, get_country_list

no_cache = True


def get_context(context):
	if frappe.session.user == "Guest":
		raise frappe.PermissionError
	context.billing_addresses = get_addresses()
	context.shipping_addresses = get_addresses(address_type="Shipping")
	context.country_list = get_country_list()
	context.breadcrumbs = [
		{
			"label": "My Account",
			"href": f"/{frappe.local.lang}/account/",
		},
		{
			"label": "Address",
			"href": "#",
		},
	]
