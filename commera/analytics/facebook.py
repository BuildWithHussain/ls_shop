import frappe
from frappe.integrations.utils import make_get_request
from frappe.utils.data import add_days, cint, cstr, now_datetime

GRAPH_URL = "https://graph.facebook.com/v25.0"
EVENTS = ("PageView", "ViewContent", "AddToCart", "InitiateCheckout", "Purchase")
PAGE_CAP = 30
CACHE_KEY = "fb_pixel_stats_summary"
CACHE_TTL_SECONDS = 5 * 60


def fetch_stats(days=30):
	"""Hourly event buckets from Meta's /stats endpoint; [] when disabled/unconfigured."""
	settings = frappe.get_cached_doc("Analytics Settings")
	if not (settings.enable_facebook and settings.fb_pixel_id):
		return []
	token = settings.get_password("fb_access_token")
	if not token:
		return []
	end_time = now_datetime()
	params = {
		"aggregation": "event",
		"start_time": cint(add_days(end_time, -days).timestamp()),
		"end_time": cint(end_time.timestamp()),
		"limit": 100,
	}
	# Token in the Authorization header, never the URL: query strings leak into tracebacks and Error Log.
	headers = {"Authorization": f"Bearer {token}"}
	url = f"{GRAPH_URL}/{settings.fb_pixel_id}/stats"
	buckets = []
	pages_left = PAGE_CAP
	while url and pages_left:
		response = make_get_request(url, params=params, headers=headers)
		buckets.extend(response.get("data") or [])
		url = (response.get("paging") or {}).get("next")
		params = None
		pages_left -= 1
	return buckets


def summarize(buckets):
	"""Reduce hourly buckets to per-event totals plus a sorted day-to-PageView-count dict.

	Bucket shape (aggregation=event): {"start_time": "...", "data": [{"value": "PageView", "count": 6}]}
	"""
	totals = dict.fromkeys(EVENTS, 0)
	daily_pageviews = {}
	for bucket in buckets:
		day = cstr(bucket.get("start_time"))[:10]
		for row in bucket.get("data") or []:
			event = row.get("value")
			if event not in totals:
				continue
			count = cint(row.get("count"))
			totals[event] += count
			if event == "PageView" and day:
				daily_pageviews[day] = daily_pageviews.get(day, 0) + count
	return {"totals": totals, "daily_pageviews": dict(sorted(daily_pageviews.items()))}


def get_summary():
	"""Summary of the last 30 days of pixel stats, cached for 5 minutes."""
	summary = frappe.cache.get_value(CACHE_KEY, expires=True)
	if summary is None:
		summary = summarize(fetch_stats())
		frappe.cache.set_value(CACHE_KEY, summary, expires_in_sec=CACHE_TTL_SECONDS)
	return summary
