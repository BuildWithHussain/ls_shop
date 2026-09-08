no_cache = True

import frappe

from ls_shop.utils import get_login_url_for_current_page


def get_context(context):
	# Guests reach this gateway-return page; frappe.is_whitelisted would refuse confirm_payment bare.
	if frappe.session.user == "Guest":
		context.login_url = get_login_url_for_current_page()
	return context
