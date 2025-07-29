// Copyright (c) 2025, company@bwhstudios.com and contributors
// For license information, please see license.txt

frappe.query_reports['Items Without Stock'] = {
	filters: [
		{
			label: __('Published but No Stock'),
			fieldname: 'published_but_no_stock',
			fieldtype: 'Check',
		},
		{
			label: __('Unpublished but Has Stock'),
			fieldname: 'unpublished_but_has_stock',
			fieldtype: 'Check',
		},
	],
	onload: (report) => {
		report.page.add_inner_button(__('Unpublish'), async () => {
			const filters = report.get_values();
			await frappe.call({
				method:
					'ls_shop.lifestyle_shop_ecommerce.report.items_without_stock.items_without_stock.bulk_unpublish',
				args: { filters },
			});
			frappe.show_alert(__('Items unpublished..'));
			frappe.query_report.generate_background_report();
		});
		report.page.add_inner_button(__('Publish'), async () => {
			const filters = report.get_values();
			await frappe.call({
				method:
					'ls_shop.lifestyle_shop_ecommerce.report.items_without_stock.items_without_stock.bulk_publish',
				args: { filters },
			});
			frappe.show_alert(__('Items Published..'));
			frappe.query_report.generate_background_report();
		});
	},
};
