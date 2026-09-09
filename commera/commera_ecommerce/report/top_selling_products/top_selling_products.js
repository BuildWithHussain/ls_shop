// Copyright (c) 2026, company@bwhstudios.com and contributors
// For license information, please see license.txt

frappe.query_reports['Top Selling Products'] = {
	filters: [
		{
			label: __('From Date'),
			fieldname: 'from_date',
			fieldtype: 'Date',
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -29),
			reqd: 1,
		},
		{
			label: __('To Date'),
			fieldname: 'to_date',
			fieldtype: 'Date',
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			label: __('Limit'),
			fieldname: 'limit',
			fieldtype: 'Int',
			default: 50,
		},
	],
};
