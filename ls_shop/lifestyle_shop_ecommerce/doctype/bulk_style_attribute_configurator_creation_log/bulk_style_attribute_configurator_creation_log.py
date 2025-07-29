# Copyright (c) 2025, company@bwhstudios.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BulkStyleAttributeConfiguratorCreationLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from ls_shop.lifestyle_shop_ecommerce.doctype.style_attribute_configurator_log_table.style_attribute_configurator_log_table import (
			StyleAttributeConfiguratorLogTable,
		)

		configurators: DF.Table[StyleAttributeConfiguratorLogTable]
	# end: auto-generated types
	pass
