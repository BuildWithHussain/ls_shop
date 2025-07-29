# Copyright (c) 2025, company@bwhstudios.com and contributors
# For license information, please see license.txt

import io
import zipfile

import frappe
from frappe.model.document import Document


class BulkImageUpload(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		folder_zip: DF.Attach | None
		name: DF.Int | None
		replace_existing: DF.Check
	# end: auto-generated types

	def on_submit(self):
		if not self.folder_zip:
			frappe.throw(frappe._("ZIP file is required for import!"))

		if not self.folder_zip.endswith(".zip"):
			frappe.throw(frappe._("Please upload a zip file."))

		# TODO after testing
		# frappe.enqueue_doc("Bulk Image Upload", self.name, "import_images")

		self.import_images()

		# frappe.throw("Images imported successfully!")

	def import_images(self):
		# folder zip can now contain multiple style folders
		# Each style folder has the structure: STYLE-NAME > Color > list of image files
		file_doc = frappe.get_doc("File", {"file_url": self.folder_zip})

		with zipfile.ZipFile(file_doc.get_full_path()) as zip_file:
			# Get all unique top-level folder names (style names)
			style_folders = set()
			for path in zip_file.namelist():
				parts = path.split("/")
				if len(parts) > 1:  # Ensure it's not the root
					style_folders.add(parts[0])

			# Process each style folder
			for style_name in style_folders:
				# iterate through all the color folders in this style
				for folder_name in zip_file.namelist():
					if (
						folder_name.startswith(f"{style_name}/")
						and folder_name.count("/") == 2
						and folder_name.endswith("/")
					):
						# this is a color folder within the style
						self.import_images_for_folder(
							style_name,
							folder_name,
							zip_file,
							replace_existing=self.replace_existing,
						)

	def import_images_for_folder(
		self,
		style_name: str,
		folder_name: str,
		zip_file: "zipfile.ZipFile",
		replace_existing: bool = False,
	):
		try:
			color_name = folder_name.split("/")[1]
			# check if this variant exists

			variant_doc = frappe.get_doc(
				"Style Attribute Variant",
				{"item_style": style_name, "attribute_value": color_name},
			)
			if replace_existing:
				variant_doc.images = []
			self.import_images_in_variant(variant_doc, folder_name, zip_file)
			variant_doc.save()
		except Exception as e:
			frappe.log_error(
				title=f"Error importing images for style {style_name}",
				message=str(e),
				reference_doctype="Bulk Image Upload",
				reference_name=self.name,
			)

	def import_images_in_variant(
		self, variant_doc, folder_name: str, zip_file: "zipfile.ZipFile"
	):
		import_count = 0
		image_files = sorted(zip_file.namelist())
		for image_file in image_files:
			if image_file.startswith(folder_name) and image_file.endswith(
				(".png", ".jpg", ".jpeg", ".webp")
			):
				image_data = zip_file.read(image_file)
				image_data = io.BytesIO(image_data)

				# create a new file document
				file_doc = frappe.get_doc(
					{
						"doctype": "File",
						"file_name": image_file.split("/")[-1],
						"attached_to_doctype": "Style Attribute Variant",
						"attached_to_name": variant_doc.name,
						"content": image_data.getvalue(),
						"attached_to_field": "image",
						"is_private": 0,
					}
				)
				file_doc.save()
				variant_doc.append("images", {"image": file_doc.file_url})
				import_count += 1

		frappe.get_doc(
			{
				"doctype": "Bulk Image Upload Log",
				"import": self.name,
				"variant": variant_doc.name,
				"images_uploaded": import_count,
			}
		).insert(ignore_permissions=True)
