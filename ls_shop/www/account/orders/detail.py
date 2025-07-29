import frappe

from ls_shop.www.account.orders.index import get_orders_list

no_cache = True


def get_context(context):
	order_id = frappe.form_dict.get("order_id")
	if not order_id:
		frappe.redirect(f"/{frappe.local.lang}/account/orders")
	_, order_details = get_orders_list([order_id])
	if not order_details:
		frappe.redirect(f"/{frappe.local.lang}/account/orders")
	context.order = order_details[0]
	context.return_period = frappe.get_cached_value(
		"Lifestyle Settings", "Lifestyle Settings", "return_period"
	)
	return_reasons = frappe.get_cached_value(
		"Lifestyle Settings", "Lifestyle Settings", "reason_for_return"
	)
	context.return_reasons = [
		{"name": return_reason.name, "display_name": return_reason.display_name}
		for return_reason in return_reasons
	]
	context.breadcrumbs = get_breadcrumbs(order_id)


def get_breadcrumbs(order_id):
	return [
		{
			"label": "My Account",
			"href": f"/{frappe.local.lang}/account/",
		},
		{
			"label": "Orders",
			"href": f"/{frappe.local.lang}/account/orders",
		},
		{
			"label": order_id,
			"href": "#",
		},
	]
