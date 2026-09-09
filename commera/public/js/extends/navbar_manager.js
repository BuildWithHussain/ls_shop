// Copyright (c) 2026, company@bwhstudios.com and contributors
// For license information, please see license.txt

// Frappe concatenates every `doctype_js` file for a doctype into one `new Function()` scope
// (script_manager.js `setup`), so a top-level name here would collide with the other scripts.
(() => {
	frappe.ui.form.on('Lifestyle Settings', {
		refresh(frm) {
			refresh_navbar_editor(frm);
		},
	});

	const MENU_MANAGER_METHOD_PREFIX =
		'commera.lifestyle_shop_ecommerce.doctype.lifestyle_settings.navbar.navbar_manager.';
	const MAX_MENU_DEPTH = 3;
	const NO_LINK = 'No Link';
	const LINK_TYPES = [NO_LINK, 'Item Group', 'Brand', 'URL'];
	const PRODUCT_PAGE_LENGTH = 50;
	const PRODUCT_SEARCH_DELAY = 300;

	const SELECTION_PAGE = 'page';
	const SELECTION_SCOPE = 'scope';

	const EDITOR_CHROME_HEIGHT = 230;
	const EDITOR_MIN_HEIGHT = 460;
	const EDITOR_STACK_BREAKPOINT = 991;

	const PREVIEW_OPEN_KEY = 'navbar_manager_preview_open';

	const TOOLBAR_LINK_STYLE =
		'padding:0; border:none; background:none; font-size:12px;';

	const DELETE_ALL_CONFIRMATION = 'DELETE';

	const CARET =
		'<svg width="8" height="8" viewBox="0 0 8 8" fill="currentColor"><path d="M2 0l4 4-4 4z"/></svg>';

	const DRAG_HANDLE =
		'<svg width="12" height="14" viewBox="0 0 24 24" fill="currentColor"><circle cx="8" cy="5" r="2"/><circle cx="16" cy="5" r="2"/><circle cx="8" cy="12" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="8" cy="19" r="2"/><circle cx="16" cy="19" r="2"/></svg>';

	const escape_html = (value) => frappe.utils.escape_html(value);

	async function get_menu_response(method, args) {
		const response = await frappe.call({
			method: MENU_MANAGER_METHOD_PREFIX + method,
			args: args || {},
		});
		return response.message;
	}

	async function get_menu(method, args) {
		return (await get_menu_response(method, args)).menu;
	}

	function find_node(nodes, name) {
		for (const node of nodes) {
			if (node.name === name) return node;
			const found = find_node(node.children, name);
			if (found) return found;
		}
		return null;
	}

	function get_node_depth(nodes, name, depth = 0) {
		for (const node of nodes) {
			if (node.name === name) return depth;
			const found = get_node_depth(node.children, name, depth + 1);
			if (found !== null) return found;
		}
		return null;
	}

	function get_ancestor_names(nodes, name, trail = []) {
		for (const node of nodes) {
			if (node.name === name) return trail;
			const found = get_ancestor_names(node.children, name, [
				...trail,
				node.name,
			]);
			if (found) return found;
		}
		return null;
	}

	function get_parent_names(nodes, names = []) {
		for (const node of nodes) {
			if (!node.children.length) continue;
			names.push(node.name);
			get_parent_names(node.children, names);
		}
		return names;
	}

	function expand_ancestors(state) {
		for (const name of get_ancestor_names(state.menu, state.selected) || []) {
			state.expanded.add(name);
		}
	}

	async function refresh_navbar_editor(frm) {
		const field = frm.get_field('navbar_editor');
		if (!field) return;
		const wrapper = field.$wrapper;
		wrapper.html(
			`<div class="text-muted" style="padding: 8px 0;">${__(
				'Loading navbar editor…',
			)}</div>`,
		);

		let menu;
		try {
			menu = await get_menu('get_menu_editor_data');
		} catch (error) {
			wrapper.html(
				`<div class="text-muted" style="padding: 8px 0;">${__(
					'Could not load navbar data.',
				)}</div>`,
			);
			return;
		}

		add_navbar_editor(wrapper, menu);
	}

	function add_navbar_editor(wrapper, menu) {
		wrapper.html(format_shell(localStorage.getItem(PREVIEW_OPEN_KEY) !== 'no'));
		const body = wrapper.get(0);
		const tree_pane = body.querySelector('.menu-manager-tree');
		const inspector_pane = body.querySelector('.menu-manager-inspector');
		const preview_pane = body.querySelector('.menu-manager-preview');
		const add_child_button = body.querySelector('.menu-manager-add-child');

		const state = {
			menu,
			selected: null,
			open_tab: 0,
			inspector: null,
			expanded: new Set(),
		};

		function refresh() {
			const selected_depth = state.selected
				? get_node_depth(state.menu, state.selected)
				: null;
			if (selected_depth === null) state.selected = null;
			expand_ancestors(state);
			refresh_tree(tree_pane, state);
			refresh_inspector(inspector_pane, state, refresh);
			refresh_preview(preview_pane, state);
			add_child_button.disabled =
				selected_depth === null || selected_depth + 1 >= MAX_MENU_DEPTH;
			add_menu_sortable(tree_pane, state, refresh);
		}

		add_menu_click_handlers(
			body,
			tree_pane,
			preview_pane,
			add_child_button,
			state,
			refresh,
		);
		refresh();
	}

	function format_editor_styles() {
		return `
		<style>
			.menu-manager-editor { display:flex; flex-direction:column; gap:14px;
				height:calc(100vh - ${EDITOR_CHROME_HEIGHT}px); min-height:${EDITOR_MIN_HEIGHT}px; }
			.menu-manager-columns { display:flex; gap:16px; flex:1 1 auto; min-height:0; }
			.menu-manager-column { flex:1 1 340px; min-width:300px; display:flex;
				flex-direction:column; min-height:0; }
			@media (max-width: ${EDITOR_STACK_BREAKPOINT}px) {
				.menu-manager-editor { height:auto; min-height:0; }
				.menu-manager-columns { flex-wrap:wrap; }
			}
		</style>`;
	}

	function format_preview_band(is_open) {
		return `
		<div style="flex:0 0 auto;">
			<div style="display:flex; align-items:center; justify-content:space-between; gap:8px;
				margin-bottom:${is_open ? '10px' : '0'};">
				<span style="font-size:14px; font-weight:600; color:var(--text-color);">${__(
					'Preview — first tab expanded',
				)}</span>
				<button class="btn btn-xs btn-default menu-manager-preview-toggle">${
					is_open ? __('Hide preview') : __('Show preview')
				}</button>
			</div>
			<div class="menu-manager-preview" ${
				is_open ? '' : 'style="display:none;"'
			}></div>
		</div>`;
	}

	function format_shell(is_preview_open) {
		return `
		${format_editor_styles()}
		<div class="menu-manager-editor">
			${format_preview_band(is_preview_open)}
			<div class="menu-manager-columns">
				<div class="menu-manager-column">
					<div style="flex:0 0 auto; font-size:14px; font-weight:600; color:var(--text-color);
						margin-bottom:10px;">${__('Structure')}</div>
					<div style="position:relative; flex:1 1 auto; min-height:0;">
						<div class="menu-manager-tree menu-manager-scroll"
							style="height:100%; overflow-y:auto; padding-right:4px; padding-bottom:24px;"></div>
						<div style="position:absolute; bottom:0; left:0; right:4px; height:32px; pointer-events:none;
							background:linear-gradient(to bottom, transparent, var(--card-bg, #fff));"></div>
					</div>
					<div style="flex:0 0 auto; display:flex; gap:6px; margin-top:10px;">
						<button class="btn btn-xs btn-default menu-manager-add-root">+ ${__(
							'Add Section',
						)}</button>
						<button class="btn btn-xs btn-default menu-manager-add-child" disabled
							title="${__('Select an entry first')}">+ ${__('Add Child')}</button>
						<button class="btn btn-xs btn-default menu-manager-import"
							title="${__(
								'Copy the Item Group tree into the menu. Groups already in the menu are skipped.',
							)}">${__('Import from Item Group')}</button>
						${format_toolbar_controls()}
					</div>
				</div>
				<div class="menu-manager-inspector menu-manager-column"
					style="border:1px solid var(--border-color); border-radius:var(--border-radius, 6px);
						background:var(--card-bg, var(--fg-color)); overflow:hidden;"></div>
			</div>
		</div>`;
	}

	function format_toolbar_controls() {
		return `
		<span style="margin-left:auto; display:flex; gap:10px; align-items:center;">
			<button class="btn btn-xs menu-manager-expand-all"
				style="${TOOLBAR_LINK_STYLE} color:var(--text-muted);">${__(
					'Expand all',
				)}</button>
			<button class="btn btn-xs menu-manager-collapse-all"
				style="${TOOLBAR_LINK_STYLE} color:var(--text-muted);">${__(
					'Collapse all',
				)}</button>
			<span style="width:1px; height:12px; background:var(--border-color);"></span>
			<button class="btn btn-xs menu-manager-delete-all"
				title="${__(
					'Delete every menu entry and start over. Item Groups, brands and products are not affected.',
				)}"
				style="${TOOLBAR_LINK_STYLE} color:var(--red-500);">${__('Delete all')}</button>
		</span>`;
	}

	function format_status_chip(node) {
		const color = node.visible ? 'green' : 'gray';
		const text = node.visible ? __('Shown') : __('Hidden');
		return `<span class="indicator-pill ${color}" style="font-size:11px; flex-shrink:0;">${text}</span>`;
	}

	function is_node_expanded(state, node) {
		return Boolean(node.children.length) && state.expanded.has(node.name);
	}

	function format_node_caret(state, node) {
		if (!node.children.length) {
			return '<span style="width:10px; flex-shrink:0;"></span>';
		}
		const rotation = is_node_expanded(state, node) ? 90 : 0;
		return `<span class="menu-node-caret" title="${__('Expand or collapse')}"
		style="width:10px; flex-shrink:0; display:flex; align-items:center; justify-content:center;
			color:var(--text-muted); cursor:pointer; transform:rotate(${rotation}deg);">${CARET}</span>`;
	}

	function format_node_row(state, node, depth) {
		const is_selected = state.selected === node.name;
		return `
		<div class="menu-node-row" data-name="${escape_html(
			node.name,
		)}" data-depth="${depth}"
			style="display:flex; align-items:center; gap:8px; padding:5px 8px; margin-bottom:4px;
				border:1px solid ${
					is_selected ? 'var(--text-color)' : 'var(--border-color)'
				};
				border-radius:var(--border-radius, 6px); background:var(--card-bg, var(--fg-color));
				${node.visible ? '' : 'opacity:0.55;'} cursor:pointer;">
			<span class="drag-handle" style="cursor:grab; color:var(--text-muted); display:flex;">${DRAG_HANDLE}</span>
			${format_node_caret(state, node)}
			<span style="font-size:13px; ${depth === 0 ? 'font-weight:600;' : ''} color:var(--text-color); flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
				${escape_html(node.label)}
			</span>
			${format_status_chip(node)}
		</div>`;
	}

	function format_nodes(state, nodes, depth) {
		return nodes
			.map(
				(node) => `
		<div class="menu-node" data-name="${escape_html(node.name)}">
			${format_node_row(state, node, depth)}
			${format_children(state, node, depth)}
		</div>`,
			)
			.join('');
	}

	function format_children(state, node, depth) {
		if (depth + 1 >= MAX_MENU_DEPTH) return '';
		const hidden =
			node.children.length && !is_node_expanded(state, node)
				? 'display:none;'
				: '';
		return `<div class="menu-children" data-parent="${escape_html(node.name)}"
		style="margin-left:22px; margin-top:2px; margin-bottom:4px; min-height:8px; ${hidden}">${format_nodes(
			state,
			node.children,
			depth + 1,
		)}</div>`;
	}

	function refresh_tree(tree_pane, state) {
		tree_pane.innerHTML = `<div class="menu-children" data-parent="">${format_nodes(
			state,
			state.menu,
			0,
		)}</div>`;
	}

	function get_inspector_fields(node, depth) {
		const fields = [
			{
				fieldname: 'display_name',
				fieldtype: 'Data',
				label: __('Label'),
				reqd: 1,
				default: node.label,
			},
			{ fieldtype: 'Column Break' },
			{
				fieldname: 'link_type',
				fieldtype: 'Select',
				label: __('Links To'),
				options: LINK_TYPES.join('\n'),
				default: node.link_type || NO_LINK,
			},
			{ fieldtype: 'Section Break' },
			{
				fieldname: 'item_groups',
				fieldtype: 'MultiSelectList',
				label: __('Item Groups'),
				depends_on: 'eval:doc.link_type == "Item Group"',
				default: node.item_groups,
				get_data: (search_text) =>
					frappe.db.get_link_options('Item Group', search_text),
			},
			{
				fieldname: 'brand',
				fieldtype: 'Link',
				label: __('Brand'),
				options: 'Brand',
				depends_on: 'eval:doc.link_type == "Brand"',
				default: node.brand,
			},
			{
				fieldname: 'url',
				fieldtype: 'Data',
				label: __('URL'),
				depends_on: 'eval:doc.link_type == "URL"',
				default: node.url,
			},
		];

		if (!depth) {
			fields.push({
				fieldname: 'route_slug',
				fieldtype: 'Data',
				label: __('Page URL'),
				reqd: 1,
				description: `/${escape_html(node.route_slug)}`,
				default: node.route_slug,
			});
		}

		fields.push(
			{
				fieldtype: 'Section Break',
				label: __('Display'),
				collapsible: 1,
				css_class: 'navbar-inspector-display',
			},
			{
				fieldname: 'icon',
				fieldtype: 'Data',
				label: __('Icon'),
				default: node.icon,
			},
			{
				fieldname: 'image',
				fieldtype: 'Attach Image',
				label: __('Image'),
				default: node.image,
			},
			{
				fieldtype: 'Section Break',
				label: __('Search Engine Listing'),
				collapsible: 1,
				css_class: 'navbar-inspector-seo',
			},
			{
				fieldname: 'meta_title',
				fieldtype: 'Data',
				label: __('Meta Title'),
				default: node.meta_title,
			},
			{
				fieldname: 'meta_description',
				fieldtype: 'Small Text',
				label: __('Meta Description'),
				default: node.meta_description,
			},
			{
				fieldname: 'og_image',
				fieldtype: 'Attach Image',
				label: __('OG Image'),
				default: node.og_image,
			},
			{
				fieldname: 'noindex',
				fieldtype: 'Check',
				label: __('Hide from search engines'),
				default: node.noindex,
			},
		);

		return fields;
	}

	function format_inspector_shell(node) {
		const visibility_label = node.visible ? __('Hide') : __('Show');
		return `
		<div style="flex:0 0 auto; display:flex; align-items:center; justify-content:space-between; gap:8px;
			padding:10px 14px; border-bottom:1px solid var(--border-color);">
			<div style="font-size:14px; font-weight:600; color:var(--text-color); min-width:0;
				overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
				${escape_html(node.label)}
			</div>
			<button class="btn btn-xs btn-primary inspector-save">${__('Save')}</button>
		</div>
		<div class="menu-manager-scroll" style="flex:1 1 auto; min-height:0; overflow-y:auto; padding:12px 14px;">
			<div class="menu-inspector-form"></div>
			<div style="border-top:1px solid var(--border-color); margin:12px 0 10px;"></div>
			<div style="display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:8px;">
				<span style="font-size:13px; color:var(--text-color);">${__(
					'Menu entry',
				)}</span>
				<span style="display:flex; align-items:center; gap:8px;">
					${format_status_chip(node)}
					<button class="btn btn-xs btn-default inspector-visibility"
						title="${__(
							'Show or hide this menu entry — does not change any product',
						)}">${visibility_label}</button>
				</span>
			</div>
			<div class="menu-manager-products"></div>
			<div style="border-top:1px solid var(--border-color); margin:12px 0 10px;"></div>
			<button class="btn btn-xs btn-default inspector-delete"
				style="color:var(--red-500);">${__('Delete entry')}</button>
		</div>`;
	}

	function refresh_inspector(inspector_pane, state, refresh) {
		state.inspector = null;
		const node = state.selected ? find_node(state.menu, state.selected) : null;
		if (!node) {
			inspector_pane.innerHTML = `<div class="text-muted" style="font-size:13px; padding:12px 14px;">${__(
				'Select an entry on the left to edit it.',
			)}</div>`;
			return;
		}

		inspector_pane.innerHTML = format_inspector_shell(node);
		state.inspector = new frappe.ui.FieldGroup({
			fields: get_inspector_fields(node, get_node_depth(state.menu, node.name)),
			body: inspector_pane.querySelector('.menu-inspector-form'),
		});
		state.inspector.make();
		state.inspector.refresh();
		for (const section of state.inspector.sections) {
			if (section.df.collapsible) section.collapse(true);
		}
		add_inspector_actions(inspector_pane, node, state, refresh);
		refresh_products(inspector_pane, node, state, refresh);
	}

	function get_link_target(link_type, values) {
		if (link_type === 'Item Group') return values.item_groups || [];
		if (link_type === 'Brand') return values.brand || '';
		if (link_type === 'URL') return values.url || '';
		return '';
	}

	function get_node_arguments(node, values) {
		const link_type = values.link_type === NO_LINK ? '' : values.link_type;
		const args = {
			name: node.name,
			display_name: values.display_name,
			link_type,
			link_target: get_link_target(link_type, values),
			icon: values.icon || '',
			image: values.image || '',
			meta_title: values.meta_title || '',
			meta_description: values.meta_description || '',
			og_image: values.og_image || '',
			noindex: cint(values.noindex),
		};
		if (values.route_slug !== undefined) args.route_slug = values.route_slug;
		return args;
	}

	async function save_node(node, state, refresh) {
		const values = state.inspector.get_values();
		if (!values) return;

		try {
			state.menu = await get_menu(
				'update_node',
				get_node_arguments(node, values),
			);
			frappe.show_alert({ message: __('Saved'), indicator: 'green' });
		} catch (error) {}
		refresh();
	}

	function set_selected_node(name, state, refresh) {
		state.selected = name;
		refresh();
	}

	function toggle_branch(name, state, refresh) {
		if (!state.expanded.has(name)) {
			state.expanded.add(name);
			refresh();
			return;
		}
		state.expanded.delete(name);
		// Collapsing the branch that holds the selection would hide the inspector's subject, so the
		// selection climbs to the branch head instead of vanishing.
		if (get_ancestor_names(state.menu, state.selected)?.includes(name)) {
			state.selected = name;
		}
		refresh();
	}

	function expand_all_branches(state, refresh) {
		state.expanded = new Set(get_parent_names(state.menu));
		refresh();
	}

	function collapse_all_branches(state, refresh) {
		state.expanded = new Set();
		const [root_name] = get_ancestor_names(state.menu, state.selected) || [];
		if (root_name) state.selected = root_name;
		refresh();
	}

	function expand_hovered_branch(event, state) {
		const node_element = event.related?.closest('.menu-node');
		const children = node_element?.querySelector(':scope > .menu-children');
		if (!children || children.style.display !== 'none') return;
		children.style.display = '';
		state.expanded.add(node_element.dataset.name);
	}

	function add_inspector_actions(inspector_pane, node, state, refresh) {
		$(inspector_pane)
			.find('.inspector-save')
			.on('click', () => save_node(node, state, refresh));

		$(inspector_pane)
			.find('.inspector-visibility')
			.on('click', () => {
				set_menu(
					get_menu('set_visibility', {
						name: node.name,
						visible: node.visible ? 0 : 1,
					}),
					state,
					refresh,
				);
			});

		$(inspector_pane)
			.find('.inspector-delete')
			.on('click', () => open_delete_dialog(node, state, refresh));
	}

	function get_delete_message(preview) {
		const label = escape_html(preview.label);
		if (!preview.count) {
			return __("Delete '{0}'? This can't be undone.", [label]);
		}
		const sub_entries =
			preview.count === 1
				? __('1 sub-entry')
				: __('{0} sub-entries', [preview.count]);
		return __("Delete '{0}' and its {1}? This can't be undone.", [
			label,
			sub_entries,
		]);
	}

	async function open_delete_dialog(node, state, refresh) {
		let preview;
		try {
			preview = await get_menu_response('get_delete_preview', {
				name: node.name,
			});
		} catch (error) {
			return;
		}

		frappe.confirm(get_delete_message(preview), () => {
			set_menu(get_menu('delete_node', { name: node.name }), state, refresh);
		});
	}

	function format_delete_all_warning(count) {
		return `
		<p style="font-size:13px; color:var(--text-color); margin-bottom:4px;">
			${__(
				'This will permanently delete all {0} menu entries. Your Item Groups, brands and products are not affected.',
				[count],
			)}
		</p>
		<p style="font-size:12px; color:var(--text-muted);">${__(
			"This can't be undone.",
		)}</p>`;
	}

	async function open_delete_all_dialog(state, refresh) {
		let preview;
		try {
			preview = await get_menu_response('get_delete_all_preview');
		} catch (error) {
			return;
		}

		if (!preview.count) {
			frappe.show_alert({
				message: __('There are no menu entries to delete.'),
				indicator: 'orange',
			});
			return;
		}

		const dialog = new frappe.ui.Dialog({
			title: __('Delete all menu entries'),
			fields: [
				{
					fieldtype: 'HTML',
					options: format_delete_all_warning(preview.count),
				},
				{
					fieldname: 'confirmation',
					fieldtype: 'Data',
					label: __('Type {0} to confirm', [DELETE_ALL_CONFIRMATION]),
					reqd: 1,
				},
			],
			primary_action_label: __('Delete all entries'),
			primary_action: (values) => {
				if (values.confirmation.trim() !== DELETE_ALL_CONFIRMATION) return;
				dialog.hide();
				delete_all_nodes(state, refresh);
			},
		});

		dialog.get_primary_btn().addClass('btn-danger').prop('disabled', true);
		dialog.fields_dict.confirmation.$input.on('input', (event) => {
			dialog
				.get_primary_btn()
				.prop(
					'disabled',
					event.target.value.trim() !== DELETE_ALL_CONFIRMATION,
				);
		});
		dialog.show();
	}

	async function delete_all_nodes(state, refresh) {
		frappe.dom.freeze(__('Deleting menu entries…'));
		try {
			await set_menu(get_menu('delete_all_nodes'), state, refresh);
		} finally {
			frappe.dom.unfreeze();
		}
	}

	function format_preview_link(node) {
		return `
		<div style="font-size:13px; color:var(--text-color); padding:3px 0;">
			${escape_html(node.label)}
		</div>`;
	}

	function format_preview_column(heading, nodes) {
		const links = nodes.map(format_preview_link).join('');
		return `
		<div style="min-width:120px;">
			<div style="font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:0.6px;
				color:var(--text-color); margin-bottom:8px;">
				${escape_html(heading)}
			</div>
			${
				links ||
				`<div style="font-size:12px; color:var(--text-muted);">${__(
					'links to collection',
				)}</div>`
			}
		</div>`;
	}

	function format_preview_columns(root) {
		const columns = root.children.filter((child) => child.visible);
		if (!columns.length) {
			return `
			<div style="font-size:13px; color:var(--text-muted);">
				${__('No dropdown — this tab links directly to')} /${escape_html(
					root.route_slug,
				)}
			</div>`;
		}

		const has_third_level = columns.some((column) =>
			column.children.some((link) => link.visible),
		);
		if (!has_third_level) {
			return format_preview_column(__('Shop {0}', [root.label]), columns);
		}

		return columns
			.map((column) =>
				format_preview_column(
					column.label,
					column.children.filter((link) => link.visible),
				),
			)
			.join('');
	}

	function refresh_preview(preview_pane, state) {
		const visible_roots = state.menu.filter((root) => root.visible);
		if (state.open_tab >= visible_roots.length) state.open_tab = 0;
		const open_root = visible_roots[state.open_tab];

		const tabs = visible_roots
			.map((root, tab_index) => {
				const is_open = tab_index === state.open_tab;
				return `
				<span class="preview-tab" data-tab="${tab_index}"
					style="padding:10px 4px; margin-right:22px; font-size:13px; letter-spacing:0.3px; cursor:pointer;
						color:var(--text-color); font-weight:${is_open ? '600' : '400'};
						border-bottom:2px solid ${
							is_open ? 'var(--text-color)' : 'transparent'
						};">
					${escape_html(root.label.toUpperCase())}
				</span>`;
			})
			.join('');

		preview_pane.innerHTML = `
		<div style="border:1px solid var(--border-color); border-radius:var(--border-radius, 6px); overflow:hidden;">
			<div style="display:flex; align-items:center; padding:0 18px; background:var(--card-bg, var(--fg-color));
				border-bottom:1px solid var(--border-color); flex-wrap:wrap;">
				<span style="font-weight:700; font-size:15px; margin-right:28px; padding:10px 0;
					color:var(--text-color);">Lifestyle</span>
				${tabs}
			</div>
			<div style="display:flex; gap:32px; padding:20px 24px 24px; background:var(--card-bg, var(--fg-color));
				box-shadow:inset 0 6px 8px -8px rgba(0,0,0,0.15);">
				${open_root ? format_preview_columns(open_root) : ''}
			</div>
		</div>
		<div style="margin-top:10px; font-size:12px; color:var(--text-muted);">
			${__(
				'Click a tab above to preview its dropdown. Reordering and visibility update this preview live.',
			)}
		</div>`;
	}

	function toggle_preview(body) {
		const preview_pane = body.querySelector('.menu-manager-preview');
		const is_open = preview_pane.style.display === 'none';
		preview_pane.style.display = is_open ? '' : 'none';
		preview_pane.previousElementSibling.style.marginBottom = is_open
			? '10px'
			: '0';
		body.querySelector('.menu-manager-preview-toggle').textContent = is_open
			? __('Hide preview')
			: __('Show preview');
		localStorage.setItem(PREVIEW_OPEN_KEY, is_open ? 'yes' : 'no');
	}

	async function set_menu(menu_promise, state, refresh) {
		try {
			state.menu = await menu_promise;
		} catch (error) {}
		refresh();
	}

	function add_menu_click_handlers(
		body,
		tree_pane,
		preview_pane,
		add_child_button,
		state,
		refresh,
	) {
		$(tree_pane)
			.off('click.menu_manager')
			.on('click.menu_manager', (event) => {
				const row = event.target.closest('.menu-node-row');
				if (!row) return;
				if (event.target.closest('.menu-node-caret')) {
					toggle_branch(row.dataset.name, state, refresh);
					return;
				}
				if (row.dataset.name === state.selected) return;
				set_selected_node(row.dataset.name, state, refresh);
			});

		$(preview_pane)
			.off('click.menu_manager')
			.on('click.menu_manager', '.preview-tab', (event) => {
				state.open_tab = Number(event.currentTarget.dataset.tab);
				refresh();
			});

		$(body)
			.find('.menu-manager-preview-toggle')
			.on('click', () => toggle_preview(body));

		$(body)
			.find('.menu-manager-expand-all')
			.on('click', () => expand_all_branches(state, refresh));

		$(body)
			.find('.menu-manager-collapse-all')
			.on('click', () => collapse_all_branches(state, refresh));

		$(body)
			.find('.menu-manager-delete-all')
			.on('click', () => open_delete_all_dialog(state, refresh));

		$(body)
			.find('.menu-manager-import')
			.on('click', () => import_item_groups(state, refresh));

		$(body)
			.find('.menu-manager-add-root')
			.on('click', () =>
				open_add_dialog('', __('Add Section'), state, refresh),
			);

		$(add_child_button).on('click', () => {
			if (!state.selected) return;
			open_add_dialog(state.selected, __('Add Child'), state, refresh);
		});
	}

	function add_menu_sortable(tree_pane, state, refresh) {
		for (const container of tree_pane.querySelectorAll('.menu-children')) {
			new Sortable(container, {
				handle: '.drag-handle',
				animation: 150,
				group: 'menu-nodes',
				onMove: (event) => {
					expand_hovered_branch(event, state);
				},
				onEnd: (event) => {
					const parent = event.to.dataset.parent;
					if (event.from === event.to) {
						const ordered_names = Array.from(event.to.children).map(
							(child) => child.dataset.name,
						);
						set_menu(
							get_menu('reorder_nodes', { parent, ordered_names }),
							state,
							refresh,
						);
						return;
					}
					set_menu(
						get_menu('move_node', {
							name: event.item.dataset.name,
							to_parent: parent,
							target_index: event.newIndex,
						}),
						state,
						refresh,
					);
				},
			});
		}
	}

	async function import_item_groups(state, refresh) {
		frappe.dom.freeze(__('Importing categories…'));
		try {
			await set_menu(get_menu('import_from_item_group'), state, refresh);
		} finally {
			frappe.dom.unfreeze();
		}
	}

	function format_product_count(count) {
		return count === 1 ? __('1 product') : __('{0} products', [count]);
	}

	function format_publish_result(count, publish) {
		if (!count) {
			return publish
				? __('Nothing needed publishing.')
				: __('Nothing needed unpublishing.');
		}
		return publish
			? __('{0} published.', [format_product_count(count)])
			: __('{0} unpublished.', [format_product_count(count)]);
	}

	function get_products_state(node, state) {
		if (!state.products || state.products.node !== node.name) {
			state.products = {
				node: node.name,
				open: false,
				loading: false,
				counts: null,
				rows: [],
				selection_mode: SELECTION_PAGE,
				search: '',
				matching: 0,
				selected_names: new Set(),
				excluded_names: new Set(),
			};
		}
		return state.products;
	}

	function is_product_selected(products, name) {
		return products.selection_mode === SELECTION_SCOPE
			? !products.excluded_names.has(name)
			: products.selected_names.has(name);
	}

	function get_loaded_selectable_names(products) {
		return products.rows
			.filter((row) => !row.blocked_reason)
			.map((row) => row.name);
	}

	function get_selection_counts(products) {
		const scope_selectable = products.counts
			? products.counts.total - products.counts.incomplete
			: 0;
		const loaded_selectable = get_loaded_selectable_names(products).length;
		const selected =
			products.selection_mode === SELECTION_SCOPE
				? scope_selectable - products.excluded_names.size
				: products.selected_names.size;
		return { scope_selectable, loaded_selectable, selected };
	}

	function reset_selection(products) {
		products.selection_mode = SELECTION_PAGE;
		products.selected_names.clear();
		products.excluded_names.clear();
	}

	function format_products_summary(products) {
		if (!products.counts) {
			return `<span style="font-size:12px; color:var(--text-muted);">${__(
				'Publish or unpublish the products in this section and everything under it',
			)}</span>`;
		}
		const parts = [
			__('{0} ready', [products.counts.publishable]),
			__('{0} live', [products.counts.published]),
		];
		if (products.counts.incomplete) {
			parts.push(__('{0} blocked', [products.counts.incomplete]));
		}
		return `<span style="font-size:12px; color:var(--text-muted);">${escape_html(
			parts.join(' · '),
		)}</span>`;
	}

	function format_product_state(row) {
		if (row.blocked_reason) {
			return `<span style="font-size:11px; color:var(--text-muted);">${escape_html(
				row.blocked_reason,
			)}</span>`;
		}
		return `<span class="indicator-pill ${
			row.is_published ? 'green' : 'gray'
		}" style="font-size:11px; flex-shrink:0;">${
			row.is_published ? __('Live') : __('Not live')
		}</span>`;
	}

	function format_product_row(row, products) {
		const blocked = Boolean(row.blocked_reason);
		const checked = !blocked && is_product_selected(products, row.name);
		return `
		<label style="display:flex; align-items:center; gap:8px; padding:4px 2px; margin:0;
			cursor:${blocked ? 'not-allowed' : 'pointer'}; ${
				blocked ? 'opacity:0.55;' : ''
			}">
			<input type="checkbox" class="menu-product-tick" data-name="${escape_html(
				row.name,
			)}"
				${blocked ? 'disabled' : ''} ${checked ? 'checked' : ''}>
			<span style="flex:1; min-width:0; font-size:12px; color:var(--text-color);
				overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escape_html(
					row.display_name,
				)}</span>
			<span style="font-size:11px; color:var(--text-muted); max-width:35%;
				overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escape_html(
					row.item_group,
				)}</span>
			${format_product_state(row)}
		</label>`;
	}

	function format_products_search(products) {
		return `
		<input type="search" class="form-control input-xs menu-products-search"
			style="margin-top:8px; font-size:12px;"
			placeholder="${__('Search products by name or category')}"
			value="${escape_html(products.search)}">`;
	}

	function format_selection_count(products) {
		const { selected } = get_selection_counts(products);
		if (products.selection_mode !== SELECTION_SCOPE) {
			return __('{0} selected', [selected]);
		}
		if (!products.excluded_names.size) {
			return __('{0} selected — the whole section', [selected]);
		}
		return __('{0} selected — the whole section minus {1}', [
			selected,
			products.excluded_names.size,
		]);
	}

	function format_selection_banner(products) {
		const { selected, scope_selectable, loaded_selectable } =
			get_selection_counts(products);

		if (products.selection_mode === SELECTION_SCOPE) {
			const message = products.excluded_names.size
				? __('{0} of the {1} in this section are selected — {2} unticked.', [
						selected,
						scope_selectable,
						products.excluded_names.size,
				  ])
				: __('All {0} in this section are selected, including any not shown.', [
						scope_selectable,
				  ]);
			return `${escape_html(message)}
			<a href="#" class="menu-products-clear-selection">${__(
				'Clear selection',
			)}</a>`;
		}

		if (
			!loaded_selectable ||
			selected < loaded_selectable ||
			scope_selectable <= loaded_selectable
		) {
			return '';
		}
		return `${escape_html(
			__('All {0} shown are selected.', [loaded_selectable]),
		)}
		<a href="#" class="menu-products-select-scope">${__(
			'Select all {0} in this section',
			[scope_selectable],
		)}</a>`;
	}

	function get_publish_scope_message(products) {
		const { selected, scope_selectable } = get_selection_counts(products);
		let scope;
		if (products.selection_mode !== SELECTION_SCOPE) {
			scope = __('Publishing acts on the {0} ticked above, and nothing else.', [
				format_product_count(selected),
			]);
		} else if (products.excluded_names.size) {
			scope = __(
				'Publishing acts on the whole section except the {0} you unticked — {1}, including any not shown here.',
				[products.excluded_names.size, format_product_count(selected)],
			);
		} else {
			scope = __(
				'Publishing acts on the whole section — all {0}, including any not shown here.',
				[format_product_count(scope_selectable)],
			);
		}
		if (!products.search) return scope;
		return `${scope} ${__('The search box filters this list only.')}`;
	}

	function format_products_body(products) {
		if (products.loading && !products.rows.length) {
			return `<div class="text-muted" style="font-size:12px; padding:6px 0;">${__(
				'Loading products…',
			)}</div>`;
		}
		if (!products.counts || !products.counts.total) {
			return `<div class="text-muted" style="font-size:12px; padding:6px 0;">${__(
				'No products are linked to this entry or anything under it.',
			)}</div>`;
		}

		const remaining = products.matching - products.rows.length;
		return `
		${format_products_search(products)}
		<div style="display:flex; align-items:center; justify-content:space-between; gap:8px; margin:8px 0 4px;">
			<label style="display:flex; align-items:center; gap:6px; margin:0; min-width:0; cursor:pointer;"
				title="${__(
					'Tick to select the products loaded below, untick to select none',
				)}">
				<input type="checkbox" class="menu-products-select-all">
				<span style="font-size:12px; color:var(--text-color); white-space:nowrap;">${__(
					'Select all',
				)}</span>
				<span class="menu-products-selection" style="font-size:11px; color:var(--text-muted);
					overflow:hidden; text-overflow:ellipsis; white-space:nowrap;"></span>
			</label>
			<span style="font-size:11px; color:var(--text-muted); white-space:nowrap;">${escape_html(
				products.search
					? __('showing {0} of {1} matching', [
							products.rows.length,
							products.matching,
					  ])
					: __('showing {0} of {1}', [
							products.rows.length,
							products.counts.total,
					  ]),
			)}</span>
		</div>
		<div class="menu-products-banner" style="font-size:11px; color:var(--text-muted);
			line-height:1.6; margin-bottom:4px;"></div>
		<div style="border:1px solid var(--border-color); border-radius:var(--border-radius, 6px);
			padding:6px 8px;">
			${
				products.rows.length
					? products.rows
							.map((row) => format_product_row(row, products))
							.join('')
					: `<div class="text-muted" style="font-size:12px; padding:4px 2px;">${__(
							'No products match this search.',
					  )}</div>`
			}
		</div>
		${
			remaining > 0
				? `<button class="btn btn-xs btn-default menu-products-more" style="margin-top:8px;" ${
						products.loading ? 'disabled' : ''
				  }>${__('Load {0} more', [
						Math.min(remaining, PRODUCT_PAGE_LENGTH),
				  ])}</button>`
				: ''
		}
		<div style="margin-top:8px; font-size:11px; color:var(--text-muted); line-height:1.6;">
			${__(
				'This moves the products themselves on and off the live store — it is not the Menu entry control, which only hides the menu entry.',
			)}
		</div>
		<div class="menu-products-scope" style="margin-top:6px; font-size:11px;
			color:var(--text-muted); line-height:1.6;"></div>
		<div style="position:sticky; bottom:-12px; z-index:1; display:flex; gap:6px; margin-top:10px;
			padding:8px 0 12px; background:var(--card-bg, var(--fg-color));">
			<button class="btn btn-xs btn-primary menu-products-publish">${__(
				'Publish selected',
			)}</button>
			<button class="btn btn-xs btn-default menu-products-unpublish">${__(
				'Unpublish selected',
			)}</button>
		</div>`;
	}

	function refresh_products(inspector_pane, node, state, refresh) {
		const container = inspector_pane.querySelector('.menu-manager-products');
		if (!container) return;

		const products = get_products_state(node, state);
		const had_search_focus = document.activeElement?.classList.contains(
			'menu-products-search',
		);
		container.innerHTML = `
		<div style="display:flex; align-items:center; justify-content:space-between; gap:8px;">
			<span style="display:flex; align-items:baseline; gap:8px; min-width:0;">
				<span style="font-size:13px; color:var(--text-color);">${__('Products')}</span>
				${format_products_summary(products)}
			</span>
			<button class="btn btn-xs btn-default menu-products-toggle">${
				products.open ? __('Hide') : __('Choose…')
			}</button>
		</div>
		${products.open ? format_products_body(products) : ''}`;

		refresh_products_selection(container, products);
		add_products_actions(container, inspector_pane, node, state, refresh);

		const search_field = container.querySelector('.menu-products-search');
		if (had_search_focus && search_field) {
			search_field.focus();
			search_field.setSelectionRange(
				search_field.value.length,
				search_field.value.length,
			);
		}
	}

	function refresh_products_selection(container, products) {
		const { selected, scope_selectable, loaded_selectable } =
			get_selection_counts(products);

		const select_all = container.querySelector('.menu-products-select-all');
		if (!select_all) return;
		const box_total =
			products.selection_mode === SELECTION_SCOPE
				? scope_selectable
				: loaded_selectable;
		select_all.checked = Boolean(box_total) && selected === box_total;
		select_all.indeterminate = selected > 0 && selected < box_total;

		container.querySelector('.menu-products-selection').textContent =
			format_selection_count(products);
		container.querySelector('.menu-products-banner').innerHTML =
			format_selection_banner(products);
		container.querySelector('.menu-products-scope').textContent =
			get_publish_scope_message(products);
		for (const tick of container.querySelectorAll(
			'.menu-product-tick:not(:disabled)',
		)) {
			tick.checked = is_product_selected(products, tick.dataset.name);
		}

		container.querySelector('.menu-products-publish').disabled =
			!selected || !products.counts.publishable;
		container.querySelector('.menu-products-unpublish').disabled =
			!selected || !products.counts.published;
	}

	function add_products_actions(
		container,
		inspector_pane,
		node,
		state,
		refresh,
	) {
		const products = get_products_state(node, state);
		const refresh_panel = () =>
			refresh_products(inspector_pane, node, state, refresh);

		// The panel replaces its own innerHTML on every pass, so the delegated handlers below would
		// stack once per pass without this.
		$(container).off('.menu_products');

		$(container)
			.find('.menu-products-toggle')
			.on('click.menu_products', async () => {
				products.open = !products.open;
				refresh_panel();
				if (products.open && !products.counts) {
					await set_products_page(node, state, 0);
					refresh_panel();
				}
			});

		$(container)
			.find('.menu-products-search')
			.on(
				'input.menu_products',
				frappe.utils.debounce(async (event) => {
					const search = event.target.value.trim();
					if (search === products.search) return;
					products.search = search;
					if (products.selection_mode !== SELECTION_SCOPE) {
						products.selected_names.clear();
					}
					await set_products_page(node, state, 0);
					refresh_panel();
				}, PRODUCT_SEARCH_DELAY),
			);

		$(container)
			.find('.menu-products-more')
			.on('click.menu_products', async () => {
				await set_products_page(node, state, products.rows.length);
				refresh_panel();
			});

		$(container).on('change.menu_products', '.menu-product-tick', (event) => {
			const { name } = event.currentTarget.dataset;
			const list =
				products.selection_mode === SELECTION_SCOPE
					? products.excluded_names
					: products.selected_names;
			if (
				event.currentTarget.checked ===
				(products.selection_mode !== SELECTION_SCOPE)
			) {
				list.add(name);
			} else {
				list.delete(name);
			}
			refresh_products_selection(container, products);
		});

		$(container).on(
			'change.menu_products',
			'.menu-products-select-all',
			(event) => {
				const checked = event.currentTarget.checked;
				reset_selection(products);
				if (checked) {
					for (const name of get_loaded_selectable_names(products)) {
						products.selected_names.add(name);
					}
				}
				refresh_products_selection(container, products);
			},
		);

		$(container).on(
			'click.menu_products',
			'.menu-products-select-scope',
			(event) => {
				event.preventDefault();
				reset_selection(products);
				products.selection_mode = SELECTION_SCOPE;
				refresh_products_selection(container, products);
			},
		);

		$(container).on(
			'click.menu_products',
			'.menu-products-clear-selection',
			(event) => {
				event.preventDefault();
				reset_selection(products);
				refresh_products_selection(container, products);
			},
		);

		$(container)
			.find('.menu-products-publish')
			.on('click.menu_products', () => save_published(node, 1, state, refresh));

		$(container)
			.find('.menu-products-unpublish')
			.on('click.menu_products', () => save_published(node, 0, state, refresh));
	}

	async function set_products_page(node, state, start) {
		const products = get_products_state(node, state);
		products.loading = true;
		try {
			const page = await get_menu_response('get_cascade_products', {
				name: node.name,
				start,
				search: products.search,
			});
			products.counts = {
				total: page.total,
				publishable: page.publishable,
				incomplete: page.incomplete,
				published: page.published,
			};
			products.matching = page.matching;
			products.rows = start
				? [...products.rows, ...page.products]
				: page.products;
		} finally {
			products.loading = false;
		}
	}

	function get_publish_scope_arguments(products) {
		return products.selection_mode === SELECTION_SCOPE
			? { excluded_names: JSON.stringify([...products.excluded_names]) }
			: { included_names: JSON.stringify([...products.selected_names]) };
	}

	async function save_published(node, publish, state, refresh) {
		const products = get_products_state(node, state);
		if (!get_selection_counts(products).selected) return;

		frappe.dom.freeze(
			publish ? __('Publishing products…') : __('Unpublishing products…'),
		);
		try {
			const result = await get_menu_response('set_published', {
				name: node.name,
				publish,
				...get_publish_scope_arguments(products),
			});
			frappe.show_alert({
				message: format_publish_result(result.count, publish),
				indicator: result.count ? 'green' : 'orange',
			});
			state.menu = result.menu;
			reset_selection(products);
			await set_products_page(node, state, 0);
		} catch (error) {
			return;
		} finally {
			frappe.dom.unfreeze();
		}
		refresh();
	}

	function open_add_dialog(parent, title, state, refresh) {
		frappe.prompt(
			[
				{
					fieldname: 'display_name',
					fieldtype: 'Data',
					label: __('Display Name'),
					reqd: 1,
				},
			],
			(values) => {
				if (parent) state.expanded.add(parent);
				set_menu(
					get_menu('add_node', { parent, display_name: values.display_name }),
					state,
					refresh,
				);
			},
			title,
			__('Add'),
		);
	}
})();
