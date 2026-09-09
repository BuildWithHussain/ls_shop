// Copyright (c) 2025, company@bwhstudios.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Style Attribute Configurator', {
	refresh(frm) {
		if (!frm.doc.__islocal) {
			const btn = frm.add_custom_button(__('Generate Color Variants'), () => {
				frm
					.call({
						method: 'generate_variants',
						doc: frm.doc,
						btn,
					})
					.then(() => {
						frappe.show_alert({
							indicator: 'green',
							message: __('Variants generated!'),
						});
						frm.refresh();
					});
			});
		}
	},
});
