// Copyright (c) 2026, company@bwhstudios.com and contributors
// For license information, please see license.txt

// Frappe concatenates every `doctype_js` file for a doctype into one `new Function()` scope
// (script_manager.js `setup`), so a top-level name here would collide with the other scripts.
(() => {
	frappe.ui.form.on('Lifestyle Settings', {
		refresh(frm) {
			refresh_footer_editor(frm);
		},
	});

	const FOOTER_EDITOR_METHOD_PREFIX =
		'commera.lifestyle_shop_ecommerce.doctype.lifestyle_settings.footer.footer_preview.';

	const LINK_SOURCE_URL = 'Custom URL';
	const LINK_SOURCE_PAGE = 'Existing Page';

	const PREVIEW_RELOAD_DELAY = 350;

	// Fields the storefront footer reads. The preview page takes them as query params so an unsaved
	// edit shows up without the shop owner having to save first.
	const PREVIEW_OVERRIDE_FIELDS = [
		'newsletter_title',
		'newsletter_description',
		'copyright_text',
		'contact_phone',
		'contact_email',
		'working_hours',
		'store_name',
		'footer_logo',
		'payment_methods_image',
		'vat_certificate_image',
		'facebook_url',
		'instagram_url',
		'twitter_url',
		'tiktok_url',
		'snapchat_url',
		'footer_bg_color',
		'footer_text_color',
	];

	const escape_html = (value) => frappe.utils.escape_html(value);

	async function get_footer_data(method, args) {
		const response = await frappe.call({
			method: FOOTER_EDITOR_METHOD_PREFIX + method,
			args: args || {},
		});
		return response.message;
	}

	async function refresh_footer_editor(frm) {
		const field = frm.get_field('footer_editor');
		if (!field) return;
		const wrapper = field.$wrapper;
		wrapper.html(
			`<div class="text-muted" style="padding: 8px 0;">${__(
				'Loading footer editor…',
			)}</div>`,
		);

		let data;
		try {
			data = await get_footer_data('get_footer_editor_data');
		} catch (error) {
			wrapper.html(
				`<div class="text-muted" style="padding: 8px 0;">${__(
					'Could not load footer data.',
				)}</div>`,
			);
			return;
		}

		add_footer_editor(frm, wrapper, data);
	}

	function add_footer_editor(frm, wrapper, data) {
		wrapper.html(
			format_header() +
				format_board(data) +
				format_extras(frm) +
				format_preview(frm),
		);
		add_click_handlers(frm, wrapper, data);
		add_sortable(frm, wrapper, data);
		add_preview_handlers(frm, wrapper);
	}

	// A section change writes to Lifestyle Settings itself, so the open form is now stale. Reloading it
	// would throw away whatever the shop owner is mid-edit on another tab, hence the dirty branch.
	async function refresh_after_section_change(frm, wrapper, data) {
		if (frm.is_dirty()) {
			frm.doc.modified = data.modified;
			add_footer_editor(frm, wrapper, data);
			return;
		}
		await frm.reload_doc();
	}

	function format_header() {
		return `
		<div style="display: flex; align-items: center; gap: 10px; margin: 4px 0 4px;">
			<span style="font-size: var(--text-lg); font-weight: 600;">${__(
				'Footer Editor',
			)}</span>
			<span style="flex: 1;"></span>
			<button class="btn btn-default btn-sm footer-editor-add-column">+ ${__(
				'Add column',
			)}</button>
		</div>
		<div class="text-muted" style="margin-bottom: 12px; font-size: var(--text-sm);">
			${__(
				'Manage footer columns and links here instead of jumping between Footer Section Config and Footer Link.',
			)}
		</div>`;
	}

	function format_board(data) {
		return `
		<div class="footer-editor-board" style="display: flex; gap: 12px; align-items: stretch; flex-wrap: wrap; margin-bottom: 12px;">
			${data.columns.map(format_card).join('')}
		</div>`;
	}

	function format_card(column) {
		return `
		<div class="footer-editor-card" data-section="${escape_html(column.name)}"
			style="flex: 1 1 200px; min-width: 200px; max-width: 260px; background: var(--card-bg, var(--fg-color));
			border: 1px solid var(--border-color); border-radius: var(--border-radius-md, 8px); padding: 10px;
			display: flex; flex-direction: column;">
			<div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
				<span class="footer-editor-col-handle" style="cursor: grab; color: var(--text-muted); font-size: 14px;"
					title="${__('Drag to reorder')}">⠿</span>
				<span style="font-weight: 600;">${escape_html(column.title)}</span>
				<span class="footer-editor-rename-col" style="cursor: pointer; color: var(--text-muted);"
					title="${__('Rename')}">✎</span>
				<span style="flex: 1;"></span>
				<span class="text-muted" style="font-size: 11px; white-space: nowrap;">${
					column.links.length
				} ${__('links')}</span>
				<span class="footer-editor-delete-col" style="cursor: pointer; color: var(--text-muted); padding: 0 2px;"
					title="${__('Delete')}">✕</span>
			</div>
			<div class="footer-editor-links" data-section="${escape_html(column.name)}"
				style="flex: 1;">${column.links.map(format_link_row).join('')}</div>
			<div style="margin-top: 8px;">
				<button class="btn btn-default btn-xs footer-editor-add-link" style="width: 100%;">+ ${__(
					'Add link',
				)}</button>
			</div>
		</div>`;
	}

	function format_link_row(row) {
		return `
		<div class="footer-editor-link-row" data-row="${escape_html(row.name)}"
			style="display: flex; align-items: center; gap: 6px; padding: 4px 6px; border: 1px solid var(--border-color);
			border-radius: 6px; margin-bottom: 5px; background: var(--control-bg);">
			<span class="footer-editor-link-handle" style="cursor: grab; color: var(--text-muted);">⠿</span>
			<span class="footer-editor-edit-link" style="flex: 1; min-width: 0; cursor: pointer;">
				<span style="font-size: var(--text-sm); font-weight: 500;">${escape_html(
					row.link_label,
				)}</span>
				<span class="text-muted" style="font-size: 11px; display: block; overflow: hidden; text-overflow: ellipsis;
					white-space: nowrap;">${escape_html(row.link_url)}</span>
			</span>
			<span class="footer-editor-delete-link" style="cursor: pointer; color: var(--text-muted); padding: 0 2px;"
				title="${__('Remove')}">✕</span>
		</div>`;
	}

	function format_extra_block(label, value, fieldname) {
		return `
		<div style="flex: 1 1 180px; min-width: 180px;">
			<div style="display: flex; align-items: center; gap: 6px;">
				<span class="text-muted" style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.4px;">
					${label}
				</span>
				<button class="btn btn-default btn-xs footer-editor-extra-edit" data-fieldname="${fieldname}"
					style="padding: 0px 6px;">${__('Edit')}</button>
			</div>
			<div style="font-size: var(--text-sm); margin-top: 3px;">${value}</div>
		</div>`;
	}

	function format_social_chips(doc) {
		const networks = [
			['Facebook', doc.facebook_url],
			['Instagram', doc.instagram_url],
			['X / Twitter', doc.twitter_url],
			['TikTok', doc.tiktok_url],
			['Snapchat', doc.snapchat_url],
		].filter(([, url]) => url);

		if (!networks.length) {
			return `<span class="text-muted">${__('No social links set')}</span>`;
		}
		return networks
			.map(
				([network]) =>
					`<span class="indicator-pill gray">${escape_html(network)}</span>`,
			)
			.join(' ');
	}

	function format_extras(frm) {
		const doc = frm.doc;
		const not_set = `<span class="text-muted">${__('Not set')}</span>`;
		const payment_image = doc.payment_methods_image
			? escape_html(doc.payment_methods_image.split('/').pop())
			: not_set;

		return `
		<div style="background: var(--card-bg, var(--fg-color)); border: 1px solid var(--border-color);
			border-radius: var(--border-radius-md, 8px); padding: 10px 12px; margin-bottom: 14px;">
			<div style="font-weight: 600; margin-bottom: 8px;">${__('Footer extras')}</div>
			<div style="display: flex; gap: 16px; flex-wrap: wrap;">
				${format_extra_block(
					__('Newsletter'),
					`${escape_html(doc.newsletter_title) || not_set}
					<span class="text-muted" style="display: block; font-size: 11px;">
						${escape_html(doc.newsletter_description)}
					</span>`,
					'newsletter_title',
				)}
				${format_extra_block(
					__('Copyright'),
					escape_html(doc.copyright_text) || not_set,
					'copyright_text',
				)}
				${format_extra_block(
					__('Social links'),
					format_social_chips(doc),
					'facebook_url',
				)}
				${format_extra_block(
					__('Payment methods image'),
					payment_image,
					'payment_methods_image',
				)}
			</div>
		</div>`;
	}

	function get_preview_url(frm) {
		const params = new URLSearchParams();
		for (const fieldname of PREVIEW_OVERRIDE_FIELDS) {
			const value = frm.doc[fieldname];
			if (value) params.set(fieldname, value);
		}
		return `/footer_editor_preview?${params.toString()}`;
	}

	function refresh_preview(frm) {
		const field = frm.get_field('footer_editor');
		const iframe = field?.$wrapper.find('.footer-editor-preview-frame').get(0);
		if (iframe) iframe.src = get_preview_url(frm);
	}

	// The preview page renders the whole storefront layout; only the footer is interesting, so the
	// iframe is grown to its full document height and then slid up under a fixed-height crop box.
	function crop_preview_to_footer(iframe) {
		const preview_document = iframe.contentDocument;
		const footer = preview_document?.querySelector('footer');
		const crop_box = iframe.parentElement;
		if (!footer || !crop_box) return;

		const footer_rect = footer.getBoundingClientRect();
		iframe.style.height = `${Math.ceil(
			preview_document.documentElement.scrollHeight,
		)}px`;
		iframe.style.marginTop = `-${Math.floor(footer_rect.top)}px`;
		crop_box.style.height = `${Math.ceil(footer_rect.height)}px`;
	}

	function add_preview_handlers(frm, wrapper) {
		const iframe = wrapper.find('.footer-editor-preview-frame').get(0);
		if (!iframe) return;

		iframe.addEventListener('load', () => crop_preview_to_footer(iframe));

		frm.$wrapper
			.off('shown.bs.tab.footer_editor')
			.on('shown.bs.tab.footer_editor', () => crop_preview_to_footer(iframe));
	}

	const refresh_preview_debounced = frappe.utils.debounce(
		refresh_preview,
		PREVIEW_RELOAD_DELAY,
	);

	frappe.ui.form.on(
		'Lifestyle Settings',
		Object.fromEntries(
			PREVIEW_OVERRIDE_FIELDS.map((fieldname) => [
				fieldname,
				refresh_preview_debounced,
			]),
		),
	);

	function format_preview(frm) {
		return `
		<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
			<span style="font-weight: 600;">${__('Storefront preview')}</span>
		</div>
		<div style="border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; min-height: 160px;">
			<iframe class="footer-editor-preview-frame" src="${escape_html(
				get_preview_url(frm),
			)}"
				style="width: 100%; border: 0; display: block;"
				title="${__('Storefront footer preview')}"></iframe>
		</div>`;
	}

	function get_column(data, section_name) {
		return data.columns.find((column) => column.name === section_name);
	}

	function get_closest_section(event) {
		return $(event.currentTarget).closest('[data-section]').data('section');
	}

	function get_closest_link(data, event) {
		const column = get_column(data, get_closest_section(event));
		const row_name = $(event.currentTarget)
			.closest('.footer-editor-link-row')
			.data('row');
		const row = column?.links.find((link_row) => link_row.name === row_name);
		return { column, row };
	}

	function add_click_handlers(frm, wrapper, data) {
		wrapper.off('click.footer_editor');

		wrapper.on('click.footer_editor', '.footer-editor-add-column', () => {
			open_add_column_dialog(frm, wrapper);
		});

		wrapper.on('click.footer_editor', '.footer-editor-rename-col', (event) => {
			const column = get_column(data, get_closest_section(event));
			if (column) open_rename_column_dialog(frm, wrapper, column);
		});

		wrapper.on('click.footer_editor', '.footer-editor-delete-col', (event) => {
			const column = get_column(data, get_closest_section(event));
			if (column) confirm_delete_column(frm, wrapper, column);
		});

		wrapper.on('click.footer_editor', '.footer-editor-add-link', (event) => {
			const column = get_column(data, get_closest_section(event));
			if (column) open_link_dialog(frm, wrapper, column, null, data.pages);
		});

		wrapper.on('click.footer_editor', '.footer-editor-edit-link', (event) => {
			const { column, row } = get_closest_link(data, event);
			if (column && row)
				open_link_dialog(frm, wrapper, column, row, data.pages);
		});

		wrapper.on('click.footer_editor', '.footer-editor-delete-link', (event) => {
			const { column, row } = get_closest_link(data, event);
			if (column && row) confirm_delete_link(frm, wrapper, column, row);
		});

		wrapper.on('click.footer_editor', '.footer-editor-extra-edit', (event) => {
			const fieldname = $(event.currentTarget).data('fieldname');
			if (fieldname) frm.scroll_to_field(fieldname);
		});
	}

	function add_sortable(frm, wrapper, data) {
		const board = wrapper.find('.footer-editor-board').get(0);
		if (board) {
			new Sortable(board, {
				handle: '.footer-editor-col-handle',
				animation: 150,
				onEnd: async () => {
					const ordered_names = Array.from(board.children).map(
						(card) => card.dataset.section,
					);
					const fresh_data = await get_footer_data('reorder_footer_sections', {
						ordered_names,
					});
					await refresh_after_section_change(frm, wrapper, fresh_data);
				},
			});
		}

		wrapper.find('.footer-editor-links').each((_index, container) => {
			new Sortable(container, {
				handle: '.footer-editor-link-handle',
				animation: 150,
				group: 'footer-links',
				onEnd: async (event) => {
					let fresh_data;
					if (event.from === event.to) {
						fresh_data = await get_footer_data('reorder_footer_links', {
							section_name: event.to.dataset.section,
							ordered_row_names: Array.from(event.to.children).map(
								(row) => row.dataset.row,
							),
						});
					} else {
						fresh_data = await get_footer_data('move_footer_link', {
							from_section: event.from.dataset.section,
							to_section: event.to.dataset.section,
							link_row_name: event.item.dataset.row,
							target_index: event.newIndex,
						});
					}
					add_footer_editor(frm, wrapper, fresh_data);
				},
			});
		});
	}

	function open_add_column_dialog(frm, wrapper) {
		frappe.prompt(
			{
				fieldname: 'title',
				fieldtype: 'Data',
				label: __('Column Title'),
				reqd: 1,
			},
			async (values) => {
				const data = await get_footer_data('add_footer_section', {
					title: values.title,
				});
				await refresh_after_section_change(frm, wrapper, data);
			},
			__('Add Footer Column'),
			__('Add'),
		);
	}

	function open_rename_column_dialog(frm, wrapper, column) {
		frappe.prompt(
			{
				fieldname: 'title',
				fieldtype: 'Data',
				label: __('Column Title'),
				reqd: 1,
				default: column.title,
			},
			async (values) => {
				const data = await get_footer_data('rename_footer_section', {
					old_name: column.name,
					new_name: values.title,
				});
				await refresh_after_section_change(frm, wrapper, data);
			},
			__('Rename Column'),
			__('Rename'),
		);
	}

	function confirm_delete_column(frm, wrapper, column) {
		frappe.confirm(
			__('Delete "{0}" and its {1} link(s)? This cannot be undone.', [
				escape_html(column.title),
				column.links.length,
			]),
			async () => {
				const data = await get_footer_data('delete_footer_section', {
					name: column.name,
				});
				await refresh_after_section_change(frm, wrapper, data);
			},
		);
	}

	function confirm_delete_link(frm, wrapper, column, row) {
		frappe.confirm(
			__('Remove "{0}" from {1}?', [
				escape_html(row.link_label),
				escape_html(column.title),
			]),
			async () => {
				const data = await get_footer_data('delete_footer_link', {
					section_name: column.name,
					link_row_name: row.name,
				});
				add_footer_editor(frm, wrapper, data);
			},
		);
	}

	// Core `Web Page` routes are relative ("about" -> /about); the storefront's own routes already
	// arrive as absolute paths.
	function get_page_url(page) {
		return page.route.startsWith('/') ? page.route : `/${page.route}`;
	}

	function get_link_dialog_fields(existing_row, pages, on_page_change) {
		return [
			{
				fieldname: 'source',
				fieldtype: 'Select',
				label: __('Link Source'),
				options: [
					{ value: LINK_SOURCE_URL, label: __('Custom URL') },
					{ value: LINK_SOURCE_PAGE, label: __('Existing Page') },
				],
				default: LINK_SOURCE_URL,
				hidden: existing_row ? 1 : 0,
			},
			{
				fieldname: 'page',
				fieldtype: 'Select',
				label: __('Page'),
				// Core renders an option's label as HTML, so a page titled with a tag would run it.
				options: pages.map((page) => ({
					value: page.name,
					label: escape_html(page.name),
				})),
				depends_on: `eval:doc.source=="${LINK_SOURCE_PAGE}"`,
				onchange: on_page_change,
			},
			{
				fieldname: 'label',
				fieldtype: 'Data',
				label: __('Label'),
				reqd: 1,
				default: existing_row ? existing_row.link_label : '',
			},
			{
				fieldname: 'url',
				fieldtype: 'Data',
				label: __('URL'),
				reqd: 1,
				default: existing_row ? existing_row.link_url : '',
			},
		];
	}

	function open_link_dialog(frm, wrapper, column, existing_row, pages) {
		const page_list = pages || [];
		const is_edit = Boolean(existing_row);

		const set_values_from_page = () => {
			const page = page_list.find(
				(row) => row.name === dialog.get_value('page'),
			);
			if (!page) return;
			dialog.set_value('label', page.name);
			dialog.set_value('url', get_page_url(page));
		};

		const dialog = new frappe.ui.Dialog({
			title: is_edit ? __('Edit Link') : __('Add Link'),
			fields: get_link_dialog_fields(
				existing_row,
				page_list,
				set_values_from_page,
			),
			primary_action_label: is_edit ? __('Save') : __('Add'),
			primary_action: async (values) => {
				dialog.hide();
				const data = is_edit
					? await get_footer_data('update_footer_link', {
							section_name: column.name,
							link_row_name: existing_row.name,
							label: values.label,
							url: values.url,
					  })
					: await get_footer_data('add_footer_link', {
							section_name: column.name,
							label: values.label,
							url: values.url,
					  });
				add_footer_editor(frm, wrapper, data);
			},
		});

		dialog.show();
	}
})();
