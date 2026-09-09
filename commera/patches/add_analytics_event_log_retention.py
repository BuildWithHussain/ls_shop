import frappe


def execute():
	log_settings = frappe.get_doc("Log Settings")
	log_settings.register_doctype("Storefront Analytics Event", 90)
	log_settings.save()
