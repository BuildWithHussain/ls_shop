// Copyright (c) 2025, company@bwhstudios.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Telr Settings', {
	refresh(frm) {
		const btn = frm.add_custom_button(__('Get Account Information'), () => {
			frm
				.call({ method: 'get_account_information', btn, doc: frm.doc })
				.then((m) => {
					frappe.msgprint({
						title: __('Account Information'),
						indicator: 'green',
						message: m,
					});
				});
		});
	},
});
