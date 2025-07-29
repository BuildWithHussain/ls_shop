# Copyright (c) 2025, company@bwhstudios.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ColorSizeItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		item_code: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		size: DF.Data
	# end: auto-generated types
	pass
