import frappe

no_cache = True


def get_context(context):
	context.breadcrumbs = [
		{
			"label": "My Account",
			"href": f"/{frappe.local.lang}/account/",
		},
		{
			"label": "Wishlist",
			"href": "#",
		},
	]
