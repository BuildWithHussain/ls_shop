no_cache = True

import frappe

from ls_shop.utils import get_login_url_for_current_page
from ls_shop.www.account.orders.index import get_orders_list


def get_context(context):
	context.no_cache = 1
	# Guests reach this gateway-return page; frappe.is_whitelisted would refuse confirm_payment bare.
	if frappe.session.user == "Guest":
		context.login_url = get_login_url_for_current_page()
		return context

	context.order = get_owned_order(frappe.form_dict.get("order_id"))
	return context


def get_owned_order(order_id):
	if not order_id:
		return None
	_, orders = get_orders_list([order_id])
	return orders[0] if orders else None
