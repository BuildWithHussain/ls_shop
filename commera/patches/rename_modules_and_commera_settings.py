import frappe

# The frappe.rename_doc wrapper does not expose ignore_permissions; only the model function does.
from frappe.model.rename_doc import rename_doc

MODULE_RENAMES = {
	"Ls Shop": "Commera",
	"Lifestyle Shop Ecommerce": "Commera Ecommerce",
}

DOCTYPE_RENAMES = {
	"Lifestyle Settings": "Commera Settings",
}


def execute():
	"""Drop the pre-Commera branding from the Module Defs and the settings Single.
	Must stay pre-model-sync: once sync reads the new JSON it inserts an empty Commera Settings and strands the old tabSingles rows.
	"""
	renamed_any_record = False

	for old_module_name, new_module_name in MODULE_RENAMES.items():
		renamed_any_record |= rename_module(old_module_name, new_module_name)

	for old_doctype_name, new_doctype_name in DOCTYPE_RENAMES.items():
		renamed_any_record |= rename_if_pending("DocType", old_doctype_name, new_doctype_name)

	if renamed_any_record:
		# rename_doc clears the doc caches but not the module map, which still points the renamed
		# modules at directories that no longer exist on disk.
		frappe.cache.delete_value("app_modules")
		frappe.client_cache.delete_value("installed_app_modules")
		frappe.setup_module_map()


def rename_module(old_name: str, new_name: str) -> bool:
	"""Module Def.before_rename refuses anything an app ships, so the custom flag is flipped for the
	rename and restored after, leaving the module app-shipped rather than user-created."""
	if not is_pending("Module Def", old_name, new_name):
		return False

	frappe.db.set_value("Module Def", old_name, "custom", 1, update_modified=False)
	frappe.clear_document_cache("Module Def", old_name)

	# Module Def is the Link target of the `module` field on DocType, Report, Page, Dashboard,
	# Dashboard Chart, Dashboard Chart Source, Number Card and Workspace, so this repoints them all.
	rename_doc(
		"Module Def",
		old_name,
		new_name,
		ignore_permissions=True,
		show_alert=False,
		rebuild_search=False,
	)

	frappe.db.set_value("Module Def", new_name, "custom", 0, update_modified=False)
	frappe.clear_document_cache("Module Def", new_name)
	return True


def rename_if_pending(doctype: str, old_name: str, new_name: str) -> bool:
	if not is_pending(doctype, old_name, new_name):
		return False

	rename_doc(
		doctype,
		old_name,
		new_name,
		ignore_permissions=True,
		show_alert=False,
		rebuild_search=False,
	)
	return True


def is_pending(doctype: str, old_name: str, new_name: str) -> bool:
	"""Keeps the patch a no-op on an already-renamed site and on a fresh install that never had the
	old names, since it ships to three existing sites and to CI."""
	return bool(frappe.db.exists(doctype, old_name)) and not frappe.db.exists(doctype, new_name)
