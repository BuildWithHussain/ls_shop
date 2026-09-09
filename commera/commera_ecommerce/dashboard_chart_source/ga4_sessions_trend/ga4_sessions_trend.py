import frappe

from commera.analytics import ga4


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
	try:
		daily = ga4.get_summary()["daily_sessions"]
	except Exception:
		daily = {}
	return {
		"labels": list(daily),
		"datasets": [{"name": "Sessions", "values": list(daily.values())}],
	}
