import frappe

from ls_shop.lifestyle_shop_ecommerce.doctype.lifestyle_settings.navbar.navbar_manager import (
	seed_menu_when_empty,
)


def execute():
	"""Seed a store that has no menu of its own from its Item Group tree."""
	# Never rename this module: a new name re-runs it and re-seeds a menu the owner emptied on purpose.
	seed_menu_when_empty()
