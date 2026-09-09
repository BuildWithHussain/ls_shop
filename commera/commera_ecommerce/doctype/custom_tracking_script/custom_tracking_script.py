# Copyright (c) iVendNext@2025
# See license.txt

# import frappe
from frappe.model.document import Document


class CustomTrackingScript(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		enabled: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		script: DF.Code
		title: DF.Data
	# end: auto-generated types
	pass
