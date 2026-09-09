import frappe

DROPPED_CUSTOM_FIELDS = (
	"Item Group-custom_display_on_website",
	"Item Group-custom_item_group_display_name",
	"Brand-custom_display_on_website",
)


def execute():
	"""Delete the Custom Fields the menu manager replaced.
	Fixture sync only upserts, so a field dropped from the JSON lingers - and a mandatory one breaks every insert.
	"""
	for name in DROPPED_CUSTOM_FIELDS:
		if frappe.db.exists("Custom Field", name):
			frappe.delete_doc("Custom Field", name, ignore_permissions=True)
