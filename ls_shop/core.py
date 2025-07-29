import os

import frappe


def generate_otp():
	"""Generates a cryptographically secure random OTP"""

	return int.from_bytes(os.urandom(5), byteorder="big") % 900000 + 100000


def send_otp(email):
	"""Generate OTP and store it temporarily in Redis"""

	otp = generate_otp()
	frappe.cache.set_value(f"otp:{email}", otp, expires_in_sec=5 * 60)

	if frappe.conf.developer_mode:
		print(f"OTP for {email}: {otp}")
		return

	frappe.sendmail(
		recipients=email, subject="Your OTP", message=f"Your OTP: {otp}", now=True
	)
