// Copyright (c) 2025, company@bwhstudios.com and contributors
// For license information, please see license.txt

frappe.query_reports['Orphaned Payments'] = {
	filters: [],
	formatter: (value, row, column, data, default_formatter) => {
		let new_value = default_formatter(value, row, column, data);

		if (column.fieldname === 'cancelled' || column.fieldname === 'refunded') {
			const is_true = value;
			// Center-align the content with a span
			new_value = `<span style="display:block; text-align:center;">${
				is_true ? '✔️' : '❌'
			}</span>`;
		}

		return new_value;
	},
};
