import frappe

no_cache = True


def get_context(context):
	user = frappe.session.user
	if user == "Guest":
		raise frappe.PermissionError
	context.user_details = frappe.get_doc("User", user)
	context.breadcrumbs = [
		{
			"label": "My Account",
			"href": f"/{frappe.local.lang}/account/",
		},
		{
			"label": "Profile",
			"href": "#",
		},
	]
