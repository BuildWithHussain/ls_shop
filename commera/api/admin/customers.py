# Copyright (c) 2026, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Count, Sum
from frappe.utils.data import cint, cstr, flt

from commera.api.admin.orders import (
	describe_payment_state,
	describe_state,
	is_webshop_order,
	read_order_lifecycles,
	read_paid_orders,
)

PAGE_LENGTH = 20

# Caps the IN lists the batched address/order reads build from a page.
MAX_PAGE_LENGTH = 100

# How many of a customer's own orders the profile screen's "Recent orders" list shows. A customer
# in this seed data has at most a handful, but a long-lived real customer should not blow this open.
CUSTOMER_ORDER_LIMIT = 50


@frappe.whitelist()
def get_customers(search: str | None = None, start: int = 0, page_length: int = PAGE_LENGTH):
	"""The whole Customers screen in one call."""
	frappe.has_permission("Customer", ptype="read", throw=True)

	# Or-ed against nothing else here (there are no tab filters, unlike Orders), so a plain
	# or_filters list is enough — see orders.get_orders for why it can't just be appended.
	or_filters = (
		[
			["name", "like", f"%{search}%"],
			["customer_name", "like", f"%{search}%"],
			["email_id", "like", f"%{search}%"],
		]
		if search
		else None
	)

	if or_filters:
		total = len(frappe.get_all("Customer", or_filters=or_filters, pluck="name"))
	else:
		total = frappe.db.count("Customer")

	customers = frappe.get_all(
		"Customer",
		or_filters=or_filters,
		fields=["name", "customer_name", "email_id", "creation"],
		order_by="creation desc",
		start=cint(start),
		page_length=min(cint(page_length) or PAGE_LENGTH, MAX_PAGE_LENGTH),
	)
	if not customers:
		return {"customers": [], "total": total}

	customer_names = [row.name for row in customers]
	stats = read_customer_order_stats(customer_names)
	cities = read_customer_cities(customer_names)

	return {
		"customers": [
			{
				"id": row.name,
				"name": row.customer_name or row.name,
				"email": row.email_id,
				"city": cities.get(row.name),
				"orders": cint(stats.get(row.name, {}).get("order_count")),
				"spend": flt(stats.get(row.name, {}).get("spend")),
				"since": row.creation,
			}
			for row in customers
		],
		"total": total,
	}


def read_customer_order_stats(customer_names: list) -> dict:
	"""Lifetime order count and spend for a whole page of customers, in one query. Counts drafts as real
	revenue and sums base_grand_total rather than grand_total, both the way orders.read_sales_window does."""
	if not customer_names:
		return {}
	sales_order = frappe.qb.DocType("Sales Order")
	rows = (
		frappe.qb.from_(sales_order)
		.select(
			sales_order.customer,
			Count(sales_order.name).as_("order_count"),
			Sum(sales_order.base_grand_total).as_("spend"),
		)
		.where(is_webshop_order(sales_order))
		.where(sales_order.customer.isin(customer_names))
		.groupby(sales_order.customer)
	).run(as_dict=True)
	return {row.customer: row for row in rows}


def read_customer_cities(customer_names: list) -> dict:
	"""One customer's city off whichever Address links to it, batched across the page. A checkout address
	links back to the Customer only when add_billing_address/add_shipping_address wrote that Dynamic Link."""
	if not customer_names:
		return {}

	address_names_by_customer: dict = {}
	for row in frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Address", "link_doctype": "Customer", "link_name": ["in", customer_names]},
		fields=["parent", "link_name"],
	):
		address_names_by_customer.setdefault(row.link_name, []).append(row.parent)

	address_names = [name for names in address_names_by_customer.values() for name in names]
	if not address_names:
		return {}

	city_by_address = {
		row.name: row.city
		for row in frappe.get_all("Address", filters={"name": ["in", address_names]}, fields=["name", "city"])
	}

	cities = {}
	for customer, names in address_names_by_customer.items():
		city = next((city_by_address[name] for name in names if city_by_address.get(name)), None)
		if city:
			cities[customer] = city
	return cities


@frappe.whitelist()
def get_customer(customer: str):
	"""Everything one customer's profile screen needs, in one call."""
	frappe.has_permission("Customer", doc=customer, ptype="read", throw=True)

	doc = frappe.db.get_value(
		"Customer", customer, ["name", "customer_name", "email_id", "mobile_no", "creation"], as_dict=True
	)
	if not doc:
		frappe.throw(_("Customer {0} not found").format(customer))

	orders = read_customer_orders(customer)
	spend = sum(flt(order["base_total"]) for order in orders)
	order_count = len(orders)

	return {
		"id": doc.name,
		"name": doc.customer_name or doc.name,
		"email": doc.email_id,
		"phone": doc.mobile_no,
		"city": read_customer_cities([doc.name]).get(doc.name),
		"since": doc.creation,
		"orders": order_count,
		"spend": spend,
		"average_order": flt(spend / order_count) if order_count else 0,
		"recent_orders": [{k: v for k, v in order.items() if k != "base_total"} for order in orders],
	}


def read_customer_orders(customer: str) -> list:
	"""This one customer's own order history, in the same shape orders.get_orders uses for its rows.
	Counts drafts, for the reason read_customer_order_stats gives."""
	orders = frappe.get_all(
		"Sales Order",
		filters=[
			["customer", "=", customer],
			["docstatus", "<", 2],
			["order_type", "=", "Shopping Cart"],
		],
		fields=[
			"name",
			"transaction_date",
			"status",
			"grand_total",
			"base_grand_total",
			"currency",
			"docstatus",
			"per_delivered",
			"custom_ecommerce_payment_mode",
		],
		order_by="creation desc",
		page_length=CUSTOMER_ORDER_LIMIT,
	)
	if not orders:
		return []

	order_names = [row.name for row in orders]
	item_counts: dict = {}
	for row in frappe.get_all(
		"Sales Order Item", filters={"parent": ["in", order_names]}, fields=["parent", "qty"]
	):
		item_counts[row.parent] = item_counts.get(row.parent, 0) + flt(row.qty)

	lifecycles = read_order_lifecycles(order_names)
	paid_orders = read_paid_orders(order_names)

	return [
		{
			"name": row.name,
			"placed_on": row.transaction_date,
			"status": row.status,
			"state": describe_state(row, lifecycles.get(cstr(row.name))),
			"payment_state": describe_payment_state(row, paid_orders),
			"total": flt(row.grand_total),
			"base_total": flt(row.base_grand_total),
			"currency": row.currency,
			"item_count": item_counts.get(row.name, 0),
		}
		for row in orders
	]
