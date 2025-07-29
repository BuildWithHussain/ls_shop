from functools import wraps

import frappe
from erpnext.controllers.website_list_for_contact import get_transaction_list
from frappe import _
from frappe.translate import get_all_translations
from webshop.webshop.variant_selector.utils import (
	get_attributes_and_values,
	get_items_with_selected_attributes,
)

from ls_shop.utils import get_product_list


def auth_required(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		current_user = frappe.session.user
		if current_user == "Guest":
			raise frappe.PermissionError
		return func(*args, **kwargs)

	return wrapper


@frappe.whitelist(allow_guest=True)
def get_product_detail(item_code):
	try:
		website_item = frappe.get_doc("Website Item", {"name": item_code})
	except Exception:
		return {
			"product": {
				"id": "",
				"brand": "",
				"product_name": "",
				"item_code": "",
				"has_variants": "",
				"description": "",
				"website_image": "",
				"website_image_alt": "",
				"short_description": "",
				"long_description": "",
				"recommended_items": [],
				"offers": "",
				"slides": "",
				"price_info": "",
				"stock_qty": "",
			}
		}
	context = frappe._dict({"route": website_item.route or website_item.make_route()})
	context = website_item.get_context(context)
	recommended_items = []
	for item in website_item.get("recommended_items"):
		recommended_website_item = frappe.get_doc(
			"Website Item", {"name": item.get("website_item")}
		)
		recommended_item_context = frappe._dict(
			{
				"route": recommended_website_item.route
				or recommended_website_item.make_route()
			}
		)
		recommended_item_context = recommended_website_item.get_context(
			recommended_item_context
		)
		recommended_item_info = {
			"id": recommended_website_item.get("name"),
			"brand": recommended_website_item.get("brand")
			or recommended_website_item.get("item_group"),
			"product_name": recommended_website_item.get("item_name")
			or recommended_website_item.get("web_item_name"),
			"item_code": recommended_website_item.get("item_code"),
			"has_variants": recommended_website_item.get("has_variants"),
			"description": recommended_website_item.get("description"),
			"website_image": recommended_website_item.get("website_image"),
			"website_image_alt": recommended_website_item.get("website_image_alt"),
			"price_info": recommended_item_context.get("shopping_cart")
			.get("product_info", {})
			.get("price", {}),
		}
		recommended_items.append(recommended_item_info)
	product = {
		"id": website_item.get("name"),
		"brand": website_item.get("brand") or website_item.get("item_group"),
		"product_name": website_item.get("item_name")
		or website_item.get("web_item_name"),
		"item_code": website_item.get("item_code"),
		"has_variants": website_item.get("has_variants"),
		"description": website_item.get("description"),
		"website_image": website_item.get("website_image"),
		"website_image_alt": website_item.get("website_image_alt"),
		"short_description": website_item.get("web_short_description"),
		"long_description": website_item.get("web_long_description"),
		"recommended_items": recommended_items,
		"offers": website_item.get("offers"),
		"slides": context.get("slides"),
		"price_info": context.get("shopping_cart")
		.get("product_info", {})
		.get("price", {}),
		"stock_qty": context.get("shopping_cart")
		.get("product_info", {})
		.get("stock_qty", {}),
		# "attributes": get_attributes_and_values()
	}
	product["attributes"] = get_attributes_and_values(product["product_name"])

	return {"product": product}


@frappe.whitelist(allow_guest=True)
def get_order_detail(order_name):
	sales_order = frappe.get_doc("Sales Order", order_name)

	return {"sales_order": sales_order}


@frappe.whitelist(allow_guest=True)
def get_items_with_attributes(item_code, selected_attributes):
	return get_items_with_selected_attributes(item_code, selected_attributes)


@frappe.whitelist()
def get_whitelist_transaction_list(
	doctype,
	txt=None,
	filters=None,
	limit_start=0,
	limit_page_length=20,
	order_by="modified",
	custom=False,
):
	return get_transaction_list(
		doctype, txt, filters, limit_start, limit_page_length, order_by, custom
	)


@frappe.whitelist(allow_guest=True)
def get_homepage_details():
	landing_page = frappe.get_cached_doc("Landing Page Settings")
	landing_page = landing_page.as_dict()
	landing_page["new_arrivals"] = get_item_details(landing_page.get("new_arrivals"))
	landing_page["best_picks"] = get_item_details(landing_page.get("best_picks"))
	landing_page["carousel_1"] = get_item_details(landing_page.get("carousel_1"))
	return landing_page


def get_item_details(items):
	recommended_items = []

	for item in items:
		recommended_website_item = frappe.get_doc(
			"Website Item", {"name": item.get("website_item")}
		)
		recommended_item_context = frappe._dict(
			{
				"route": recommended_website_item.route
				or recommended_website_item.make_route()
			}
		)
		recommended_item_context = recommended_website_item.get_context(
			recommended_item_context
		)
		recommended_item_info = {
			"id": recommended_website_item.get("name"),
			"brand": recommended_website_item.get("brand")
			or recommended_website_item.get("item_group"),
			"product_name": recommended_website_item.get("item_name")
			or recommended_website_item.get("web_item_name"),
			"item_code": recommended_website_item.get("item_code"),
			"has_variants": recommended_website_item.get("has_variants"),
			"description": recommended_website_item.get("description"),
			"website_image": recommended_website_item.get("website_image"),
			"website_image_alt": recommended_website_item.get("website_image_alt"),
			"price_info": recommended_item_context.get("shopping_cart")
			.get("product_info", {})
			.get("price", {}),
		}
		recommended_items.append(recommended_item_info)
	return recommended_items


@frappe.whitelist(allow_guest=True)
def get_search_results(search):
	filters = {"search": search}
	products = get_product_list(filters=filters, page_length=6)
	return products


@frappe.whitelist()
def notify_user_product(item):
	try:
		user = frappe.session.user

		exists = frappe.db.exists(
			"OOS Notify Subscription",
			{
				"user": user,
				"item": item,
			},
		)
		if exists:
			frappe.db.set_value("OOS Notify Subscription", exists, "notified", 0)
		else:
			frappe.get_doc(
				{
					"doctype": "OOS Notify Subscription",
					"user": user,
					"item": item,
					"notified": 0,
				}
			).insert()
	except Exception:
		frappe.throw(_("Cannot subscribe for notification"))


@frappe.whitelist(allow_guest=True)
def get_translations(lang="ar"):
	return get_all_translations(lang=lang)
