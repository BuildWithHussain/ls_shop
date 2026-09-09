# Copyright (c) 2025, hussain@buildwithhussain.com and Contributors
# See license.txt

# import frappe
from frappe.tests import IntegrationTestCase

# IntegrationTestCase recursively loads link-field test record dependencies; tune that with these.
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class IntegrationTestFooterSectionConfig(IntegrationTestCase):
	pass
