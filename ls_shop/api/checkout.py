import frappe
from webshop.webshop.shopping_cart.cart import _get_cart_quotation, get_cart_quotation

from ls_shop.api.payments import set_charges
from ls_shop.utils import get_delivery_configuration


@frappe.whitelist()
def apply_shipping_rule():
	cart_quotation = _get_cart_quotation()
	set_charges(cart_quotation)
	cart_quotation.save(ignore_permissions=True)
	return get_delivery_configuration()
