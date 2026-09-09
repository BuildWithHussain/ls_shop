# Copyright (c) 2026, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now


class StorefrontAnalyticsEvent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		currency: DF.Data | None
		device: DF.Literal["", "Desktop", "Mobile", "Tablet"]
		event: DF.Literal["page_view", "view_item", "add_to_cart", "begin_checkout", "purchase"]
		item_code: DF.Link | None
		items_json: DF.LongText | None
		order_id: DF.Link | None
		path: DF.Data | None
		qty: DF.Int
		referrer: DF.Data | None
		session_id: DF.Data | None
		utm_campaign: DF.Data | None
		utm_content: DF.Data | None
		utm_medium: DF.Data | None
		utm_source: DF.Data | None
		value: DF.Currency
		visitor_user: DF.Data | None
	# end: auto-generated types

	@staticmethod
	def clear_old_logs(days=90):
		table = frappe.qb.DocType("Storefront Analytics Event")
		frappe.db.delete(table, filters=(table.creation < (Now() - Interval(days=days))))
