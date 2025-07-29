// Copyright (c) 2025, company@bwhstudios.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Publish Variants', {
	refresh(frm) {
		frm.disable_save();

		// Primary button: Publish
		frm.page.set_primary_action(__('Publish'), async ($btn) => {
			await call_bulk_toggle(frm, true, $btn); // true = publish
		});

		// Secondary button: Unpublish
		frm.page.set_secondary_action(__('Unpublish'), async ($btn) => {
			await call_bulk_toggle(frm, false, $btn); // false = unpublish
		});
	},
});

// Helper function to call server method
async function call_bulk_toggle(frm, publish, $btn) {
	const values = frm.doc;

	if (
		!values.vendor_code &&
		!values.dcs &&
		!values.brand &&
		!values.item_code &&
		!values.season_code
	) {
		frappe.msgprint(__('Please fill at least one filter to continue.'));
		return;
	}
	frappe.confirm(
		__(`Are you sure you want to ${publish ? 'Publish' : 'Unpublish'} items?`),
		async () => {
			try {
				const r = await frm.call({
					method: 'bulk_toggle_publish',
					args: {
						publish: publish,
					},
					doc: frm.doc,
					freeze: true,
					freeze_message: __('Updating variants...'),
				});
				const action = publish ? 'published' : 'unpublished';
				frappe.msgprint(
					__('Successfully {0} {1} variants, matched {2} variants', [
						action,
						r.message.updated_count,
						r.message.total_matched,
					]),
				);
			} catch (err) {
			} finally {
				$btn
					.prop('disabled', false)
					.text(publish ? __('Publish') : __('Unpublish'));
			}
		},
	);
}
