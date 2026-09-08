import frappe

MODULE_NAME = "Shop Themes"


def execute():
	"""Create the Module Def the Shop Themes doctypes are filed under.
	add_module_defs() runs only at install, so an existing site skips the new module; must run pre-model-sync.
	"""
	if not frappe.db.exists("Module Def", MODULE_NAME):
		module_def = frappe.new_doc("Module Def")
		module_def.module_name = MODULE_NAME
		module_def.app_name = "ls_shop"
		module_def.custom = 0
		module_def.insert(ignore_permissions=True)

	# sync_for() walks a redis-cached modules.txt; without this refresh the new module waits for a second migrate.
	frappe.cache.delete_value("app_modules")
	frappe.client_cache.delete_value("installed_app_modules")
	frappe.setup_module_map()
