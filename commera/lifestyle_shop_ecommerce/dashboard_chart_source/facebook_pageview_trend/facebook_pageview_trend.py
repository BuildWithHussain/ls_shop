import frappe

from commera.analytics import facebook


@frappe.whitelist()
def get(
	chart_name: str | None = None,
	chart: dict | str | None = None,
	no_cache: int | None = None,
	filters: dict | list | str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	timespan: str | None = None,
	time_interval: str | None = None,
	heatmap_year: str | int | None = None,
	refresh: int | None = None,
):
	frappe.only_for("System Manager")
	# broken credentials must render an empty chart, not error the Desk dashboard
	try:
		daily = facebook.get_summary()["daily_pageviews"]
	except Exception:
		daily = {}
	return {
		"labels": list(daily),
		"datasets": [{"name": "PageView", "values": list(daily.values())}],
	}
