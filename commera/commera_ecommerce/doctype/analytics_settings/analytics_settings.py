# Copyright (c) 2026, company@bwhstudios.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class AnalyticsSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from commera.commera_ecommerce.doctype.custom_tracking_script.custom_tracking_script import (
			CustomTrackingScript,
		)

		custom_tracking_scripts: DF.Table[CustomTrackingScript]
		enable_facebook: DF.Check
		enable_first_party: DF.Check
		enable_ga4: DF.Check
		fb_access_token: DF.Password | None
		fb_pixel_id: DF.Data | None
		ga4_measurement_id: DF.Data | None
		ga4_property_id: DF.Data | None
		ga4_service_account_json: DF.Password | None
	# end: auto-generated types
	pass
