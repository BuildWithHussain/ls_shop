import frappe

# The frappe.rename_doc wrapper does not expose ignore_permissions; only the model function does.
from frappe.model.rename_doc import rename_doc
from pypika.functions import Replace

# Children first, so the parent Single's rename repoints their parenttype under the new names.
DOCTYPE_RENAMES = {
	"Pixio Hero Slide": "Summer Hero Slide",
	"Pixio Promo Banner": "Summer Promo Banner",
	"Pixio Theme Settings": "Summer Theme Settings",
}

THEME_RENAMES = {
	"Pixio Theme": "Summer Theme",
}

OLD_ASSET_PATH = "/assets/commera/themes/pixio_theme/"
NEW_ASSET_PATH = "/assets/commera/themes/summer_theme/"

# The only columns holding a themed asset URL, from a scan of every table for the old path.
THEMED_ASSET_COLUMNS = (
	("Website Slideshow Item", "image"),
	("Summer Hero Slide", "image"),
	("Summer Promo Banner", "image"),
)


def execute():
	"""Must stay pre-model-sync: Summer Theme Settings is a Single, so once sync reads the new
	JSON it inserts an empty one and strands the old tabSingles rows under the old name."""
	for old_doctype_name, new_doctype_name in DOCTYPE_RENAMES.items():
		rename_if_pending("DocType", old_doctype_name, new_doctype_name)

	# After the DocType renames, so the theme's `theme_settings` link already reads Summer Theme Settings.
	for old_theme_name, new_theme_name in THEME_RENAMES.items():
		rename_if_pending("Shop Theme", old_theme_name, new_theme_name)

	for doctype, fieldname in THEMED_ASSET_COLUMNS:
		repoint_themed_assets(doctype, fieldname)


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
	old names, since it ships to existing sites and to CI."""
	if not frappe.db.table_exists(doctype):
		return False
	return bool(frappe.db.exists(doctype, old_name)) and not frappe.db.exists(doctype, new_name)


def repoint_themed_assets(doctype: str, fieldname: str) -> None:
	if not frappe.db.table_exists(doctype):
		return

	table = frappe.qb.DocType(doctype)
	column = table[fieldname]
	# `_` is a LIKE wildcard, so the slug is escaped or this also matches "pixio theme" paths.
	old_path_pattern = OLD_ASSET_PATH.replace("_", r"\_") + "%"
	frappe.qb.update(table).set(column, Replace(column, OLD_ASSET_PATH, NEW_ASSET_PATH)).where(
		column.like(old_path_pattern)
	).run()
