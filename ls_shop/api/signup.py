import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from ls_shop.core import send_otp


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=30, seconds=60 * 60)
def send_signup_otp(email: str):
	user_exist = frappe.db.exists("User", {"email": email})
	if user_exist:
		frappe.throw(_("Email already in use."))
	send_otp(email)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=30, seconds=60 * 60)
def send_login_otp(email: str):
	user_exists = frappe.db.exists("User", email)
	if not user_exists:
		frappe.throw(_("Invalid login ID"))

	send_otp(email)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=30, seconds=60 * 60)
def verify_signup_otp(email: str, first_name: str, last_name: str, otp: str):
	stored_otp = frappe.cache.get_value(f"otp:{email}")
	otp = int(otp) if otp else 0
	if stored_otp != otp:
		frappe.throw(_("Invalid OTP"))

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first_name,
			"last_name": last_name,
			"enabled": 1,
		}
	)
	user.insert(ignore_permissions=True)

	frappe.local.login_manager.login_as(email)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=30, seconds=60 * 60)
def verify_login_otp(email: str, otp: str):
	"""Check OTP from Redis instead of DB"""

	stored_otp = frappe.cache.get_value(f"otp:{email}")
	otp = int(otp) if otp else 0
	if stored_otp != otp:
		frappe.throw(_("Invalid OTP"))

	frappe.local.login_manager.login_as(email)
