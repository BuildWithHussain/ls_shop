// Copyright (c) 2025, company@bwhstudios.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Lifestyle Settings', {
	// refresh(frm) {

	// },
	publish_variants_for_all_templates(frm) {
		if (!frm.doc.based_on_attribute) {
			frappe.throw(__('Please set attribute variant to generate variants!'));
		}

		frm
			.call({
				doc: frm.doc,
				method: 'enqueue_publish_all_variants',
				args: { attribute: frm.doc.based_on_attribute },
			})
			.then((r) => {
				if (r.message) {
					frappe.msgprint(r.message);
				} else {
					frappe.show_alert(__('Generation started in the background...'));
				}
			});
	},
	view_logs(frm) {
		frappe.set_route('List', 'Bulk Style Attribute Configurator Creation Log');
	},

	sync_item_group_mapping_to_ecommerce_items(frm) {
		frappe.confirm(
			__(
				'Are you sure you want to sync item group mapping to existing ecommerce items?',
			),
			() => {
				frm
					.call({
						doc: frm.doc,
						method: 'sync_item_group_mapping_to_ecommerce_items',
					})
					.then(() => {
						frappe.show_alert(__('Sync completed successfully.'));
					});
			},
			() => {
				frappe.show_alert(__('Sync cancelled.'));
			},
		);
	},
});
