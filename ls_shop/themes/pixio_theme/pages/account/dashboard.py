import frappe

from ls_shop.www.account import dashboard
from ls_shop.www.account.orders.index import get_orders_list

# What update_sales_order_ecommerce_status assigns short of Delivered, Cancelled and Returned.
OPEN_ORDER_STATUSES = ("Waiting for Approval", "Order Received", "Preparing for Shipment", "Shipped")

RECENT_ORDER_COUNT = 5


def get_context(context):
	dashboard.get_context(context)
	context.total_order_count, context.recent_orders = get_orders_list(page_length=RECENT_ORDER_COUNT)
	context.open_order_count = frappe.db.count(
		"Sales Order",
		{"owner": frappe.session.user, "custom_ecommerce_status": ("in", OPEN_ORDER_STATUSES)},
	)
	return context
