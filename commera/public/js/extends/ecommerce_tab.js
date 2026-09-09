// Copyright (c) 2026, company@bwhstudios.com and contributors
// For license information, please see license.txt

// Frappe concatenates every `doctype_js` file for a doctype into one `new Function()` scope
// (script_manager.js `setup`), so a top-level name here would collide with the other scripts.
(() => {
	const PANEL_STYLES = `<style>
		.sf-panel { margin-top: 4px; }
		.sf-toolbar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
		.sf-title { font-size: var(--text-lg); font-weight: 600; color: var(--text-color); margin-right: 8px; }
		.sf-actions { display: flex; gap: 8px; }
		.sf-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--border-radius-md); overflow: hidden; }
		.sf-variant-grid { width: 100%; border-collapse: collapse; }
		.sf-variant-grid th { font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted); font-weight: 500; text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--border-color); background: var(--subtle-fg); }
		.sf-variant-grid td { padding: 10px 12px; border-bottom: 1px solid var(--border-color); vertical-align: top; font-size: var(--text-md); color: var(--text-color); }
		.sf-variant-grid tr:last-child td { border-bottom: none; }
		.sf-variant-grid tbody tr:hover td { background: var(--fg-hover); }
		.sf-swatch { width: 18px; height: 18px; border-radius: 50%; border: 1px solid var(--border-color); flex-shrink: 0; display: inline-block; }
		.sf-variant-name { font-weight: 500; }
		.sf-variant-route { font-size: var(--text-sm); color: var(--text-muted); }
		.sf-variant-link { cursor: pointer; }
		.sf-variant-link:hover .sf-variant-name { color: var(--primary); text-decoration: underline; }
		.sf-thumb { width: 54px; height: 54px; object-fit: cover; border-radius: 6px; border: 1px solid var(--border-color); }
		.sf-thumbs { display: grid; grid-template-columns: repeat(2, 54px); gap: 4px; width: max-content; margin-bottom: 5px; }
		.sf-thumb-wrap { position: relative; display: inline-block; line-height: 0; }
		.sf-thumb-remove { position: absolute; top: -4px; right: -4px; width: 14px; height: 14px; border-radius: 50%; background: var(--gray-700); color: #fff; font-size: 12px; line-height: 1; align-items: center; justify-content: center; cursor: pointer; display: none; z-index: 1; box-shadow: var(--shadow-sm); }
		.sf-thumb-wrap:hover .sf-thumb-remove { display: flex; }
		.sf-thumb-remove:hover { background: var(--red-500); }
		.sf-images-actions { display: flex; gap: 8px; align-items: center; }
		.sf-clear-images { font-size: var(--text-xs); color: var(--text-muted); cursor: pointer; }
		.sf-clear-images:hover { color: var(--red-500); text-decoration: underline; }
		.sf-dropbox { width: 54px; height: 54px; border: 1.5px dashed var(--gray-400); border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 10px; line-height: 1.2; color: var(--text-muted); text-align: center; cursor: pointer; }
		.sf-dropbox:hover { border-color: var(--primary); color: var(--primary); }
		.sf-price-link { cursor: pointer; }
		.sf-price-link:hover, .sf-price-link:hover .text-muted { color: var(--primary); text-decoration: underline; }
		.sf-stock-link { cursor: pointer; }
		.sf-stock-link:hover { color: var(--primary); text-decoration: underline; }
		.sf-seo-link { color: var(--text-muted); cursor: pointer; font-size: var(--text-sm); white-space: nowrap; }
		.sf-seo-link:hover { text-decoration: underline; }
		.sf-seo-link-filled { color: var(--primary); }
		.sf-chip { display: inline-block; font-size: var(--text-md); color: var(--text-color); }
		.sf-variant-grid td.sf-size-cell { vertical-align: top; padding-top: 6px; padding-bottom: 6px; }
		.sf-size-col { display: flex; flex-direction: column; }
		.sf-size-line { height: 28px; display: flex; align-items: center; white-space: nowrap; }
		.sf-badge { font-size: 11px; padding: 2px 8px; }
		.sf-readiness { display: grid; grid-template-columns: auto auto; gap: 4px 6px; justify-content: start; }
		.sf-blocked { display: block; font-size: var(--text-xs); color: var(--red-500); margin-top: 4px; max-width: 110px; white-space: normal; }
		.sf-switch { position: relative; display: inline-block; width: 34px; height: 20px; margin: 0; cursor: pointer; vertical-align: middle; }
		.sf-switch input { display: none; }
		.sf-switch-slider { position: absolute; inset: 0; background: var(--gray-400); border-radius: 20px; transition: background 0.15s ease; }
		.sf-switch-slider::before { content: ""; position: absolute; width: 16px; height: 16px; border-radius: 50%; background: #fff; top: 2px; left: 2px; transition: left 0.15s ease; box-shadow: var(--shadow-sm); }
		.sf-switch input:checked + .sf-switch-slider { background: var(--primary); }
		.sf-switch input:checked + .sf-switch-slider::before { left: 16px; }
		.sf-switch-blocked { opacity: 0.45; cursor: not-allowed; }
	</style>`;

	// A swatch value is interpolated into a `style` attribute, where HTML-escaping alone still lets
	// `red;background-image:url(...)` through — only an allow-list keeps that cell safe.
	const CSS_COLOR_PATTERN = /^(#[0-9a-f]{3,8}|[a-z]+)$/i;

	const PUBLISH_METHOD =
		'commera.lifestyle_shop_ecommerce.doctype.bulk_publish_variants.bulk_publish_variants.set_variants_published';

	frappe.ui.form.on('Item', {
		refresh(frm) {
			refresh_ecommerce_panel(frm);
		},
	});

	async function refresh_ecommerce_panel(frm) {
		const field = frm.get_field('custom_ecommerce_variant_grid');
		if (!field) return;
		const wrapper = field.$wrapper;
		add_panel_actions(wrapper, frm);
		if (frm.is_new() || !frm.doc.has_variants) {
			wrapper.html(
				PANEL_STYLES +
					format_note(
						__(
							'This panel lights up on template items (Has Variants) and shows every storefront variant in one place.',
						),
					),
			);
			return;
		}
		wrapper.html(PANEL_STYLES + format_note(__('Loading variants…')));
		try {
			const variants = await get_variants(frm);
			frm.storefront_variants = variants;
			if (!variants.length) {
				wrapper.html(PANEL_STYLES + format_empty_state());
				return;
			}
			wrapper.html(PANEL_STYLES + format_panel(variants));
		} catch (error) {
			wrapper.html(
				PANEL_STYLES +
					format_note(__('Could not load variants — check console.')),
			);
			console.error('Ecommerce tab:', error);
		}
	}

	function add_panel_actions(wrapper, frm) {
		wrapper
			.off('click.sfux')
			.on('click.sfux', '[data-sf-action]', async function (event) {
				event.preventDefault();
				event.stopPropagation();
				const action = $(this).attr('data-sf-action');
				const variant_name = $(this).attr('data-sf-variant');
				if (action === 'drop-images') {
					open_image_uploader(frm, variant_name);
				} else if (action === 'remove-image') {
					remove_variant_image(
						frm,
						variant_name,
						$(this).attr('data-sf-image'),
					);
				} else if (action === 'clear-images') {
					remove_all_variant_images(frm, variant_name);
				} else if (action === 'edit-seo') {
					await open_seo_dialog(frm, variant_name);
				} else if (action === 'edit-prices') {
					await open_price_dialog(frm, variant_name);
				} else if (action === 'receive-stock') {
					await open_receive_stock_dialog(frm, variant_name);
				} else if (action === 'bulk-upload-images') {
					open_bulk_image_upload(frm);
				} else if (action === 'bulk-set-prices') {
					open_bulk_price_dialog(frm);
				} else if (action === 'toggle-publish') {
					const checkbox = $(this).find('input')[0];
					if (checkbox && variant_name && !checkbox.disabled) {
						await set_variant_published(
							frm,
							variant_name,
							!checkbox.checked,
							checkbox,
						);
					}
				} else if (action === 'publish-all-ready') {
					await publish_ready_variants(frm, $(this));
				} else if (action === 'generate-variants') {
					await generate_variants(frm, $(this));
				}
			})
			.off('click.sfux-variant')
			.on(
				'click.sfux-variant',
				'.sf-variant-link[data-sf-variant]',
				function (event) {
					event.preventDefault();
					event.stopPropagation();
					frappe.set_route(
						'Form',
						'Style Attribute Variant',
						$(this).attr('data-sf-variant'),
					);
				},
			);
	}

	function open_image_uploader(frm, variant_name) {
		if (!variant_name) return;
		const uploaded_urls = [];
		const uploader = new frappe.ui.FileUploader({
			doctype: 'Style Attribute Variant',
			docname: variant_name,
			folder: 'Home/Attachments',
			allow_multiple: true,
			on_success(file_doc) {
				uploaded_urls.push(file_doc.file_url);
			},
		});
		// `onhide` is frappe.ui.Dialog's own hook; the fork bound `hidden.bs.modal` directly, which the
		// uploader's own handler detaches the wrapper from first.
		uploader.dialog.onhide = async () => {
			if (!uploaded_urls.length) return;
			try {
				await add_variant_images(variant_name, uploaded_urls);
				await refresh_ecommerce_panel(frm);
			} catch (error) {
				console.error('Ecommerce tab: image attach failed', error);
			}
		};
	}

	async function add_variant_images(variant_name, file_urls) {
		await frappe.call({
			method: 'run_doc_method',
			args: {
				dt: 'Style Attribute Variant',
				dn: variant_name,
				method: 'add_images',
				args: { file_urls },
			},
		});
	}

	function remove_variant_image(frm, variant_name, file_url) {
		if (!variant_name || !file_url) return;
		frappe.confirm(
			__('Remove this image from {0}?', [variant_name]),
			async () => {
				await frappe.call({
					method: 'run_doc_method',
					args: {
						dt: 'Style Attribute Variant',
						dn: variant_name,
						method: 'remove_image',
						args: { file_url },
					},
				});
				await refresh_ecommerce_panel(frm);
			},
		);
	}

	function remove_all_variant_images(frm, variant_name) {
		if (!variant_name) return;
		frappe.confirm(
			__('Remove all images from {0}?', [variant_name]),
			async () => {
				await frappe.call({
					method: 'run_doc_method',
					args: {
						dt: 'Style Attribute Variant',
						dn: variant_name,
						method: 'clear_images',
					},
				});
				await refresh_ecommerce_panel(frm);
			},
		);
	}

	async function set_variant_published(
		frm,
		variant_name,
		next_published,
		checkbox_element,
	) {
		checkbox_element.checked = next_published;
		checkbox_element.disabled = true;
		try {
			const response = await frappe.db.set_value(
				'Style Attribute Variant',
				variant_name,
				'is_published',
				next_published ? 1 : 0,
			);
			// The variant's own `unpublish_if_incomplete_data` can veto the write, so trust the saved doc.
			if (next_published && !response.message?.is_published) {
				frappe.show_alert(
					{
						message: __(
							'{0} could not be published — it needs images and sizes first.',
							[variant_name],
						),
						indicator: 'orange',
					},
					6,
				);
			}
		} catch (error) {
			checkbox_element.checked = !next_published;
			checkbox_element.disabled = false;
			throw error;
		}
		await refresh_ecommerce_panel(frm);
	}

	async function publish_ready_variants(frm, $button) {
		const ready_unpublished = (frm.storefront_variants || []).filter(
			(variant) => !variant.is_published && variant.ready,
		);
		if (!ready_unpublished.length) {
			frappe.show_alert(
				{
					message: __('No unpublished variants are ready to publish'),
					indicator: 'blue',
				},
				4,
			);
			return;
		}

		$button.prop('disabled', true).text(__('Publishing…'));
		try {
			// set_variants_published owns the only bulk write to `is_published` and its search-index
			// enqueue; bulk_toggle_publish would AND in the Bulk Publish Variants form's last filters.
			const response = await frappe.call({
				method: PUBLISH_METHOD,
				args: {
					publish: 1,
					names: ready_unpublished.map((variant) => variant.name),
				},
			});
			frappe.show_alert(
				{
					message: __('Published {0} variant(s)', [
						response.message?.updated_count || 0,
					]),
					indicator: 'green',
				},
				5,
			);
		} finally {
			$button.prop('disabled', false).text(__('Publish All Ready'));
			await refresh_ecommerce_panel(frm);
		}
	}

	async function generate_variants(frm, $button) {
		if (!frm.doc.has_variants) {
			frappe.show_alert(
				{
					message: __('This item does not have variants'),
					indicator: 'orange',
				},
				4,
			);
			return;
		}

		$button.prop('disabled', true).text(__('Generating…'));
		const before_count = (frm.storefront_variants || []).length;
		try {
			const existing_configurator = await frappe.db.get_value(
				'Style Attribute Configurator',
				{ item_template: frm.doc.name },
				'name',
			);
			let configurator_name = existing_configurator.message?.name;
			if (!configurator_name) {
				const based_on_attribute = await frappe.db.get_single_value(
					'Lifestyle Settings',
					'based_on_attribute',
				);
				if (!based_on_attribute) {
					frappe.throw(
						__(
							'Set "Based On Attribute" in Lifestyle Settings before generating variants.',
						),
					);
				}
				const inserted = await frappe.db.insert({
					doctype: 'Style Attribute Configurator',
					item_template: frm.doc.name,
					item_attribute: based_on_attribute,
				});
				configurator_name = inserted.name;
			}

			await frappe.call({
				method: 'run_doc_method',
				args: {
					dt: 'Style Attribute Configurator',
					dn: configurator_name,
					method: 'generate_variants',
				},
			});
		} finally {
			$button.prop('disabled', false).text(__('Generate Variants'));
			await refresh_ecommerce_panel(frm);
		}

		const created_count = (frm.storefront_variants || []).length - before_count;
		frappe.show_alert(
			{
				message:
					created_count > 0
						? __('Generated {0} new variant(s)', [created_count])
						: __('No new variants — every colour already has one'),
				indicator: created_count > 0 ? 'green' : 'blue',
			},
			5,
		);
	}

	function open_bulk_image_upload(frm) {
		const escape_html = frappe.utils.escape_html;
		const colors = (frm.storefront_variants || [])
			.map((variant) => variant.attribute_value)
			.filter(Boolean);
		const color_hint = colors.length
			? colors.map((color) => `<code>${escape_html(color)}</code>`).join(', ')
			: '';

		const dialog = new frappe.ui.Dialog({
			title: __('Bulk Upload Images — {0}', [
				escape_html(frm.doc.item_name || frm.doc.name),
			]),
			fields: [
				{
					fieldname: 'info',
					fieldtype: 'HTML',
					options: `<div class="text-muted" style="margin-bottom: 10px;">
						${__('ZIP structure: {0} / colour / images.', [
							`<code>${escape_html(frm.doc.name)}</code>`,
						])}
						${color_hint ? `<br>${__('Colours')}: ${color_hint}` : ''}
					</div>`,
				},
				{
					fieldname: 'folder_zip',
					fieldtype: 'Attach',
					label: __('Folder ZIP'),
					reqd: 1,
					options: { restrictions: { allowed_file_types: ['.zip'] } },
				},
				{
					fieldname: 'replace_existing',
					fieldtype: 'Check',
					label: __('Replace Existing?'),
					default: 1,
				},
			],
			primary_action_label: __('Upload & Import'),
			async primary_action(values) {
				dialog.get_primary_btn().prop('disabled', true).text(__('Importing…'));
				try {
					const upload_name = await save_bulk_image_upload(values);
					dialog.hide();
					frappe.show_alert(
						{
							message: __(
								'Import queued. See {0} shortly for per-colour results (including any errors).',
								[
									`<a href="/app/bulk-image-upload/${encodeURIComponent(
										upload_name,
									)}" target="_blank">${escape_html(upload_name)}</a>`,
								],
							),
							indicator: 'green',
						},
						7,
					);
				} catch (error) {
					dialog
						.get_primary_btn()
						.prop('disabled', false)
						.text(__('Upload & Import'));
					throw error;
				}
			},
		});
		dialog.onhide = () => dialog.$wrapper.remove();
		dialog.show();
	}

	async function save_bulk_image_upload(values) {
		const insert_response = await frappe.call({
			method: 'frappe.client.insert',
			args: {
				doc: {
					doctype: 'Bulk Image Upload',
					folder_zip: values.folder_zip,
					replace_existing: values.replace_existing ? 1 : 0,
				},
			},
		});
		const submit_response = await frappe.call({
			method: 'frappe.client.submit',
			args: { doc: insert_response.message },
		});
		return submit_response.message.name;
	}

	async function open_seo_dialog(frm, variant_name) {
		if (!variant_name) return;
		const variant_doc = await frappe.db.get_doc(
			'Style Attribute Variant',
			variant_name,
		);
		const dialog = new frappe.ui.Dialog({
			title: __('SEO — {0}', [
				frappe.utils.escape_html(variant_doc.display_name || variant_name),
			]),
			fields: [
				{
					fieldname: 'meta_title',
					fieldtype: 'Data',
					label: __('Meta Title'),
					description: __(
						'Overrides the page title. Defaults to display name + store name.',
					),
					default: variant_doc.meta_title,
				},
				{
					fieldname: 'meta_description',
					fieldtype: 'Small Text',
					label: __('Meta Description'),
					description: __(
						'Used as the meta description / OG description (truncated to 160 chars).',
					),
					default: variant_doc.meta_description,
				},
				{
					fieldname: 'meta_keywords',
					fieldtype: 'Data',
					label: __('Meta Keywords'),
					default: variant_doc.meta_keywords,
				},
				{
					fieldname: 'og_image',
					fieldtype: 'Attach Image',
					label: __('OG Image'),
					description: __('Overrides the auto-generated social share image.'),
					default: variant_doc.og_image,
				},
				{
					fieldname: 'noindex',
					fieldtype: 'Check',
					label: __('No Index'),
					description: __(
						'Emits {0} and drops this product from the XML sitemap.',
						['<code>&lt;meta name="robots" content="noindex"&gt;</code>'],
					),
					default: variant_doc.noindex,
				},
			],
			primary_action_label: __('Save'),
			async primary_action(values) {
				await frappe.db.set_value('Style Attribute Variant', variant_name, {
					meta_title: values.meta_title || '',
					meta_description: values.meta_description || '',
					meta_keywords: values.meta_keywords || '',
					og_image: values.og_image || '',
					noindex: values.noindex ? 1 : 0,
				});
				dialog.hide();
				frappe.show_alert(
					{ message: __('SEO details saved'), indicator: 'green' },
					4,
				);
				await refresh_ecommerce_panel(frm);
			},
		});
		dialog.onhide = () => dialog.$wrapper.remove();
		dialog.show();
	}

	async function open_price_dialog(frm, variant_name) {
		if (!variant_name) return;
		const escape_html = frappe.utils.escape_html;
		const response = await frappe.call({
			method: 'run_doc_method',
			args: {
				dt: 'Style Attribute Variant',
				dn: variant_name,
				method: 'get_size_prices',
			},
		});
		const price_data = response.message;
		if (!price_data.sizes.length) {
			frappe.show_alert(
				{
					message: __('Add sizes to this variant before setting prices'),
					indicator: 'orange',
				},
				4,
			);
			return;
		}

		const variant = (frm.storefront_variants || []).find(
			(candidate) => candidate.name === variant_name,
		);
		const dialog = new frappe.ui.Dialog({
			title: __('Prices — {0}', [
				escape_html(variant?.display_name || variant_name),
			]),
			fields: [
				{
					fieldname: 'size_prices',
					fieldtype: 'Table',
					label: __('Price per Size'),
					cannot_add_rows: true,
					cannot_delete_rows: true,
					in_place_edit: true,
					data: price_data.sizes,
					get_data: () => price_data.sizes,
					fields: [
						{
							fieldname: 'size',
							fieldtype: 'Data',
							label: __('Size'),
							in_list_view: 1,
							read_only: 1,
							columns: 2,
						},
						{
							fieldname: 'default_rate',
							fieldtype: 'Currency',
							label: escape_html(price_data.default_price_list),
							in_list_view: 1,
							columns: 4,
						},
						{
							fieldname: 'sale_rate',
							fieldtype: 'Currency',
							label: escape_html(price_data.sale_price_list),
							in_list_view: 1,
							columns: 4,
						},
					],
				},
			],
			primary_action_label: __('Save'),
			async primary_action(values) {
				const size_prices = (values.size_prices || []).map((row) => ({
					item_code: row.item_code,
					default_rate: row.default_rate,
					sale_rate: row.sale_rate,
				}));
				dialog.get_primary_btn().prop('disabled', true).text(__('Saving…'));
				try {
					const save_response = await frappe.call({
						method: 'run_doc_method',
						args: {
							dt: 'Style Attribute Variant',
							dn: variant_name,
							method: 'save_size_prices',
							args: { size_prices },
						},
					});
					dialog.hide();
					const counts = save_response.message || {};
					const saved_count = (counts.created || 0) + (counts.updated || 0);
					frappe.show_alert(
						{
							message: saved_count
								? __('Saved {0} price(s)', [saved_count])
								: __('No price changes'),
							indicator: saved_count ? 'green' : 'blue',
						},
						4,
					);
					await refresh_ecommerce_panel(frm);
				} catch (error) {
					dialog.get_primary_btn().prop('disabled', false).text(__('Save'));
					throw error;
				}
			},
		});
		dialog.add_custom_action(__('Copy to all sizes'), () =>
			set_rates_from_first_row(dialog.fields_dict.size_prices.grid),
		);
		dialog.onhide = () => dialog.$wrapper.remove();
		dialog.show();
	}

	function set_rates_from_first_row(grid) {
		const [first_row, ...other_rows] = grid.get_data();
		if (!first_row) return;
		for (const row of other_rows) {
			if (flt(first_row.default_rate))
				row.default_rate = first_row.default_rate;
			if (flt(first_row.sale_rate)) row.sale_rate = first_row.sale_rate;
		}
		grid.refresh();
	}

	function open_bulk_price_dialog(frm) {
		const variants = frm.storefront_variants || [];
		if (!variants.length) {
			frappe.show_alert(
				{ message: __('No variants to price yet'), indicator: 'orange' },
				4,
			);
			return;
		}

		const price_lists = frm.storefront_price_lists || {};
		const dialog = new frappe.ui.Dialog({
			title: __('Set Prices for All Variants'),
			fields: [
				{
					fieldname: 'default_rate',
					fieldtype: 'Currency',
					label: price_lists.default_price_list || __('Default Price'),
					description: __('Leave blank to leave this price list alone.'),
				},
				{
					fieldname: 'sale_rate',
					fieldtype: 'Currency',
					label: price_lists.sale_price_list || __('Sale Price'),
					description: __('Leave blank to leave this price list alone.'),
				},
				{
					fieldname: 'scope',
					fieldtype: 'Select',
					label: __('Apply To'),
					options: [
						{ label: __('All variants'), value: 'All variants' },
						{ label: __('Selected variants'), value: 'Selected variants' },
					],
					default: 'All variants',
				},
				{
					fieldname: 'selected_variants',
					fieldtype: 'MultiSelectPills',
					label: __('Variants'),
					depends_on: 'eval:doc.scope == "Selected variants"',
					get_data: () =>
						variants.map((variant) => ({
							value: variant.name,
							description: variant.display_name || variant.name,
						})),
				},
				{
					fieldname: 'overwrite_existing',
					fieldtype: 'Check',
					label: __('Overwrite existing prices'),
					default: 0,
					description: __('Off: only size items without a price are touched.'),
				},
			],
			primary_action_label: __('Set Prices'),
			primary_action(values) {
				if (!flt(values.default_rate) && !flt(values.sale_rate)) {
					frappe.show_alert(
						{ message: __('Enter at least one rate'), indicator: 'orange' },
						4,
					);
					return;
				}
				const selected_names =
					values.scope === 'Selected variants'
						? values.selected_variants || []
						: [];
				if (values.scope === 'Selected variants' && !selected_names.length) {
					frappe.show_alert(
						{ message: __('Select at least one variant'), indicator: 'orange' },
						4,
					);
					return;
				}

				const target_variants = selected_names.length
					? variants.filter((variant) => selected_names.includes(variant.name))
					: variants;
				const affected_count = target_variants.reduce(
					(total, variant) => total + variant.sizes.length,
					0,
				);
				frappe.confirm(
					__('This will price {0} size items', [affected_count]),
					async () =>
						await save_bulk_prices(frm, dialog, values, selected_names),
				);
			},
		});
		dialog.onhide = () => dialog.$wrapper.remove();
		dialog.show();
	}

	async function save_bulk_prices(frm, dialog, values, selected_names) {
		const args = {
			item_template: frm.doc.name,
			default_rate: flt(values.default_rate),
			sale_rate: flt(values.sale_rate),
			overwrite_existing: values.overwrite_existing ? 1 : 0,
		};
		if (selected_names.length) {
			args.style_attribute_variant_list = selected_names;
		}

		dialog.get_primary_btn().prop('disabled', true).text(__('Pricing…'));
		try {
			const response = await frappe.call({
				method: 'commera.api.variant_pricing.set_variant_prices',
				args,
			});
			const counts = response.message || {};
			dialog.hide();
			if (counts.queued) {
				frappe.show_alert(
					{
						message: __(
							'Pricing {0} items in the background — refresh in a moment.',
							[counts.queued],
						),
						indicator: 'blue',
					},
					7,
				);
			} else {
				const changed_count = (counts.created || 0) + (counts.updated || 0);
				frappe.show_alert(
					{
						message: changed_count
							? __('Priced {0} size item(s), skipped {1}', [
									changed_count,
									counts.skipped || 0,
							  ])
							: __('No price changes — every size item already had a price'),
						indicator: changed_count ? 'green' : 'blue',
					},
					5,
				);
			}
			await refresh_ecommerce_panel(frm);
		} catch (error) {
			dialog.get_primary_btn().prop('disabled', false).text(__('Set Prices'));
			throw error;
		}
	}

	async function open_receive_stock_dialog(frm, variant_name) {
		if (!variant_name) return;
		const escape_html = frappe.utils.escape_html;
		const variant = (frm.storefront_variants || []).find(
			(candidate) => candidate.name === variant_name,
		);
		const size_rows = (variant?.sizes || []).filter((row) => row.item_code);
		if (!size_rows.length) {
			frappe.show_alert(
				{
					message: __('Add sizes to this variant before receiving stock'),
					indicator: 'orange',
				},
				4,
			);
			return;
		}

		const item_codes = size_rows.map((row) => row.item_code);
		const stock_response = await frappe.call({
			method: 'commera.api.utils.get_stock_for_items',
			args: { item_codes },
		});
		const stock_by_item_code = stock_response.message || {};

		const valuation_rate_by_item_code = {};
		const item_rows = await frappe.db.get_list('Item', {
			filters: { name: ['in', item_codes] },
			fields: ['name', 'valuation_rate'],
			limit: 0,
		});
		for (const item_row of item_rows) {
			valuation_rate_by_item_code[item_row.name] = item_row.valuation_rate;
		}

		const size_data = size_rows.map((row) => ({
			size: row.size,
			item_code: row.item_code,
			current_stock: stock_by_item_code[row.item_code] || 0,
			receive_qty: 0,
			valuation_rate: valuation_rate_by_item_code[row.item_code] || 0,
		}));
		const dialog = new frappe.ui.Dialog({
			title: __('Receive Stock — {0}', [
				escape_html(variant?.display_name || variant_name),
			]),
			fields: [
				{
					fieldname: 'sizes',
					fieldtype: 'Table',
					label: __('Receive Qty per Size'),
					cannot_add_rows: true,
					cannot_delete_rows: true,
					in_place_edit: true,
					data: size_data,
					get_data: () => size_data,
					fields: [
						{
							fieldname: 'size',
							fieldtype: 'Data',
							label: __('Size'),
							in_list_view: 1,
							read_only: 1,
							columns: 2,
						},
						{
							fieldname: 'item_code',
							fieldtype: 'Data',
							label: __('Item Code'),
							in_list_view: 1,
							read_only: 1,
							columns: 2,
						},
						{
							fieldname: 'current_stock',
							fieldtype: 'Float',
							label: __('Current Stock'),
							in_list_view: 1,
							read_only: 1,
							columns: 2,
						},
						{
							fieldname: 'receive_qty',
							fieldtype: 'Float',
							label: __('Receive Qty'),
							in_list_view: 1,
							columns: 2,
						},
						{
							fieldname: 'valuation_rate',
							fieldtype: 'Currency',
							label: __('Valuation Rate'),
							in_list_view: 1,
							columns: 2,
						},
					],
				},
			],
			primary_action_label: __('Receive Stock'),
			async primary_action(values) {
				const received_quantities = {};
				const valuation_rates = {};
				for (const row of values.sizes || []) {
					if (row.item_code && flt(row.receive_qty)) {
						received_quantities[row.item_code] = flt(row.receive_qty);
						if (flt(row.valuation_rate)) {
							valuation_rates[row.item_code] = flt(row.valuation_rate);
						}
					}
				}
				dialog.get_primary_btn().prop('disabled', true).text(__('Receiving…'));
				try {
					const response = await frappe.call({
						method: 'run_doc_method',
						args: {
							dt: 'Style Attribute Variant',
							dn: variant_name,
							method: 'receive_stock',
							args: { received_quantities, valuation_rates },
						},
					});
					const stock_entry_name = response.message;
					dialog.hide();
					frappe.show_alert(
						{
							message: __('Stock received — see {0}', [
								`<a href="/app/stock-entry/${encodeURIComponent(
									stock_entry_name,
								)}" target="_blank">${escape_html(stock_entry_name)}</a>`,
							]),
							indicator: 'green',
						},
						7,
					);
					await refresh_ecommerce_panel(frm);
				} catch (error) {
					dialog
						.get_primary_btn()
						.prop('disabled', false)
						.text(__('Receive Stock'));
					throw error;
				}
			},
		});
		dialog.onhide = () => dialog.$wrapper.remove();
		dialog.show();
	}

	async function get_variants(frm) {
		const variants = await frappe.db.get_list('Style Attribute Variant', {
			filters: { item_style: frm.doc.name },
			fields: [
				'name',
				'display_name',
				'attribute_value',
				'is_published',
				'route',
			],
			limit: 0,
		});
		if (!variants.length) return [];

		const variant_docs = await Promise.all(
			variants.map((variant) =>
				frappe.db.get_doc('Style Attribute Variant', variant.name),
			),
		);
		const size_item_codes = [];
		for (const [index, variant_doc] of variant_docs.entries()) {
			variants[index].images = (variant_doc.images || [])
				.map((row) => row.image)
				.filter(Boolean);
			variants[index].sizes = (variant_doc.sizes || []).map((row) => ({
				size: row.size,
				item_code: row.item_code,
			}));
			for (const row of variants[index].sizes) {
				if (row.item_code) size_item_codes.push(row.item_code);
			}
			variants[index].seo_filled = Boolean(
				variant_doc.meta_title || variant_doc.meta_description,
			);
		}

		const { message: settings_price_lists } = await frappe.db.get_value(
			'Lifestyle Settings',
			'Lifestyle Settings',
			['default_price_list', 'sale_price_list'],
		);
		const default_price_list = settings_price_lists?.default_price_list;
		const sale_price_list = settings_price_lists?.sale_price_list;
		frm.storefront_price_lists = { default_price_list, sale_price_list };

		const default_price_by_item_code = {};
		const sale_price_by_item_code = {};
		const stock_by_item_code = {};
		if (size_item_codes.length) {
			const prices = await frappe.db.get_list('Item Price', {
				filters: {
					item_code: ['in', size_item_codes],
					price_list: [
						'in',
						[default_price_list, sale_price_list].filter(Boolean),
					],
					selling: 1,
				},
				fields: ['item_code', 'price_list', 'price_list_rate'],
				limit: 0,
			});
			for (const price of prices) {
				if (price.price_list === default_price_list) {
					default_price_by_item_code[price.item_code] = price.price_list_rate;
				} else if (price.price_list === sale_price_list) {
					sale_price_by_item_code[price.item_code] = price.price_list_rate;
				}
			}

			const stock_response = await frappe.call({
				method: 'commera.api.utils.get_stock_for_items',
				args: { item_codes: size_item_codes },
			});
			Object.assign(stock_by_item_code, stock_response.message || {});
		}

		variants.sort((first_variant, second_variant) =>
			(first_variant.display_name || first_variant.name).localeCompare(
				second_variant.display_name || second_variant.name,
			),
		);
		for (const variant of variants) {
			for (const size_row of variant.sizes) {
				const default_price = default_price_by_item_code[size_row.item_code];
				const sale_price = sale_price_by_item_code[size_row.item_code];
				size_row.default_price = default_price != null ? default_price : null;
				size_row.sale_price = sale_price != null ? sale_price : null;
				size_row.stock = stock_by_item_code[size_row.item_code] || 0;
			}
			variant.has_price = variant.sizes.some(
				(row) => row.default_price != null,
			);
			variant.stock = variant.sizes.reduce(
				(total, row) => total + row.stock,
				0,
			);
			variant.ready = Boolean(
				variant.images.length &&
					variant.sizes.length &&
					variant.has_price &&
					variant.stock > 0,
			);
		}
		return variants;
	}

	function get_blocked_reason(variant) {
		// Mirrors the veto in Style Attribute Variant.unpublish_if_incomplete_data — anything else the
		// grid flags (price, stock) is a selling concern, not a publish blocker.
		if (!variant.images.length && !variant.sizes.length) {
			return __('Needs images and sizes');
		}
		if (!variant.images.length) return __('Needs images');
		if (!variant.sizes.length) return __('Needs sizes');
		return '';
	}

	function get_swatch_color(variant) {
		const candidate = (variant.attribute_value || '').trim();
		return CSS_COLOR_PATTERN.test(candidate) ? candidate : 'var(--gray-300)';
	}

	function format_size_price(size_row, currency) {
		if (size_row.default_price == null) {
			return `<span class="text-muted">${__('Set price')}</span>`;
		}
		if (size_row.sale_price != null) {
			return `<span style="text-decoration: line-through; color: var(--text-muted); margin-right: 8px;">${format_currency(
				size_row.default_price,
				currency,
			)}</span>${format_currency(size_row.sale_price, currency)}`;
		}
		return format_currency(size_row.default_price, currency);
	}

	function format_badge(label, is_met) {
		const color = is_met ? 'green' : 'red';
		const glyph = is_met ? '✓' : '✕';
		return `<span class="indicator-pill ${color} no-indicator-dot sf-badge">${glyph} ${label}</span>`;
	}

	function format_seo_cell(variant) {
		const escape_html = frappe.utils.escape_html;
		const filled_class = variant.seo_filled ? ' sf-seo-link-filled' : '';
		const label = variant.seo_filled ? __('Edit SEO') : __('Add SEO');
		return `<span class="sf-seo-link${filled_class}" data-sf-action="edit-seo" data-sf-variant="${escape_html(
			variant.name,
		)}" title="${escape_html(__('Edit SEO details'))}">${label}</span>`;
	}

	function encode_file_url(url) {
		if (!url) return '';
		return url
			.split('/')
			.map((segment) => encodeURIComponent(segment))
			.join('/');
	}

	function format_row(variant) {
		const escape_html = frappe.utils.escape_html;
		const swatch = `<span class="sf-swatch" style="background: ${get_swatch_color(
			variant,
		)};"></span>`;
		const route = variant.route ? `/${escape_html(variant.route)}` : '';
		const thumbs = variant.images
			.slice(0, 4)
			.map(
				(image) =>
					`<span class="sf-thumb-wrap"><img class="sf-thumb" src="${escape_html(
						encode_file_url(image),
					)}" alt=""><span class="sf-thumb-remove" data-sf-action="remove-image" data-sf-variant="${escape_html(
						variant.name,
					)}" data-sf-image="${escape_html(image)}" title="${escape_html(
						__('Remove image'),
					)}">×</span></span>`,
			)
			.join('');
		const currency = frappe.boot.sysdefaults.currency;
		const size_lines = variant.sizes
			.map(
				(row) =>
					`<div class="sf-size-line"><span class="sf-chip" title="${escape_html(
						row.item_code || '',
					)}">${escape_html(row.size || '?')}</span></div>`,
			)
			.join('');
		const price_lines = variant.sizes
			.map(
				(row) =>
					`<div class="sf-size-line sf-price-link" data-sf-action="edit-prices" data-sf-variant="${escape_html(
						variant.name,
					)}" title="${escape_html(
						__('Edit prices per size'),
					)}">${format_size_price(row, currency)}</div>`,
			)
			.join('');
		const stock_lines = variant.sizes
			.map(
				(row) =>
					`<div class="sf-size-line sf-stock-link" data-sf-action="receive-stock" data-sf-variant="${escape_html(
						variant.name,
					)}" title="${escape_html(__('Receive stock per size'))}">${
						row.stock > 0
							? row.stock
							: `<span style="color: var(--red-500); font-weight: 500;">0</span>`
					}</div>`,
			)
			.join('');
		const badges =
			format_badge(__('Images'), variant.images.length > 0) +
			format_badge(__('Sizes'), variant.sizes.length > 0) +
			format_badge(__('Price'), variant.has_price) +
			format_badge(__('Stock'), variant.stock > 0);
		const blocked_reason = get_blocked_reason(variant);
		const toggle = `<label class="sf-switch${
			blocked_reason ? ' sf-switch-blocked' : ''
		}" data-sf-action="toggle-publish" data-sf-variant="${escape_html(
			variant.name,
		)}" title="${escape_html(blocked_reason || __('Publish / unpublish'))}">
				<input type="checkbox" ${variant.is_published ? 'checked' : ''} ${
					blocked_reason ? 'disabled' : ''
				}>
				<span class="sf-switch-slider"></span>
			</label>${
				blocked_reason
					? `<span class="sf-blocked">${escape_html(blocked_reason)}</span>`
					: ''
			}`;
		return `<tr>
			<td><div class="sf-variant-link" data-sf-variant="${escape_html(
				variant.name,
			)}" title="${escape_html(
				__('Open {0}', [variant.name]),
			)}" style="display: flex; align-items: center; gap: 10px;">${swatch}
				<div><div class="sf-variant-name">${escape_html(
					variant.display_name || variant.name,
				)}</div>
				<div class="sf-variant-route">${route}</div></div></div></td>
			<td>${
				variant.images.length ? `<div class="sf-thumbs">${thumbs}</div>` : ''
			}<div class="sf-images-actions"><div class="sf-dropbox" data-sf-action="drop-images" data-sf-variant="${escape_html(
				variant.name,
			)}">${__('Drop images')}</div>${
				variant.images.length
					? `<span class="sf-clear-images" data-sf-action="clear-images" data-sf-variant="${escape_html(
							variant.name,
					  )}" title="${escape_html(__('Remove all images'))}">${__(
							'Clear all',
					  )}</span>${
							variant.images.length > 4
								? `<span class="text-muted" style="font-size: var(--text-xs);">${__(
										'+{0} more',
										[variant.images.length - 4],
								  )}</span>`
								: ''
					  }`
					: ''
			}</div></td>
			<td class="sf-size-cell"><div class="sf-size-col">${size_lines}</div></td>
			<td class="sf-size-cell"><div class="sf-size-col">${price_lines}</div></td>
			<td class="sf-size-cell"><div class="sf-size-col">${stock_lines}</div></td>
			<td><div class="sf-readiness">${badges}</div></td>
			<td>${format_seo_cell(variant)}</td>
			<td style="text-align: center;">${toggle}</td>
		</tr>`;
	}

	function format_panel(variants) {
		const ready_count = variants.filter((variant) => variant.ready).length;
		const ready_color = ready_count === variants.length ? 'green' : 'orange';
		const rows = variants.map(format_row).join('');
		return `<div class="sf-panel">
			<div class="sf-toolbar">
				<div style="display: flex; align-items: center; flex-wrap: wrap; gap: 6px;">
					<span class="sf-title">${__('Storefront Variants')}</span>
					<span class="indicator-pill gray no-indicator-dot">${__(
						'{0} variants',
						[variants.length],
					)}</span>
					<span class="indicator-pill ${ready_color} no-indicator-dot">${__(
						'{0} of {1} ready',
						[ready_count, variants.length],
					)}</span>
				</div>
				<div class="sf-actions">
					<button class="btn btn-default btn-sm" data-sf-action="generate-variants">${__(
						'Generate Variants',
					)}</button>
					<button class="btn btn-default btn-sm" data-sf-action="bulk-upload-images">${__(
						'Bulk Upload Images',
					)}</button>
					<button class="btn btn-default btn-sm" data-sf-action="bulk-set-prices">${__(
						'Set Prices for All Variants',
					)}</button>
					<button class="btn btn-primary btn-sm" data-sf-action="publish-all-ready">${__(
						'Publish All Ready',
					)}</button>
				</div>
			</div>
			<div class="sf-card">
				<table class="sf-variant-grid">
					<thead><tr>
						<th>${__('Variant')}</th><th>${__('Images')}</th><th>${__(
							'Size',
						)}</th><th>${__('Price')}</th><th>${__('Stock')}</th><th>${__(
							'Readiness',
						)}</th><th>${__('SEO')}</th><th style="text-align: center;">${__(
							'Published',
						)}</th>
					</tr></thead>
					<tbody>${rows}</tbody>
				</table>
			</div>
		</div>`;
	}

	function format_empty_state() {
		return `<div class="sf-card" style="padding: 48px 24px; text-align: center;">
			<div style="font-size: var(--text-lg); font-weight: 600; margin-bottom: 6px;">${__(
				'No storefront variants yet',
			)}</div>
			<div style="color: var(--text-muted); margin-bottom: 16px;">${__(
				'Generate a Style Attribute Variant for each colour to start selling this item online.',
			)}</div>
			<button class="btn btn-primary btn-sm" data-sf-action="generate-variants">${__(
				'Generate Variants',
			)}</button>
		</div>`;
	}

	function format_note(message) {
		return `<div class="sf-card" style="padding: 24px; text-align: center; color: var(--text-muted);">${frappe.utils.escape_html(
			message,
		)}</div>`;
	}
})();
