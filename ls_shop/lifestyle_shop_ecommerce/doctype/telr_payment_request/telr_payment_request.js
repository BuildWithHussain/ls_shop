// Copyright (c) 2025, company@bwhstudios.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Telr Payment Request', {
	refresh(frm) {
		if (frm.doc.status !== 'Refunded') {
			const btn = frm.add_custom_button(__('Sync Status'), () => {
				frm
					.call({
						method: 'sync_status',
						doc: frm.doc,
						btn,
					})
					.then(() => {
						frappe.show_alert(__('Status synced!'));
						frm.refresh();
					});
			});

			const refund_btn = frm.add_custom_button(__('Refund'), () => {
				frm
					.call({
						method: 'refund',
						doc: frm.doc,
						btn: refund_btn,
					})
					.then(() => {
						frappe.show_alert(__('Refund processed!'));
						frm.refresh();
					});
			});
		}
	},
});
