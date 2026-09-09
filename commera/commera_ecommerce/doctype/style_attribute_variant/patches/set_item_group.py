import frappe


def execute():
	try:
		attribute_variants = frappe.get_all("Style Attribute Variant", pluck="name")

		for variant_name in attribute_variants:
			item = frappe.get_doc("Style Attribute Variant", variant_name)
			item.update_item_group()
			item.save()

		frappe.db.commit()

	except Exception:
		frappe.db.rollback()
