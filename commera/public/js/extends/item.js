frappe.ui.form.on('Item', {
	refresh(frm) {
		if (frm.doc.has_variants) {
			frm.add_custom_button(
				__('Shop Variants'),
				() => {
					frappe.route_options = { item_template: frm.doc.name };
					frappe.new_doc('Style Attribute Configurator');
				},
				'Create',
			);
		}
	},
});
