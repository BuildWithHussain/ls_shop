# Copyright (c) 2025, hussain@buildwithhussain.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class FooterSectionConfig(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from commera.lifestyle_shop_ecommerce.doctype.footer_link.footer_link import FooterLink

		enabled: DF.Check
		footer_links: DF.Table[FooterLink]
		section_order: DF.Int
		section_title: DF.Data
	# end: auto-generated types

	pass
