frappe.provide('frappe.dashboards.chart_sources');

frappe.dashboards.chart_sources['GA4 Sessions Trend'] = {
	method:
		'commera.lifestyle_shop_ecommerce.dashboard_chart_source.ga4_sessions_trend.ga4_sessions_trend.get',
	filters: [],
};
