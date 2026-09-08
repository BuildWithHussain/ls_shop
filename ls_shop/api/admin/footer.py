# Copyright (c) 2026, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cint

from ls_shop.lifestyle_shop_ecommerce.doctype.lifestyle_settings.footer import footer_preview

# Aliased by reference: frappe.whitelist records the function object, so these stay whitelisted.
get_editor_data = footer_preview.get_footer_editor_data
add_section = footer_preview.add_footer_section
rename_section = footer_preview.rename_footer_section
delete_section = footer_preview.delete_footer_section
reorder_sections = footer_preview.reorder_footer_sections
add_link = footer_preview.add_footer_link
update_link = footer_preview.update_footer_link
delete_link = footer_preview.delete_footer_link
reorder_links = footer_preview.reorder_footer_links
move_link = footer_preview.move_footer_link


@frappe.whitelist(methods=["POST"])
def set_section_enabled(name: str, enabled: int):
	"""Show or hide a whole footer column without deleting it and its links."""
	frappe.has_permission("Lifestyle Settings", "write", throw=True)

	settings = frappe.get_single("Lifestyle Settings")
	row = next((mapping for mapping in settings.footer_sections if mapping.footer_section == name), None)
	if not row:
		frappe.throw(frappe._("Footer section {0} is not part of this footer.").format(name))

	row.enabled = cint(enabled)
	settings.save()

	return footer_preview.get_footer_editor_data()


@frappe.whitelist(methods=["POST"])
def set_link_enabled(section_name: str, link_row_name: str, enabled: int):
	"""Show or hide a single link, the column it sits in staying as it is."""
	frappe.has_permission("Lifestyle Settings", "write", throw=True)

	section = frappe.get_doc("Footer Section Config", section_name)
	row = next((link_row for link_row in section.footer_links if link_row.name == link_row_name), None)
	if not row:
		frappe.throw(frappe._("Link not found in {0}.").format(section_name))

	row.enabled = cint(enabled)
	section.save()

	return footer_preview.get_footer_editor_data()
