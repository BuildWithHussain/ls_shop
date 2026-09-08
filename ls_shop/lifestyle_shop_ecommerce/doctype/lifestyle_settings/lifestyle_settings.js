// Copyright (c) 2025, company@bwhstudios.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Lifestyle Settings', {
	async refresh(frm) {
		const response = await frm.call('get_result_card_field_options');
		if (response.message) {
			frm.fields_dict.search_result_fields.grid.update_docfield_property(
				'field',
				'options',
				response.message,
			);
		}
	},
	rebuild_search_index(frm) {
		frappe.confirm(
			__('Rebuild the product search index in the background?'),
			async () => {
				await frappe.call('ls_shop.search.build.rebuild_index');
				frappe.show_alert({
					message: __('Search index rebuild queued'),
					indicator: 'green',
				});
			},
		);
	},
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

	install_demo_data(frm) {
		frappe.confirm(
			__(
				'This will seed the Pixio demo storefront: catalogue, menu, footer, banners and settings. Continue?',
			),
			() => {
				frm
					.call({
						doc: frm.doc,
						method: 'install_demo_data',
					})
					.then((r) => {
						if (r.message) {
							frappe.msgprint(r.message);
						}
					});
			},
		);
	},

	publish_all_items(frm) {
		frappe.confirm(
			__(
				'This will publish all items to the website and fix routes. Continue?',
			),
			() => {
				frm
					.call({
						doc: frm.doc,
						method: 'publish_all_items',
					})
					.then((r) => {
						if (r.message) {
							frappe.msgprint(r.message);
						}
					});
			},
		);
	},
});

frappe.ui.form.on('Search Content Field', {
	async search_doctype(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		await frappe.model.set_value(cdt, cdn, 'field', '');
		if (!row.search_doctype) {
			return;
		}
		const response = await frm.call('get_content_field_options', {
			search_doctype: row.search_doctype,
		});
		// update_docfield_property sets options grid-wide — the core-sanctioned pattern that survives
		// a grid refresh, unlike the per-row trick which gets wiped.
		frm.fields_dict.search_content_fields.grid.update_docfield_property(
			'field',
			'options',
			response.message || '',
		);
	},
});
