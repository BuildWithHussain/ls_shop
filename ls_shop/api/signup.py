import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint

from ls_shop.core import send_otp


def verify_otp(email: str, otp: str):
	"""Check the OTP and burn it, a code is single-use."""
	cache_key = f"otp:{email}"
	stored_otp = frappe.cache.get_value(cache_key)
	if not stored_otp or cint(otp) != cint(stored_otp):
		frappe.throw(_("Invalid OTP"))

	frappe.cache.delete_value(cache_key)


# Pre-login by definition; writes nothing but the cached OTP, and is rate limited.
@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
@rate_limit(limit=30, seconds=60 * 60)
def send_signup_otp(email: str):
	user_exist = frappe.db.exists("User", {"email": email})
	if user_exist:
		frappe.throw(_("Email already in use."))
	send_otp(email)


# Pre-login by definition; writes nothing but the cached OTP, and is rate limited.
@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
@rate_limit(limit=30, seconds=60 * 60)
def send_login_otp(email: str):
	user_exists = frappe.db.exists("User", email)
	if not user_exists:
		frappe.throw(_("Invalid login ID"))

	send_otp(email)


# Pre-login by definition; the OTP proves the caller owns the address.
@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
# Keyed on email, not the caller IP: an IP-bound limit leaves a 6-digit code brute-forceable.
@rate_limit(key="email", limit=5, seconds=60 * 5)
def verify_signup_otp(email: str, first_name: str, last_name: str, otp: str):
	verify_otp(email, otp)

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


# Pre-login by definition; the OTP proves the caller owns the address.
@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
@rate_limit(key="email", limit=5, seconds=60 * 5)
def verify_login_otp(email: str, otp: str):
	verify_otp(email, otp)
	frappe.local.login_manager.login_as(email)
