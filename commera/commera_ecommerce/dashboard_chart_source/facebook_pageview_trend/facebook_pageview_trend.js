frappe.provide('frappe.dashboards.chart_sources');

frappe.dashboards.chart_sources['Facebook PageView Trend'] = {
	method:
		'commera.commera_ecommerce.dashboard_chart_source.facebook_pageview_trend.facebook_pageview_trend.get',
	filters: [],
};
