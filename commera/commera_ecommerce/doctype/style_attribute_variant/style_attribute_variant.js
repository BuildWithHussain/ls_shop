// Copyright (c) 2025, company@bwhstudios.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Style Attribute Variant', {
	refresh(frm) {
		if (frm.doc.is_published) {
			frm.add_web_link(
				`/${frappe.boot.lang}/products/${frm.doc.route}`,
				'View in Shop',
			);
		}
	},
});
