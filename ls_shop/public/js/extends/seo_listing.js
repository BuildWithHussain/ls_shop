// Shopify-style "Search engine listing" editor: a live Google snippet preview plus character
// counters. One script drives every SEO-bearing doctype; Lifestyle Settings has several blocks.

const TITLE_MAX = 60;
const DESCRIPTION_MAX = 160;

// Store settings rarely change mid-edit, so resolve the lookup once and share the promise
// across every block/render on the page (avoids a round-trip per keystroke and per block).
let storeSettingsPromise = null;

async function getStoreSettings() {
	if (!storeSettingsPromise) {
		storeSettingsPromise = frappe.db.get_value(
			'Lifestyle Settings',
			'Lifestyle Settings',
			['store_name', 'seo_title_template', 'default_meta_description'],
		);
	}

	const response = await storeSettingsPromise;
	return response?.message ?? {};
}

// Mirror seo.py::apply_title_template so the preview matches what the storefront will render.
function applyTitleTemplate(title, settings) {
	const storeName = settings.store_name ?? '';
	if (!title) {
		return storeName;
	}

	const template = settings.seo_title_template || '{title} | {store}';
	return template.replaceAll('{title}', title).replaceAll('{store}', storeName);
}

function truncate(text, max) {
	if (text.length <= max) {
		return text;
	}

	return `${text.slice(0, max - 1)}…`;
}

const PREVIEW_BLOCKS = {
	'Style Attribute Variant': [
		{
			preview: 'seo_preview',
			title: 'meta_title',
			description: 'meta_description',
			handle: 'route',
			image: 'og_image',
			fallback_title: (frm, settings) =>
				`${frm.doc.display_name || ''} | ${settings.store_name || ''}`,
			path: (frm) => `/en/products/${frm.doc.route || ''}`,
		},
	],
	'Ecommerce Category': [
		{
			preview: 'seo_preview',
			title: 'meta_title',
			description: 'meta_description',
			handle: 'route_slug',
			image: 'og_image',
			fallback_title: (frm, settings) =>
				`${frm.doc.display_name || frm.doc.category_name || ''} | ${
					settings.store_name || ''
				}`,
			path: (frm) => `/en/products?category=${frm.doc.route_slug || ''}`,
		},
	],
	'Lifestyle Settings': [
		{
			preview: 'seo_homepage_preview',
			title: 'homepage_meta_title',
			description: 'homepage_meta_description',
			image: 'homepage_og_image',
			fallback_title: (frm, settings) => settings.store_name || '',
			path: () => '/en',
		},
		{
			preview: 'seo_product_list_preview',
			title: 'product_list_meta_title',
			description: 'product_list_meta_description',
			image: 'product_list_og_image',
			fallback_title: (frm, settings) =>
				`Products | ${settings.store_name || 'Store'}`,
			path: () => '/en/products',
		},
		{
			preview: 'seo_find_store_preview',
			title: 'find_store_meta_title',
			description: 'find_store_meta_description',
			image: 'find_store_og_image',
			fallback_title: (frm, settings) =>
				`Find a Store | ${settings.store_name || ''}`,
			path: () => '/en/find-store',
		},
		{
			preview: 'seo_contact_us_preview',
			title: 'contact_us_meta_title',
			description: 'contact_us_meta_description',
			image: 'contact_us_og_image',
			fallback_title: (frm, settings) =>
				`Contact Us | ${settings.store_name || ''}`,
			path: () => '/en/contact-us',
		},
	],
};

function renderPreviewCard(frm, block, settings) {
	const control = frm.fields_dict[block.preview];
	if (!control) {
		return;
	}

	const typedTitle = (frm.doc[block.title] || '').trim();
	const typedDescription = (frm.doc[block.description] || '').trim();

	const effectiveTitle =
		typedTitle || block.fallback_title(frm, settings) || '';
	const effectiveDescription =
		typedDescription || settings.default_meta_description || '';

	const baseUrl = frappe.urllib.get_base_url();
	const fullUrl = `${baseUrl}${block.path(frm)}`;
	const breadcrumb = frappe.utils
		.escape_html(fullUrl.replace(/^https?:\/\//, ''))
		.replaceAll('/', ' › ');

	const titleHtml = frappe.utils.escape_html(
		truncate(effectiveTitle, TITLE_MAX),
	);
	const descriptionHtml = effectiveDescription
		? `<div class="seo-preview-description">${frappe.utils.escape_html(
				truncate(effectiveDescription, DESCRIPTION_MAX),
		  )}</div>`
		: '<div class="seo-preview-description text-muted">Add a meta description to control how this page appears in search results…</div>';

	control.$wrapper.html(`
		<div class="seo-preview-card" style="border:1px solid var(--border-color);border-radius:var(--border-radius-md);padding:12px 16px;max-width:600px;">
			<div class="text-muted" style="font-size:11px;letter-spacing:0.05em;text-transform:uppercase;margin-bottom:8px;">Search engine listing preview</div>
			<div class="seo-preview-url" style="color:#202124;font-size:12px;">${breadcrumb}</div>
			<div class="seo-preview-title" style="color:#1a0dab;font-size:18px;line-height:1.3;margin:2px 0;">${titleHtml}</div>
			${descriptionHtml}
		</div>
	`);
}

function renderCounter(frm, fieldname, max) {
	const control = frm.fields_dict[fieldname];
	if (!control?.$wrapper) {
		return;
	}

	const length = (frm.doc[fieldname] || '').length;
	const over = length > max;
	const color = over ? 'var(--yellow-600, #b54708)' : 'var(--text-muted)';

	let counter = control.$wrapper.find('.seo-char-counter');
	if (!counter.length) {
		counter = $(
			'<div class="seo-char-counter" style="font-size:11px;text-align:right;margin-top:2px;"></div>',
		);
		control.$wrapper.append(counter);
	}

	counter.css('color', color).text(`${length} / ${max}`);
}

function renderBlock(frm, block, settings) {
	renderPreviewCard(frm, block, settings);
	renderCounter(frm, block.title, TITLE_MAX);
	renderCounter(frm, block.description, DESCRIPTION_MAX);
}

async function renderAllBlocks(frm) {
	const blocks = PREVIEW_BLOCKS[frm.doctype];
	if (!blocks) {
		return;
	}

	const settings = await getStoreSettings();
	for (const block of blocks) {
		renderBlock(frm, block, settings);
	}
}

for (const [doctype, blocks] of Object.entries(PREVIEW_BLOCKS)) {
	const handlers = {
		refresh(frm) {
			renderAllBlocks(frm);
		},
	};

	// Re-render the matching block whenever any of its driving fields changes.
	for (const block of blocks) {
		const drivingFields = [
			block.title,
			block.description,
			block.handle,
			block.image,
		].filter(Boolean);
		for (const fieldname of drivingFields) {
			handlers[fieldname] = (frm) => renderAllBlocks(frm);
		}
	}

	frappe.ui.form.on(doctype, handlers);
}
