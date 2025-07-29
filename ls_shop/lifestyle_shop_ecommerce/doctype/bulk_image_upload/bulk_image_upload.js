// Copyright (c) 2025, company@bwhstudios.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Image Upload', {
	refresh(frm) {
		if (!frm.doc.__islocal && frm.doc.docstatus === 0) {
			frm.set_intro('Submit document to start import', 'yellow');
		}
	},
});
