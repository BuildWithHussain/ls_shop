import frappe
from frappe.utils.data import getdate

TEST_COMPANY = "Lifestyle Demo"
TEST_ABBR = "LSD"
TEST_CURRENCY = "INR"
TEST_ITEM_GROUP = "Interior Accessories"


def before_tests():
	"""Seed the ERPNext setup a bare CI site never gets, so the suite has a company to bill against."""
	complete_setup_wizard()
	seed_erpnext_test_defaults()
	seed_storefront_item_group()
	seed_lifestyle_settings()

	frappe.db.commit()  # nosemgrep: frappe-manual-commit -- persist seed data before the test run begins


def complete_setup_wizard():
	# Frappe's own before_tests seeds via the wizard only when a single app is installed, so our
	# four-app CI site gets none. Call setup_complete directly (not complete_setup_wizard) to pass
	# explicit fiscal-year dates — without them erpnext's Fiscal Year validation fails and silently
	# aborts Company creation, and every test that books money dies on the missing company.
	if frappe.is_setup_complete():
		return

	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	today = getdate()
	setup_complete(
		{
			"language": "English",
			"email": "test@lifestyle.local",
			"full_name": "Test User",
			"password": "test",
			"country": "India",
			"timezone": "Asia/Kolkata",
			"currency": TEST_CURRENCY,
			"company_name": TEST_COMPANY,
			"company_abbr": TEST_ABBR,
			"chart_of_accounts": "Standard",
			"fy_start_date": today.replace(month=1, day=1).isoformat(),
			"fy_end_date": today.replace(month=12, day=31).isoformat(),
		}
	)

	# The wizard deliberately swallows its own exceptions so a real user can still reach the desk. Here
	# that would hand the suite 100+ unrelated link errors instead of naming the one thing that failed.
	if not frappe.db.exists("Company", TEST_COMPANY):
		frappe.throw(f"Test setup failed: the setup wizard did not create company {TEST_COMPANY}")


def seed_erpnext_test_defaults():
	if "erpnext" not in frappe.get_installed_apps():
		return

	from erpnext.setup.utils import enable_all_roles_and_domains, set_defaults_for_tests

	enable_all_roles_and_domains()
	set_defaults_for_tests()


def seed_storefront_item_group():
	# ls_shop makes `custom_displayname` mandatory on Item Group, so the setup wizard's own stock
	# groups never insert and the site is left with nothing but the root. The suite files every test
	# item under this one group, so seed it here rather than in each test's setUp.
	if frappe.db.exists("Item Group", TEST_ITEM_GROUP):
		return

	frappe.get_doc(
		{
			"doctype": "Item Group",
			"item_group_name": TEST_ITEM_GROUP,
			"custom_displayname": TEST_ITEM_GROUP,
			"parent_item_group": "All Item Groups",
			"is_group": 0,
		}
	).insert(ignore_permissions=True)


def seed_lifestyle_settings():
	"""Fill the four mandatory Lifestyle Settings fields, which any later save() would otherwise trip on."""
	settings = frappe.get_single("Lifestyle Settings")
	settings.company = TEST_COMPANY
	settings.order_confirmation_email_template = "Order Confirmation"
	settings.order_cancellation_email_template = "Order Cancellation"
	settings.item_in_stock_email_template = "Item In Stock"
	settings.save(ignore_permissions=True)
