# Copyright (c) 2026, hussain@buildwithhussain.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class PixioHeroSlide(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cta_label: DF.Data | None
		heading: DF.Data
		image: DF.AttachImage | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		subheading: DF.Data | None
		thumbnail_label: DF.Data | None
		url: DF.Data | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Pixio Hero Slide"
