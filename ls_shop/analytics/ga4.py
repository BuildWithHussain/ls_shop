import json

import frappe
from frappe.integrations.utils import make_post_request
from frappe.utils.data import cint

DATA_API_URL = "https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
EVENTS = ("page_view", "view_item", "add_to_cart", "begin_checkout", "purchase")
CACHE_KEY = "ga4_stats_summary"
CACHE_TTL_SECONDS = 5 * 60


def mint_access_token(info):
	"""Mint a short-lived access token from a service-account JSON key."""
	# Imported inside the function so the app never hard-depends on google-auth at import time.
	from google.auth.transport.requests import Request
	from google.oauth2 import service_account

	credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
	credentials.refresh(Request())
	return credentials.token


def run_report(body, property_id, token):
	"""POST one GA4 Data API runReport. Token in the Authorization header, never the URL."""
	return make_post_request(
		DATA_API_URL.format(property_id=property_id),
		headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
		data=json.dumps(body),
	)


def fetch_stats(days=30):
	"""Two runReport responses (daily sessions/users, per-event counts); {} when unconfigured."""
	settings = frappe.get_cached_doc("Analytics Settings")
	if not (settings.enable_ga4 and settings.ga4_measurement_id and settings.ga4_property_id):
		return {}
	service_account_json = settings.get_password("ga4_service_account_json")
	if not service_account_json:
		return {}
	info = frappe.parse_json(service_account_json)
	token = mint_access_token(info)
	date_ranges = [{"startDate": f"{days}daysAgo", "endDate": "today"}]
	daily = run_report(
		{
			"dateRanges": date_ranges,
			"dimensions": [{"name": "date"}],
			"metrics": [{"name": "sessions"}, {"name": "activeUsers"}],
		},
		settings.ga4_property_id,
		token,
	)
	events = run_report(
		{
			"dateRanges": date_ranges,
			"dimensions": [{"name": "eventName"}],
			"metrics": [{"name": "eventCount"}],
		},
		settings.ga4_property_id,
		token,
	)
	return {"daily": daily, "events": events}


def summarize(reports):
	"""Reduce the two runReport responses to per-metric totals plus a sorted day-to-sessions dict."""
	totals = dict.fromkeys(EVENTS, 0)
	totals["sessions"] = 0
	totals["activeUsers"] = 0
	daily_sessions = {}
	for row in (reports.get("daily") or {}).get("rows") or []:
		raw_day = (row.get("dimensionValues") or [{}])[0].get("value") or ""
		metrics = row.get("metricValues") or []
		sessions = cint(metrics[0].get("value")) if len(metrics) > 0 else 0
		active_users = cint(metrics[1].get("value")) if len(metrics) > 1 else 0
		totals["sessions"] += sessions
		totals["activeUsers"] += active_users
		if len(raw_day) == 8:
			day = f"{raw_day[:4]}-{raw_day[4:6]}-{raw_day[6:]}"
			daily_sessions[day] = daily_sessions.get(day, 0) + sessions
	for row in (reports.get("events") or {}).get("rows") or []:
		event = (row.get("dimensionValues") or [{}])[0].get("value")
		if event not in EVENTS:
			continue
		metrics = row.get("metricValues") or []
		totals[event] += cint(metrics[0].get("value")) if metrics else 0
	return {"totals": totals, "daily_sessions": dict(sorted(daily_sessions.items()))}


def get_summary():
	"""Summary of the last 30 days of GA4 stats, cached for 5 minutes."""
	summary = frappe.cache.get_value(CACHE_KEY, expires=True)
	if summary is None:
		summary = summarize(fetch_stats())
		frappe.cache.set_value(CACHE_KEY, summary, expires_in_sec=CACHE_TTL_SECONDS)
	return summary
