import frappe

no_cache = True
from frappe.query_builder import DocType
from frappe.query_builder.functions import Min

from ls_shop.utils import get_product_list


def get_context(context):
	homepage_details = get_homepage_details()
	context.homepage_details = homepage_details
	new_arrivals = [
		item.item_variant for item in homepage_details.get("new_arrivals", [])
	]
	best_picks = [item.item_variant for item in homepage_details.get("best_picks", [])]
	other_products = [
		item.item_variant for item in homepage_details.get("other_products", [])
	]
	best_picks = get_product_list(
		product_list=best_picks, page_length=len(best_picks) or 6
	)
	new_arrivals = get_product_list(
		product_list=new_arrivals, page_length=len(new_arrivals) or 6
	)
	other_products = get_product_list(
		product_list=other_products, page_length=len(other_products) or 6
	)

	context["new_arrivals"] = new_arrivals
	context["best_picks"] = best_picks
	context["other_products"] = other_products
	context.show_breadcrumb = False


def get_homepage_details():
	homepage_settings = frappe.get_cached_doc("Landing Page Settings")
	homepage_details = {}
	if frappe.local.lang == "ar":
		homepage_details = {
			"hero_banner": homepage_settings.hero_banner_ar
			or homepage_settings.hero_banner,
			"new_arrivals": homepage_settings.new_arrivals,
			"best_picks": homepage_settings.best_picks,
			"other_products": homepage_settings.other_products,
			"gif_1": homepage_settings.gif_1_ar or homepage_settings.gif_1,
			"gif_url_1": homepage_settings.gif_url_1_ar or homepage_settings.gif_url_1,
			"gif_2": homepage_settings.gif_2_ar or homepage_settings.gif_2,
			"gif_url_2": homepage_settings.gif_url_2_ar or homepage_settings.gif_url_2,
			"gif_3": homepage_settings.gif_3_ar or homepage_settings.gif_3,
			"gif_url_3": homepage_settings.gif_url_3_ar or homepage_settings.gif_url_3,
			"gif_4": homepage_settings.gif_4_ar or homepage_settings.gif_4,
			"gif_url_4": homepage_settings.gif_url_4_ar or homepage_settings.gif_url_4,
			"browse_by_brands": homepage_settings.browse_by_brands_ar
			or homepage_settings.browse_by_brands,
			"banner_1": homepage_settings.banner_1_ar or homepage_settings.banner_1,
			"banner_url_1": homepage_settings.banner_url_1_ar
			or homepage_settings.banner_url_1,
			"banner_2": homepage_settings.banner_2_ar or homepage_settings.banner_2,
			"banner_url_2": homepage_settings.banner_url_2_ar
			or homepage_settings.banner_url_2,
			"banner_3": homepage_settings.banner_3_ar or homepage_settings.banner_3,
			"banner_url_3": homepage_settings.banner_url_3_ar
			or homepage_settings.banner_url_3,
			"banner_4": homepage_settings.banner_4_ar or homepage_settings.banner_4,
			"banner_url_4": homepage_settings.banner_url_4_ar
			or homepage_settings.banner_url_4,
			"banner_5": homepage_settings.banner_5_ar or homepage_settings.banner_5,
			"banner_url_5": homepage_settings.banner_url_5_ar
			or homepage_settings.banner_url_5,
		}
	else:
		homepage_details = {
			"hero_banner": homepage_settings.hero_banner,
			"new_arrivals": homepage_settings.new_arrivals,
			"best_picks": homepage_settings.best_picks,
			"other_products": homepage_settings.other_products,
			"gif_1": homepage_settings.gif_1,
			"gif_url_1": homepage_settings.gif_url_1,
			"gif_2": homepage_settings.gif_2,
			"gif_url_2": homepage_settings.gif_url_2,
			"gif_3": homepage_settings.gif_3,
			"gif_url_3": homepage_settings.gif_url_3,
			"gif_4": homepage_settings.gif_4,
			"gif_url_4": homepage_settings.gif_url_4,
			"browse_by_brands": homepage_settings.browse_by_brands,
			"banner_1": homepage_settings.banner_1,
			"banner_url_1": homepage_settings.banner_url_1,
			"banner_2": homepage_settings.banner_2,
			"banner_url_2": homepage_settings.banner_url_2,
			"banner_3": homepage_settings.banner_3,
			"banner_url_3": homepage_settings.banner_url_3,
			"banner_4": homepage_settings.banner_4,
			"banner_url_4": homepage_settings.banner_url_4,
			"banner_5": homepage_settings.banner_5,
			"banner_url_5": homepage_settings.banner_url_5,
		}
	return homepage_details
