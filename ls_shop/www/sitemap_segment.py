import frappe
from frappe.utils import get_datetime, get_url
from frappe.utils.data import cint

DEFAULT_URLS_PER_SITEMAP = 50000

# Every route is emitted once per language, so the document budget is the URL cap divided by these.
LANGUAGES = ("en", "ar")


def get_docs_per_page():
	urls_per_sitemap = cint(frappe.db.get_single_value("Lifestyle Settings", "sitemap_urls_per_page"))
	if urls_per_sitemap <= 0:
		urls_per_sitemap = DEFAULT_URLS_PER_SITEMAP
	return urls_per_sitemap // len(LANGUAGES)


SEGMENT_CONFIG = {
	"products": {
		"doctype": "Style Attribute Variant",
		"filters": {"is_published": 1, "noindex": 0},
		"route_field": "route",
		"build_path": lambda route: f"/products/{route}",
		"changefreq": "weekly",
		"priority": "0.8",
	},
	"collections": {
		"doctype": "Ecommerce Category",
		"filters": {"enabled": 1, "noindex": 0},
		"route_field": "route_slug",
		"build_path": lambda route_slug: f"/products?category={route_slug}",
		"changefreq": "daily",
		"priority": "0.6",
	},
	# No CMS page doctype yet, so this segment is the homepage only.
	"pages": {
		"doctype": None,
		"changefreq": "daily",
		"priority": "1.0",
	},
}


def format_lastmod(value):
	if not value:
		return None
	return get_datetime(value).isoformat()


def add_localized(urls, path, lastmod, changefreq, priority):
	for lang in LANGUAGES:
		urls.append(
			{
				"loc": get_url(f"/{lang}{path}"),
				"lastmod": lastmod,
				"changefreq": changefreq,
				"priority": priority,
			}
		)


def get_segment_filters(config):
	"""Rows with no route emit no URL: most Ecommerce Category rows are nested and carry no route_slug."""
	return {**config["filters"], config["route_field"]: ["is", "set"]}


def segment_page_count(seg_type):
	config = SEGMENT_CONFIG[seg_type]
	if not config["doctype"]:
		return 1
	total = frappe.db.count(config["doctype"], get_segment_filters(config))
	return -(-total // get_docs_per_page())  # ceil without float math


def latest_lastmod(seg_type):
	config = SEGMENT_CONFIG[seg_type]
	if not config["doctype"]:
		return None
	rows = frappe.get_all(
		config["doctype"],
		filters=get_segment_filters(config),
		fields=["modified"],
		order_by="modified desc",
		limit=1,
	)
	if not rows:
		return None
	return format_lastmod(rows[0].modified)


def get_context(context):
	# Stay out of the page cache so freshly published routes appear promptly.
	context.no_cache = 1

	seg_type = frappe.form_dict.get("seg_type")
	page = cint(frappe.form_dict.get("page"))

	urls = []
	context.urls = urls

	config = SEGMENT_CONFIG.get(seg_type)
	if not config or page < 1:
		return

	if not config["doctype"]:
		if page == 1:
			for lang in LANGUAGES:
				urls.append(
					{
						"loc": get_url(f"/{lang}"),
						"lastmod": None,
						"changefreq": config["changefreq"],
						"priority": config["priority"],
					}
				)
		return

	docs_per_page = get_docs_per_page()
	route_field = config["route_field"]
	rows = frappe.get_all(
		config["doctype"],
		filters=get_segment_filters(config),
		fields=[route_field, "modified"],
		order_by="modified desc",
		limit_start=(page - 1) * docs_per_page,
		limit_page_length=docs_per_page,
	)
	for row in rows:
		route = row.get(route_field)
		add_localized(
			urls,
			config["build_path"](route),
			format_lastmod(row.modified),
			config["changefreq"],
			config["priority"],
		)
