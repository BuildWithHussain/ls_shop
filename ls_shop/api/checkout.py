import frappe

from ls_shop.api.payments import save_cart_quotation, set_charges
from ls_shop.core import _get_cart_quotation
from ls_shop.utils import get_delivery_configuration


@frappe.whitelist()
def apply_shipping_rule():
	cart_quotation = _get_cart_quotation()
	set_charges(cart_quotation)
	save_cart_quotation(cart_quotation)
	return get_delivery_configuration()
