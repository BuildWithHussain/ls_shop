import frappe


def has_app_permission() -> bool:
	"""Gate for the Desk apps screen. The dashboard shell refuses anyone who cannot write Items, so
	the tile answers the same question rather than offering a link that throws on arrival."""
	return bool(frappe.has_permission("Item", ptype="write"))
