# Copyright (c) 2026, company@bwhstudios.com and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from ls_shop.analytics import events


class TestAnalyticsSettings(IntegrationTestCase):
	def set_first_party(self, enabled):
		frappe.db.set_single_value("Analytics Settings", "enable_first_party", enabled)
		frappe.clear_document_cache("Analytics Settings", "Analytics Settings")

	def test_is_first_party_enabled_tracks_the_setting(self):
		self.set_first_party(1)
		self.assertTrue(events.is_first_party_enabled())
		self.set_first_party(0)
		self.assertFalse(events.is_first_party_enabled())

	def test_settings_single_exists_for_the_cached_read(self):
		# A missing Analytics Settings single silently disables tracking, it is read via get_cached_value.
		self.assertTrue(frappe.db.exists("Analytics Settings", "Analytics Settings"))
