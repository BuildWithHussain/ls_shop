# Copyright (c) 2025, company@bwhstudios.com and contributors
# For license information, please see license.txt

import json

import frappe
import openpyxl
from frappe.model.document import Document


class SizeChart(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		brand: DF.Link
		item_group: DF.Link
		name: DF.Int | None
		size_chart: DF.Attach
		size_chart_json: DF.JSON | None

	# end: auto-generated types
	def validate(self):
		if self.size_chart_with_brand_and_item_group_exists():
			frappe.throw(
				frappe._(
					f"Size Chart with {frappe.bold(self.brand)} and {frappe.bold(self.item_group)} already exists."
				)
			)

		if self.size_chart:
			# Get File URL
			file_doc = frappe.get_doc("File", {"file_url": self.size_chart})
			filename = file_doc.get_full_path()

			# Load workbook
			wb = openpyxl.load_workbook(filename)
			ws = wb.active

			data = []
			for row in ws.iter_rows(values_only=True):
				data.append(list(row))

			# Save as JSON string
			self.size_chart_json = json.dumps(data, indent=2)

	def size_chart_with_brand_and_item_group_exists(self):
		name = self.name
		if not name:
			name = ""
		return frappe.db.exists(
			"Size Chart",
			{
				"brand": self.brand,
				"item_group": self.item_group,
				"name": ["!=", name],
			},
		)
