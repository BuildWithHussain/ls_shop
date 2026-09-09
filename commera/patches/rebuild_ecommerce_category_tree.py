import frappe
from frappe.utils.nestedset import rebuild_tree


def execute():
	"""Seat pre-tree Ecommerce Category rows in the nested set.

	`bench migrate` adds lft/rgt but never populates them, so pre-tree rows sit at 0/0 and overlap new inserts.
	"""
	if not frappe.db.exists("Ecommerce Category", {"rgt": 0}):
		return

	rebuild_tree("Ecommerce Category")
