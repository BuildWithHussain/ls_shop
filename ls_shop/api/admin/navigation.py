# Copyright (c) 2026, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cstr

from ls_shop.lifestyle_shop_ecommerce.doctype.ecommerce_category.ecommerce_category import (
	MAX_MENU_DEPTH,
)
from ls_shop.lifestyle_shop_ecommerce.doctype.lifestyle_settings.navbar import navbar_manager

# Re-exported by reference: frappe.whitelist records the function object, so whitelisting travels with it.
add_node = navbar_manager.add_node
update_node = navbar_manager.update_node
delete_node = navbar_manager.delete_node
delete_all_nodes = navbar_manager.delete_all_nodes
get_delete_preview = navbar_manager.get_delete_preview
get_delete_all_preview = navbar_manager.get_delete_all_preview
move_node = navbar_manager.move_node
import_from_item_group = navbar_manager.import_from_item_group
set_visibility = navbar_manager.set_visibility
get_cascade_products = navbar_manager.get_cascade_products
get_publish_preview = navbar_manager.get_publish_preview
set_published = navbar_manager.set_published


@frappe.whitelist()
def get_editor_data():
	"""The menu editor payload, plus the server's maximum menu depth."""
	frappe.has_permission("Ecommerce Category", "read", throw=True)

	return {
		**navbar_manager.get_menu_editor_data(),
		"max_depth": MAX_MENU_DEPTH,
	}


LINK_TARGET_DOCTYPES = ("Item Group", "Brand")


@frappe.whitelist()
def get_link_options(doctype: str, search_text: str | None = None):
	"""Options for the link picker on a menu entry."""
	frappe.has_permission("Ecommerce Category", ptype="read", throw=True)

	if doctype not in LINK_TARGET_DOCTYPES:
		frappe.throw(frappe._("A menu entry cannot link to {0}.").format(doctype))

	frappe.has_permission(doctype, ptype="read", throw=True)

	filters = {}
	if search_text:
		filters["name"] = ("like", f"%{cstr(search_text)}%")

	# ponytail: first 100 matches only - the picker searches server-side, so anything further
	# down is reachable by typing; paginate if a catalog outgrows even a searched list
	records = frappe.get_all(doctype, filters=filters, pluck="name", order_by="name asc", limit=100)
	return [{"label": name, "value": name} for name in records]
