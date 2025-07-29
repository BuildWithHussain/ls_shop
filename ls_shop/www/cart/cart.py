# import frappe
from ls_shop.utils import get_delivery_configuration

no_cache = True


def get_context(context):
	context.delivery_charge, context.delivery_charge_applicable_below = (
		get_delivery_configuration()
	)
	context.breadcrumbs = [
		{
			"label": "Cart",
			"href": "#",
		}
	]
