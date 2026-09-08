frappe.pages['ecommerce-analytics'].on_page_load = (wrapper) => {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('eCommerce Analytics'),
		single_column: true,
	});
	wrapper.ecommerce_analytics = new EcommerceAnalytics(page);
};

class EcommerceAnalytics {
	constructor(page) {
		this.page = page;
		this.charts = {};
		this.cache = {};
		this.loaded = {};
		this.currency = 'INR';
		this.range = '30';
		this.device = '';
		this.product_sort = 'revenue';
		this.kpis_animated = false;
		this.$root = $(frappe.render_template('ecommerce_analytics', {})).appendTo(
			page.body,
		);
		this.widget_workers = {
			live: ($body) => this.refresh_live($body),
			kpis: ($body) => this.refresh_kpis($body),
			sales: ($body) => this.refresh_sales($body),
			funnel: ($body) => this.refresh_funnel($body),
			top_products: ($body) => this.refresh_top_products($body),
			engagement: ($body) => this.refresh_engagement($body),
			traffic: ($body) => this.refresh_traffic($body),
			devices: ($body) => this.refresh_devices($body),
			landing: ($body) => this.refresh_landing($body),
			abandoned: ($body) => this.refresh_abandoned($body),
			heatmap: ($body) => this.refresh_heatmap($body),
			ga4: ($body) => this.refresh_ga4($body),
			meta: ($body) => this.refresh_meta($body),
			health: ($body) => this.refresh_health($body),
		};
		this.get_chart_library();
		this.add_events();
		this.add_theme_observer();
		this.refresh_all();
		this.live_timer = setInterval(() => {
			if (frappe.get_route_str() !== 'ecommerce-analytics') return;
			this.refresh_widget('live', { silent: true });
		}, 30000);
	}

	add_events() {
		this.$root
			.off('click.iv_range')
			.on('click.iv_range', '[data-range]', (event) => {
				const $button = $(event.currentTarget);
				this.range = $button.attr('data-range');
				$button.addClass('active').siblings().removeClass('active');
				this.refresh_all();
			});
		this.$root
			.off('click.iv_device')
			.on('click.iv_device', '[data-device]', (event) => {
				const $button = $(event.currentTarget);
				this.device = $button.attr('data-device');
				$button.addClass('active').siblings().removeClass('active');
				this.refresh_widget('funnel');
			});
		this.$root
			.off('click.iv_sort')
			.on('click.iv_sort', '[data-sort]', (event) => {
				const $button = $(event.currentTarget);
				this.product_sort = $button.attr('data-sort');
				$button.addClass('active').siblings().removeClass('active');
				this.refresh_widget('top_products');
			});
		this.$root
			.off('click.iv_refresh')
			.on('click.iv_refresh', '[data-role="refresh"]', (event) => {
				const $button = $(event.currentTarget);
				$button.addClass('spinning');
				setTimeout(() => $button.removeClass('spinning'), 1200);
				this.refresh_all();
			});
		this.$root
			.off('click.iv_retry')
			.on('click.iv_retry', '[data-widget-retry]', (event) => {
				event.preventDefault();
				this.refresh_widget($(event.currentTarget).attr('data-widget-retry'));
			});
		this.$root
			.off('click.iv_item')
			.on('click.iv_item', 'tr[data-item-code]', (event) => {
				const item_code = $(event.currentTarget).attr('data-item-code');
				if (item_code) this.show_item_dialog(item_code);
			});
	}

	add_theme_observer() {
		// Chart.js bakes resolved hexes onto canvas, so a theme flip needs a repaint; rAF lets the new theme CSS settle before get_palette() reads it
		this.theme_observer = new MutationObserver(() => {
			requestAnimationFrame(() => {
				this.refresh_sales_chart();
				this.refresh_device_chart();
				this.refresh_sparkline('ga4');
				this.refresh_sparkline('meta');
				this.refresh_item_chart();
			});
		});
		this.theme_observer.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ['data-theme', 'data-theme-mode'],
		});
	}

	get_chart_library() {
		if (!this.chart_library_promise) {
			this.chart_library_promise = new Promise((resolve, reject) => {
				if (typeof Chart !== 'undefined') {
					resolve();
					return;
				}
				if (!document.getElementById('chartjs-lib')) {
					const script = document.createElement('script');
					script.id = 'chartjs-lib';
					// version query busts stale cached copies of the vendored build
					script.src = '/assets/ls_shop/js/vendor/chart.umd.min.js?v=4.4.9';
					document.head.appendChild(script);
				}
				const started_at = Date.now();
				const poll = setInterval(() => {
					if (typeof Chart !== 'undefined') {
						clearInterval(poll);
						resolve();
					} else if (Date.now() - started_at > 10000) {
						clearInterval(poll);
						document.getElementById('chartjs-lib')?.remove();
						reject(new Error('Chart.js failed to load'));
					}
				}, 100);
			});
			this.chart_library_promise.catch(() => {
				this.chart_library_promise = null;
			});
		}
		return this.chart_library_promise;
	}

	get_range_dates() {
		const today = frappe.datetime.get_today();
		if (this.range === 'today') {
			return { from_date: today, to_date: today };
		}
		const days = Number(this.range);
		return {
			from_date: frappe.datetime.add_days(today, -(days - 1)),
			to_date: today,
		};
	}

	refresh_all() {
		this.external_summaries_promise = null;
		this.refresh_range_caption();
		for (const widget of Object.keys(this.widget_workers)) {
			this.refresh_widget(widget);
		}
	}

	format_range_caption() {
		const { from_date, to_date } = this.get_range_dates();
		if (this.range === 'today') {
			return `${frappe.datetime.str_to_user(to_date)} · vs yesterday`;
		}
		return `${frappe.datetime.str_to_user(
			from_date,
		)} – ${frappe.datetime.str_to_user(to_date)} · vs previous ${
			this.range
		} days`;
	}

	refresh_range_caption() {
		this.$root
			.find('[data-role="range-caption"]')
			.text(this.format_range_caption());
	}

	async refresh_widget(widget, { silent = false } = {}) {
		const $body = this.$root
			.find(`[data-widget='${widget}'] [data-body]`)
			.first();
		if (!$body.length) return;
		if (this.loaded[widget] && !silent) $body.addClass('iv-dim');
		try {
			await this.widget_workers[widget]($body);
			this.loaded[widget] = true;
			$body.removeClass('iv-dim');
			if (!silent) $body.addClass('iv-fade');
		} catch (error) {
			console.error(`[ecommerce-analytics] ${widget}:`, error);
			$body.removeClass('iv-dim').html(this.format_error(widget));
		}
	}

	async get_data(method, args) {
		const response = await frappe.call({
			method: `ls_shop.api.analytics_dashboard.${method}`,
			args: args || {},
		});
		if (response.message === undefined) {
			throw new Error(`${method} returned no data`);
		}
		return response.message;
	}

	get_external_summaries() {
		if (!this.external_summaries_promise) {
			this.external_summaries_promise = this.get_data('get_external_summaries');
			this.external_summaries_promise.catch(() => {
				this.external_summaries_promise = null;
			});
		}
		return this.external_summaries_promise;
	}

	// ── widgets ──────────────────────────────────────────────────────────

	async refresh_live($body) {
		const data = await this.get_data('get_live_view');
		const today = data.today || {};
		const chips = [
			{ label: __('Sessions today'), value: this.format_count(today.sessions) },
			{ label: __('Orders today'), value: this.format_count(today.orders) },
			{
				label: __('Sales today'),
				value: this.format_money(today.sales),
				title: this.format_money_full(today.sales),
			},
			{
				label: __('Active carts'),
				value: this.format_count(data.active_carts),
			},
			{
				label: __('Checking out'),
				value: this.format_count(data.checking_out),
			},
		];
		$body.html(`
			<div class='iv-live-row'>
				<div>
					<span class='iv-live-number'>${this.format_count(data.visitors_now)}</span>
					<div class='iv-micro'>${__('Visitors now')}</div>
				</div>
				${chips
					.map(
						(chip) => `
					<span class='iv-chip' ${
						chip.title ? `title='${frappe.utils.escape_html(chip.title)}'` : ''
					}>
						<strong>${chip.value}</strong><span>${chip.label}</span>
					</span>`,
					)
					.join('')}
			</div>
		`);
	}

	async refresh_kpis($body) {
		const data = await this.get_data('get_overview', this.get_range_dates());
		this.currency = data.currency || 'INR';
		const kpis = data.kpis || {};
		const tiles = [
			{ key: 'total_sales', label: __('Total sales'), kind: 'money' },
			{ key: 'orders', label: __('Orders'), kind: 'count' },
			{ key: 'sessions', label: __('Sessions'), kind: 'count' },
			{ key: 'conversion_rate', label: __('Conversion rate'), kind: 'rate' },
			{ key: 'aov', label: __('Avg order value'), kind: 'money' },
			{
				key: 'returning_customer_rate',
				label: __('Returning customers'),
				kind: 'rate',
			},
		];
		$body.html(
			tiles
				.map((tile) => this.format_kpi_tile(tile, kpis[tile.key] || {}))
				.join(''),
		);
		if (!this.kpis_animated) {
			this.kpis_animated = true;
			this.animate_kpi_values($body);
		}
	}

	format_kpi_tile(tile, kpi) {
		const value = Number(kpi.value) || 0;
		return `
			<div class='iv-kpi'>
				<div class='iv-micro'>${tile.label}</div>
				<div class='iv-kpi-value' data-kpi-value='${value}' data-kpi-kind='${
					tile.kind
				}'
					title='${frappe.utils.escape_html(
						this.format_kpi_value(value, tile.kind, true),
					)}'>
					${this.format_kpi_value(value, tile.kind)}
				</div>
				${this.format_delta_chip(value, kpi.previous, tile.kind)}
			</div>
		`;
	}

	format_kpi_value(value, kind, full = false) {
		if (kind === 'money')
			return full ? this.format_money_full(value) : this.format_money(value);
		if (kind === 'rate') return this.format_percent(value);
		return this.format_count(value);
	}

	format_delta_chip(current, previous, kind) {
		if (
			previous === null ||
			previous === undefined ||
			(kind !== 'rate' && !Number(previous))
		) {
			return `<span class='iv-delta flat' title='${__(
				'No previous-period data',
			)}'>— ${__('vs previous')}</span>`;
		}
		const previous_value = Number(previous) || 0;
		let difference;
		let text;
		if (kind === 'rate') {
			difference = current - previous_value;
			text = `${Math.abs(difference).toFixed(1)} pp`;
		} else {
			difference = ((current - previous_value) / previous_value) * 100;
			text = `${Math.abs(difference).toFixed(1)}%`;
		}
		const direction =
			difference > 0.05 ? 'up' : difference < -0.05 ? 'down' : 'flat';
		const arrow = direction === 'up' ? '▲' : direction === 'down' ? '▼' : '—';
		const previous_label = frappe.utils.escape_html(
			`${__('Previous period')}: ${this.format_kpi_value(
				previous_value,
				kind,
				true,
			)}`,
		);
		return `<span class='iv-delta ${direction}' title='${previous_label}'>${arrow} ${text}</span>`;
	}

	animate_kpi_values($body) {
		if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
		$body.find('[data-kpi-value]').each((_, element) => {
			const target = Number(element.getAttribute('data-kpi-value')) || 0;
			const kind = element.getAttribute('data-kpi-kind');
			const started_at = performance.now();
			const duration = 600;
			const tick = (now) => {
				const progress = Math.min((now - started_at) / duration, 1);
				const eased = 1 - (1 - progress) ** 3;
				element.textContent = this.format_kpi_value(target * eased, kind);
				if (progress < 1) requestAnimationFrame(tick);
			};
			requestAnimationFrame(tick);
		});
	}

	async refresh_sales($body) {
		await this.get_chart_library();
		const data = await this.get_data(
			'get_sales_timeseries',
			this.get_range_dates(),
		);
		this.cache.sales = data;
		$body.html("<div class='iv-chart-box'><canvas></canvas></div>");
		this.refresh_sales_chart();
	}

	refresh_sales_chart() {
		const data = this.cache.sales;
		const canvas = this.$root.find("[data-widget='sales'] canvas")[0];
		if (!data || !canvas || typeof Chart === 'undefined') return;
		if (this.charts.sales) this.charts.sales.destroy();
		const palette = this.get_palette();
		const context = canvas.getContext('2d');
		const gradient = context.createLinearGradient(0, 0, 0, 280);
		gradient.addColorStop(0, this.with_alpha(palette.cat1, 0.18));
		gradient.addColorStop(1, this.with_alpha(palette.cat1, 0));
		this.charts.sales = new Chart(canvas, {
			type: 'bar',
			data: {
				labels: (data.labels || []).map((label) =>
					this.format_short_date(label),
				),
				datasets: [
					{
						type: 'line',
						label: __('Sales'),
						data: data.sales || [],
						yAxisID: 'y',
						borderColor: palette.cat1,
						backgroundColor: gradient,
						fill: true,
						borderWidth: 2,
						cubicInterpolationMode: 'monotone',
						pointRadius: 0,
						pointHoverRadius: 4,
						pointHoverBackgroundColor: palette.cat1,
						pointHoverBorderColor: palette.surface,
						pointHoverBorderWidth: 2,
					},
					{
						type: 'bar',
						label: __('Orders'),
						data: data.orders || [],
						yAxisID: 'y1',
						backgroundColor: this.with_alpha(palette.cat2, 0.35),
						hoverBackgroundColor: this.with_alpha(palette.cat2, 0.55),
						maxBarThickness: 18,
						borderRadius: { topLeft: 4, topRight: 4 },
						borderSkipped: 'start',
					},
				],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				interaction: { mode: 'index', intersect: false },
				plugins: {
					legend: {
						position: 'top',
						align: 'end',
						labels: {
							usePointStyle: true,
							pointStyle: 'circle',
							boxWidth: 7,
							boxHeight: 7,
							color: palette.muted,
							font: { size: 11 },
						},
					},
					tooltip: {
						callbacks: {
							label: (item) =>
								item.dataset.yAxisID === 'y'
									? ` ${item.dataset.label}: ${this.format_money_full(
											item.parsed.y,
									  )}`
									: ` ${item.dataset.label}: ${this.format_count(
											item.parsed.y,
									  )}`,
						},
					},
				},
				scales: {
					x: {
						grid: { display: false },
						ticks: {
							color: palette.muted,
							font: { size: 11 },
							maxTicksLimit: 10,
							maxRotation: 0,
						},
					},
					y: {
						position: 'left',
						beginAtZero: true,
						grid: { color: palette.grid, drawTicks: false },
						border: { display: false },
						ticks: {
							color: palette.muted,
							font: { size: 11 },
							maxTicksLimit: 6,
							callback: (value) => this.format_money(value),
						},
					},
					// orders axis kept recessive (no grid, muted ticks) so the sales axis leads
					y1: {
						position: 'right',
						beginAtZero: true,
						grid: { display: false },
						border: { display: false },
						ticks: {
							color: palette.muted,
							font: { size: 10 },
							maxTicksLimit: 5,
							callback: (value) => this.format_compact(value),
						},
					},
				},
			},
		});
	}

	async refresh_funnel($body) {
		const args = { ...this.get_range_dates() };
		if (this.device) args.device = this.device;
		const data = await this.get_data('get_funnel', args);
		const stages = data.stages || [];
		if (!stages.length || !Number(stages[0].count)) {
			$body.html(
				this.format_empty(__('No sessions recorded in this period yet.')),
			);
			return;
		}
		const max_count = Math.max(
			...stages.map((stage) => Number(stage.count) || 0),
			1,
		);
		const session_count = Number(stages[0].count) || 1;
		const rows = stages.map((stage, index) => {
			const count = Number(stage.count) || 0;
			const width = Math.max((count / max_count) * 100, 6);
			const next_count =
				index < stages.length - 1
					? Number(stages[index + 1].count) || 0
					: count * 0.82;
			const next_width = Math.max((next_count / max_count) * 100, 5);
			const inset =
				width > 0
					? Math.max(
							((width - Math.min(next_width, width)) / 2 / width) * 100,
							0,
					  )
					: 0;
			const share = ((count / session_count) * 100).toFixed(1);
			const previous_count =
				index > 0 ? Number(stages[index - 1].count) || 0 : 0;
			const drop_percent = previous_count
				? Math.round(((previous_count - count) / previous_count) * 100)
				: 0;
			const drop_caption =
				index > 0 && drop_percent >= 1
					? `<div class='iv-funnel-drop'>−${drop_percent}% ${__(
							'vs previous step',
					  )}</div>`
					: '';
			const label_inside = width >= 26;
			const value_text = `${this.format_count(count)} · ${share}%`;
			const stage_name = frappe.utils.escape_html(
				stage.label || stage.key || '',
			);
			return `
				${drop_caption}
				<div class='iv-funnel-wrap'>
					<div class='iv-funnel-stage' data-step='${index + 1}'
						style='width: ${width}%; clip-path: polygon(0% 0%, 100% 0%, ${(
							100 - inset
						).toFixed(2)}% 100%, ${inset.toFixed(2)}% 100%);'
						title='${frappe.utils.escape_html(
							`${stage.label || ''}: ${value_text} ${__('of sessions')}`,
						)}'>
						${label_inside ? value_text : ''}
					</div>
				</div>
				<div class='iv-funnel-stage-caption'>
					<span class='stage-name'>${stage_name}</span>
					${
						label_inside
							? ''
							: `<span class='stage-value'>· ${value_text}</span>`
					}
				</div>
			`;
		});
		$body.html(`<div class='iv-funnel'>${rows.join('')}</div>`);
	}

	async refresh_top_products($body) {
		const data = await this.get_data('get_top_products', {
			...this.get_range_dates(),
			sort_by: this.product_sort,
			limit: 8,
		});
		const rows = Array.isArray(data) ? data : [];
		if (!rows.length) {
			$body.html(this.format_empty(__('No product sales in this period yet.')));
			return;
		}
		const max_metric = Math.max(
			...rows.map(
				(row) =>
					Number(this.product_sort === 'units' ? row.units : row.revenue) || 0,
			),
			1,
		);
		$body.html(`
			<div class='iv-scroll-x'>
				<table class='iv-table'>
					<thead><tr>
						<th>${__('Product')}</th>
						<th class='num'>${__('Units')}</th>
						<th class='num'>${__('Revenue')}</th>
						<th style='width: 90px;'>${__('Share')}</th>
					</tr></thead>
					<tbody>
						${rows
							.map((row, row_index) => {
								const metric =
									Number(
										this.product_sort === 'units' ? row.units : row.revenue,
									) || 0;
								return `
								<tr class='iv-row-click' data-item-code='${frappe.utils.escape_html(
									row.item_code || '',
								)}' title='${__('View item analytics')}'>
									<td class='iv-td-stretch'><div class='iv-cell-main'>
										${this.format_item_serial(row_index + 1)}
										<span class='iv-cell-name' title='${frappe.utils.escape_html(
											row.item_name || row.item_code || '',
										)}'>
											${frappe.utils.escape_html(
												row.item_name || row.item_code || '',
											)}
										</span>
									</div></td>
									<td class='num'>${this.format_count(row.units)}</td>
									<td class='num' title='${frappe.utils.escape_html(
										this.format_money_full(row.revenue),
									)}'>${this.format_money(row.revenue)}</td>
									<td><div class='iv-bar-track'><div class='iv-bar-fill' style='width: ${(
										(metric / max_metric) *
										100
									).toFixed(1)}%;'></div></div></td>
								</tr>`;
							})
							.join('')}
					</tbody>
				</table>
			</div>
		`);
	}

	format_item_serial(position) {
		return `<span class='iv-avatar show'>${position}</span>`;
	}

	async refresh_engagement($body) {
		const data = await this.get_data('get_product_engagement', {
			...this.get_range_dates(),
			limit: 8,
		});
		const rows = Array.isArray(data) ? data : [];
		if (!rows.length) {
			$body.html(
				this.format_empty(__('No product views tracked in this period yet.')),
			);
			return;
		}
		const max_rate = Math.max(
			...rows.map((row) => Number(row.purchase_to_view_rate) || 0),
			0.1,
		);
		$body.html(`
			<div class='iv-scroll-x'>
				<table class='iv-table' style='min-width: 460px;'>
					<thead><tr>
						<th>${__('Product')}</th>
						<th class='num'>${__('Views')}</th>
						<th class='num'>${__('Adds')}</th>
						<th class='num'>${__('Purchases')}</th>
						<th style='width: 120px;'>${__('View → purchase')}</th>
					</tr></thead>
					<tbody>
						${rows
							.map((row, row_index) => {
								const rate = Number(row.purchase_to_view_rate) || 0;
								const low_conversion =
									(Number(row.views) || 0) > 50 && rate < 1;
								return `
								<tr class='iv-row-click' data-item-code='${frappe.utils.escape_html(
									row.item_code || '',
								)}' title='${__('View item analytics')}'>
									<td class='iv-td-stretch'><div class='iv-cell-main'>
										${this.format_item_serial(row_index + 1)}
										<span class='iv-cell-name' title='${frappe.utils.escape_html(
											row.item_name || row.item_code || '',
										)}'>
											${frappe.utils.escape_html(
												row.item_name || row.item_code || '',
											)}
										</span>
										${
											low_conversion
												? `<span class='iv-pill amber'>${__('Low conv')}</span>`
												: ''
										}
									</div></td>
									<td class='num'>${this.format_count(row.views)}</td>
									<td class='num'>${this.format_count(row.adds)}</td>
									<td class='num'>${this.format_count(row.purchases)}</td>
									<td>
										<div style='display: flex; align-items: center; gap: 8px;'>
											<div class='iv-bar-track' style='flex: 1;'><div class='iv-bar-fill' style='width: ${Math.min(
												(rate / max_rate) * 100,
												100,
											).toFixed(1)}%;'></div></div>
											<span style='font-size: 11.5px; font-variant-numeric: tabular-nums;'>${rate.toFixed(
												1,
											)}%</span>
										</div>
									</td>
								</tr>`;
							})
							.join('')}
					</tbody>
				</table>
			</div>
		`);
	}

	async refresh_traffic($body) {
		const data = await this.get_data(
			'get_traffic_sources',
			this.get_range_dates(),
		);
		const rows = Array.isArray(data) ? data : [];
		if (!rows.length) {
			$body.html(this.format_empty(__('No traffic data in this period yet.')));
			return;
		}
		const max_sessions = Math.max(
			...rows.map((row) => Number(row.sessions) || 0),
			1,
		);
		$body.html(`
			<div class='iv-scroll-x'>
				<table class='iv-table' style='min-width: 460px;'>
					<thead><tr>
						<th>${__('Source')}</th>
						<th style='width: 110px;'>${__('Sessions')}</th>
						<th class='num'>${__('Orders')}</th>
						<th class='num'>${__('Revenue')}</th>
						<th class='num'>${__('Conv')}</th>
					</tr></thead>
					<tbody>
						${rows
							.map((row) => {
								const source = row.source || __('Direct');
								const label = row.medium ? `${source} / ${row.medium}` : source;
								return `
								<tr>
									<td class='iv-td-stretch'><span class='iv-cell-name' title='${frappe.utils.escape_html(
										label,
									)}'>${frappe.utils.escape_html(label)}</span></td>
									<td>
										<div style='display: flex; align-items: center; gap: 8px;'>
											<div class='iv-bar-track' style='flex: 1;'><div class='iv-bar-fill' style='width: ${(
												((Number(row.sessions) || 0) / max_sessions) *
												100
											).toFixed(1)}%;'></div></div>
											<span style='font-size: 11.5px; font-variant-numeric: tabular-nums;'>${this.format_count(
												row.sessions,
											)}</span>
										</div>
									</td>
									<td class='num'>${this.format_count(row.orders)}</td>
									<td class='num' title='${frappe.utils.escape_html(
										this.format_money_full(row.revenue),
									)}'>${this.format_money(row.revenue)}</td>
									<td class='num'>${this.format_percent(row.conversion_rate)}</td>
								</tr>`;
							})
							.join('')}
					</tbody>
				</table>
			</div>
		`);
	}

	async refresh_devices($body) {
		await this.get_chart_library();
		const data = await this.get_data(
			'get_device_split',
			this.get_range_dates(),
		);
		const rows = Array.isArray(data) ? data : [];
		if (!rows.length) {
			$body.html(this.format_empty(__('No device data in this period yet.')));
			this.cache.devices = null;
			return;
		}
		this.cache.devices = rows;
		const total_sessions = rows.reduce(
			(sum, row) => sum + (Number(row.sessions) || 0),
			0,
		);
		$body.html(`
			<div class='iv-donut-box'>
				<canvas></canvas>
				<div class='iv-donut-center'>
					<strong>${this.format_count(total_sessions)}</strong>
					<span class='iv-micro'>${__('Sessions')}</span>
				</div>
			</div>
			<div class='iv-legend'>
				${rows
					.map(
						(row) => `
					<div class='iv-legend-row'>
						<span class='swatch' style='background: ${this.get_device_color(
							row.device,
						)};'></span>
						<span class='grow'>${frappe.utils.escape_html(
							this.format_device_label(row.device),
						)}</span>
						<span class='muted'>${this.format_count(row.sessions)} ${__(
							'sessions',
						)}</span>
						<span class='muted'>· ${this.format_percent(
							row.conversion_rate,
						)} ${__('conv')}</span>
					</div>`,
					)
					.join('')}
			</div>
		`);
		this.refresh_device_chart();
	}

	refresh_device_chart() {
		const rows = this.cache.devices;
		const canvas = this.$root.find("[data-widget='devices'] canvas")[0];
		if (!rows || !canvas || typeof Chart === 'undefined') return;
		if (this.charts.devices) this.charts.devices.destroy();
		const palette = this.get_palette();
		this.charts.devices = new Chart(canvas, {
			type: 'doughnut',
			data: {
				labels: rows.map((row) => this.format_device_label(row.device)),
				datasets: [
					{
						data: rows.map((row) => Number(row.sessions) || 0),
						backgroundColor: rows.map((row) =>
							this.get_device_color(row.device),
						),
						borderColor: palette.surface,
						borderWidth: 2,
						hoverOffset: 6,
					},
				],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				cutout: '68%',
				plugins: {
					legend: { display: false },
					tooltip: {
						callbacks: {
							label: (item) =>
								` ${item.label}: ${this.format_count(item.parsed)} ${__(
									'sessions',
								)}`,
						},
					},
				},
			},
		});
	}

	get_device_color(device) {
		const palette = this.get_palette();
		const slot_by_device = {
			desktop: palette.cat1,
			mobile: palette.cat2,
			tablet: palette.cat3,
		};
		return slot_by_device[String(device || '').toLowerCase()] || palette.cat4;
	}

	format_device_label(device) {
		const label = String(device || __('Other'));
		return label.charAt(0).toUpperCase() + label.slice(1);
	}

	async refresh_landing($body) {
		const data = await this.get_data('get_landing_pages', {
			...this.get_range_dates(),
			limit: 8,
		});
		const rows = Array.isArray(data) ? data : [];
		if (!rows.length) {
			$body.html(
				this.format_empty(__('No landing-page data in this period yet.')),
			);
			return;
		}
		$body.html(`
			<table class='iv-table'>
				<thead><tr>
					<th>${__('Page')}</th>
					<th class='num'>${__('Sessions')}</th>
					<th class='num'>${__('Conv')}</th>
				</tr></thead>
				<tbody>
					${rows
						.map(
							(row) => `
						<tr>
							<td class='iv-td-stretch'><span class='iv-cell-name' title='${frappe.utils.escape_html(
								row.path || '',
							)}'>${frappe.utils.escape_html(row.path || '')}</span></td>
							<td class='num'>${this.format_count(row.sessions)}</td>
							<td class='num'>${this.format_percent(row.conversion_rate)}</td>
						</tr>`,
						)
						.join('')}
				</tbody>
			</table>
		`);
	}

	async refresh_abandoned($body) {
		const data = await this.get_data(
			'get_abandoned_carts',
			this.get_range_dates(),
		);
		const stats = data.stats || {};
		const carts = data.carts || [];
		const pill_class_by_status = {
			Abandoned: 'red',
			Recoverable: 'amber',
			Recovered: 'green',
		};
		const stat_chips = `
			<div class='iv-stat-chips'>
				<div class='iv-stat-chip'>
					<span class='iv-micro'>${__('Abandoned carts')}</span>
					<strong>${this.format_count(stats.count)}</strong>
				</div>
				<div class='iv-stat-chip'>
					<span class='iv-micro'>${__('Abandoned value')}</span>
					<strong title='${frappe.utils.escape_html(
						this.format_money_full(stats.value),
					)}'>${this.format_money(stats.value)}</strong>
				</div>
				<div class='iv-stat-chip'>
					<span class='iv-micro'>${__('Abandonment rate')}</span>
					<strong>${this.format_percent(stats.rate)}</strong>
				</div>
			</div>
		`;
		if (!carts.length) {
			$body.html(
				`${stat_chips}${this.format_empty(
					__('No abandoned carts in this period. Nice work!'),
				)}`,
			);
			return;
		}
		const visible_carts = carts.slice(0, 10);
		const count_note =
			carts.length > visible_carts.length
				? `<div class='iv-table-note'>${__('Showing {0} of {1} carts', [
						visible_carts.length,
						carts.length,
				  ])}</div>`
				: '';
		$body.html(`
			${stat_chips}
			<div class='iv-scroll-x'>
				<table class='iv-table' style='min-width: 560px;'>
					<thead><tr>
						<th>${__('Customer')}</th>
						<th class='num'>${__('Items')}</th>
						<th class='num'>${__('Value')}</th>
						<th>${__('Last activity')}</th>
						<th>${__('Status')}</th>
						<th></th>
					</tr></thead>
					<tbody>
						${visible_carts
							.map((cart) => {
								const who = cart.customer || cart.email || __('Guest');
								return `
								<tr>
									<td class='iv-td-stretch'><span class='iv-cell-name' title='${frappe.utils.escape_html(
										String(who),
									)}'>${frappe.utils.escape_html(String(who))}</span></td>
									<td class='num'>${this.format_count(cart.items_count)}</td>
									<td class='num' title='${frappe.utils.escape_html(
										this.format_money_full(cart.value),
									)}'>${this.format_money(cart.value)}</td>
									<td>${frappe.utils.escape_html(
										cart.last_activity
											? frappe.datetime.str_to_user(cart.last_activity)
											: '—',
									)}</td>
									<td><span class='iv-pill ${
										pill_class_by_status[cart.status] || 'muted'
									}'>${frappe.utils.escape_html(cart.status || '—')}</span></td>
									<td class='num'>${
										cart.quotation
											? `<a href='/app/quotation/${encodeURIComponent(
													cart.quotation,
											  )}'>${__('Open')} →</a>`
											: ''
									}</td>
								</tr>`;
							})
							.join('')}
					</tbody>
				</table>
			</div>
			${count_note}
		`);
	}

	async refresh_heatmap($body) {
		const data = await this.get_data(
			'get_sales_heatmap',
			this.get_range_dates(),
		);
		const matrix = data.matrix || [];
		const max_count = Number(data.max) || 0;
		const day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
		const hour_header = Array.from(
			{ length: 24 },
			(_, hour) =>
				`<div class='iv-heat-hour'>${
					hour % 3 === 0 ? this.format_hour(hour) : ''
				}</div>`,
		).join('');
		const grid_rows = day_labels
			.map((day, day_index) => {
				const cells = Array.from({ length: 24 }, (_, hour) => {
					const count = Number((matrix[day_index] || [])[hour]) || 0;
					const intensity =
						max_count > 0 && count > 0
							? Math.round(8 + (count / max_count) * 92)
							: 0;
					const fill = intensity
						? `style='background: color-mix(in srgb, var(--iv-primary) ${intensity}%, transparent);'`
						: '';
					return `<div class='iv-heat-cell' ${fill} title='${day} ${this.format_hour(
						hour,
					)} — ${this.format_count(count)} ${__('orders')}'></div>`;
				}).join('');
				return `<div class='iv-heat-day'>${day}</div>${cells}`;
			})
			.join('');
		$body.html(`
			<div class='iv-scroll-x'>
				<div class='iv-heatmap'>
					<div></div>${hour_header}
					${grid_rows}
				</div>
			</div>
			<div class='iv-heat-legend'>
				<span>${__('Fewer orders')}</span>
				<span class='iv-heat-scale'></span>
				<span>${__('More orders')}</span>
			</div>
		`);
	}

	async refresh_ga4($body) {
		await this.refresh_external_card($body, {
			key: 'ga4',
			daily_field: 'daily_sessions',
			daily_label: __('Daily sessions'),
			missing_message: __('GA4 is not configured.'),
		});
	}

	async refresh_meta($body) {
		await this.refresh_external_card($body, {
			key: 'meta',
			daily_field: 'daily_pageviews',
			daily_label: __('Daily pageviews'),
			missing_message: __('Meta Pixel is not configured.'),
		});
	}

	async refresh_external_card($body, card) {
		const summaries = await this.get_external_summaries();
		const provider = this.get_provider_state(summaries[card.key]);
		if (!provider.configured) {
			$body.html(this.format_not_configured(card.missing_message));
			return;
		}
		if (provider.error) {
			$body.html(this.format_warning(provider.error));
			return;
		}
		const summary = provider.summary || {};
		const spark_key = `spark_${card.key}`;
		this.cache[spark_key] = this.get_series_values(summary[card.daily_field]);
		$body.html(`
			${this.format_totals(summary.totals)}
			${
				this.cache[spark_key].length
					? `<div class='iv-spark-box'><canvas></canvas></div><div class='iv-micro' style='margin-top: 4px;'>${card.daily_label}</div>`
					: ''
			}
		`);
		this.refresh_sparkline(card.key);
	}

	get_provider_state(provider) {
		const state = provider || {};
		// old flat shape ({totals,...} or {error}) means a configured provider — tolerated during split deploys
		if (state.configured === undefined) {
			return {
				configured: Boolean(state.totals || state.error),
				summary: state,
				error: state.error || null,
			};
		}
		return {
			configured: Boolean(state.configured),
			summary: state.summary || null,
			error: state.error || null,
		};
	}

	format_not_configured(message) {
		return `
			<div class='iv-empty'>
				<svg width='28' height='28' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'><rect x='1' y='5' width='22' height='14' rx='7'/><circle cx='8' cy='12' r='3'/></svg>
				<span>${message}</span>
				<a href='/app/analytics-settings'>${__('Set up in Analytics Settings')}</a>
			</div>
		`;
	}

	format_totals(totals) {
		const entries = Object.entries(totals || {}).slice(0, 4);
		if (!entries.length) {
			return this.format_empty(__('No summary data yet.'));
		}
		return `
			<div class='iv-int-stats'>
				${entries
					.map(
						([key, value]) => `
					<div class='iv-int-stat'>
						<span>${frappe.utils.escape_html(String(key).replace(/_/g, ' '))}</span>
						<strong>${this.format_count(value)}</strong>
					</div>`,
					)
					.join('')}
			</div>
		`;
	}

	refresh_sparkline(widget) {
		const values = this.cache[`spark_${widget}`];
		const canvas = this.$root.find(`[data-widget='${widget}'] canvas`)[0];
		if (!values || !values.length || !canvas || typeof Chart === 'undefined')
			return;
		const chart_key = `spark_${widget}`;
		if (this.charts[chart_key]) this.charts[chart_key].destroy();
		const palette = this.get_palette();
		this.charts[chart_key] = new Chart(canvas, {
			type: 'line',
			data: {
				labels: values.map((_, index) => index + 1),
				datasets: [
					{
						data: values,
						borderColor: palette.cat1,
						backgroundColor: this.with_alpha(palette.cat1, 0.12),
						fill: true,
						borderWidth: 2,
						cubicInterpolationMode: 'monotone',
						pointRadius: 0,
					},
				],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: { legend: { display: false }, tooltip: { enabled: false } },
				scales: { x: { display: false }, y: { display: false } },
			},
		});
	}

	async refresh_health($body) {
		const data = await this.get_data('get_tracking_health');
		const first_party = data.first_party || {};
		const ga4 = data.ga4 || {};
		const meta = data.meta || {};
		const format_source_row = (label, source) => {
			if (!source.configured) {
				return `<tr><td>${label}</td><td class='num'>—</td><td><span class='iv-pill muted'>${__(
					'Off',
				)}</span></td></tr>`;
			}
			if (!source.ok) {
				return `<tr><td>${label}</td><td class='num'>—</td><td><span class='iv-pill red'>${__(
					'Error',
				)}</span></td></tr>`;
			}
			return `<tr><td>${label}</td><td class='num'>${this.format_count(
				source.purchases_30d,
			)}</td><td><span class='iv-pill green'>${__('OK')}</span></td></tr>`;
		};
		$body.html(`
			<div class='iv-chip' style='margin-bottom: 12px;'>
				<strong>${this.format_count(first_party.events_24h)}</strong>
				<span>${__('first-party events · 24h')}</span>
			</div>
			<table class='iv-table'>
				<thead><tr>
					<th>${__('Source')}</th>
					<th class='num'>${__('Purchases (30d)')}</th>
					<th>${__('Status')}</th>
				</tr></thead>
				<tbody>
					<tr>
						<td>${__('First-party')}</td>
						<td class='num'>${this.format_count(first_party.purchases_30d)}</td>
						<td><span class='iv-pill green'>${__('Active')}</span></td>
					</tr>
					${format_source_row(__('GA4'), ga4)}
					${format_source_row(__('Meta Pixel'), meta)}
				</tbody>
			</table>
			${ga4.error ? this.format_warning(ga4.error) : ''}
			${meta.error ? this.format_warning(meta.error) : ''}
		`);
	}

	// ── item drill-down dialog ───────────────────────────────────────────

	show_item_dialog(item_code) {
		if (this.item_dialog) this.item_dialog.hide();
		const dialog = new frappe.ui.Dialog({
			title: frappe.utils.escape_html(item_code),
			size: 'large',
		});
		this.item_dialog = dialog;
		dialog.$wrapper.on('hidden.bs.modal', () => {
			if (this.charts.item_detail) {
				this.charts.item_detail.destroy();
				this.charts.item_detail = null;
			}
			if (this.item_dialog === dialog) this.item_dialog = null;
			// each row click builds a fresh Dialog; drop the hidden modal so the DOM does not accumulate
			dialog.$wrapper.remove();
		});
		dialog.$wrapper
			.off('click.iv_item_retry')
			.on('click.iv_item_retry', '[data-item-retry]', (event) => {
				event.preventDefault();
				this.refresh_item_report(
					$(event.currentTarget).attr('data-item-retry'),
				);
			});
		dialog.show();
		this.refresh_item_report(item_code);
	}

	async refresh_item_report(item_code) {
		const dialog = this.item_dialog;
		if (!dialog) return;
		$(dialog.body).html(`
			<div class='iv-analytics iv-in-dialog'>
				<div class='iv-skel-chips'>
					<div class='iv-skel iv-skel-chip'></div>
					<div class='iv-skel iv-skel-chip'></div>
					<div class='iv-skel iv-skel-chip'></div>
				</div>
				<div class='iv-skel iv-skel-chart' style='height: 200px; margin-top: 12px;'></div>
			</div>
		`);
		try {
			const data = await this.get_data('get_item_analytics', {
				item_code,
				...this.get_range_dates(),
			});
			if (this.item_dialog !== dialog) return;
			this.cache.item_detail = data;
			dialog.set_title(
				frappe.utils.escape_html(data.item_name || data.item_code || item_code),
			);
			$(dialog.body).html(this.format_item_report(data));
			try {
				await this.get_chart_library();
				this.refresh_item_chart();
			} catch (error) {
				console.error('[ecommerce-analytics] item chart:', error);
				dialog.$wrapper
					.find('.iv-item-chart-box')
					.html(this.format_empty(__('Chart could not be loaded.')));
			}
		} catch (error) {
			console.error('[ecommerce-analytics] item report:', error);
			if (this.item_dialog !== dialog) return;
			$(dialog.body).html(`
				<div class='iv-analytics iv-in-dialog'>
					<div class='iv-error'>
						<svg width='28' height='28' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='10'/><path d='M12 8v4'/><path d='M12 16h.01'/></svg>
						<span>${__('Could not load this item report.')}</span>
						<a data-item-retry='${frappe.utils.escape_html(item_code)}'>${__(
							'Retry',
						)}</a>
					</div>
				</div>
			`);
		}
	}

	format_item_report(data) {
		const daily = data.daily || {};
		const devices = Array.isArray(data.devices) ? data.devices : [];
		const sources = Array.isArray(data.sources) ? data.sources : [];
		const recent_orders = Array.isArray(data.recent_orders)
			? data.recent_orders
			: [];
		const has_daily = Array.isArray(daily.labels) && daily.labels.length > 0;
		const device_rows = devices
			.map(
				(row) => `<tr>
					<td class='iv-td-stretch'>${frappe.utils.escape_html(
						this.format_device_label(row.device),
					)}</td>
					<td class='num'>${this.format_count(row.views)}</td>
				</tr>`,
			)
			.join('');
		const source_rows = sources
			.map((row) => {
				const source = row.source || __('Direct');
				const label = row.medium ? `${source} / ${row.medium}` : source;
				return `<tr>
					<td class='iv-td-stretch'><span class='iv-cell-name' title='${frappe.utils.escape_html(
						label,
					)}'>${frappe.utils.escape_html(label)}</span></td>
					<td class='num'>${this.format_count(row.views)}</td>
					<td class='num'>${this.format_count(row.adds)}</td>
				</tr>`;
			})
			.join('');
		const order_rows = recent_orders
			.map(
				(row) => `<tr>
					<td class='iv-td-stretch'><a href='/app/sales-order/${encodeURIComponent(
						row.order || '',
					)}'>${frappe.utils.escape_html(row.order || '')}</a></td>
					<td>${frappe.utils.escape_html(
						row.date ? frappe.datetime.str_to_user(row.date) : '—',
					)}</td>
					<td class='num'>${this.format_count(row.qty)}</td>
					<td class='num' title='${frappe.utils.escape_html(
						this.format_money_full(row.amount),
					)}'>${this.format_money(row.amount)}</td>
				</tr>`,
			)
			.join('');
		return `
			<div class='iv-analytics iv-in-dialog'>
				<div class='iv-item-caption'>${frappe.utils.escape_html(
					this.format_range_caption(),
				)}</div>
				${this.format_item_totals(data.totals || {})}
				<div class='iv-chart-box iv-item-chart-box' style='height: 260px;'>
					${
						has_daily
							? "<canvas class='iv-item-chart'></canvas>"
							: this.format_empty(__('No daily activity in this period.'))
					}
				</div>
				<div class='iv-grid-2' style='margin-top: 14px;'>
					<div>
						<div class='iv-micro' style='margin-bottom: 8px;'>${__('Devices')}</div>
						${
							device_rows
								? `<table class='iv-table'><thead><tr><th>${__(
										'Device',
								  )}</th><th class='num'>${__(
										'Views',
								  )}</th></tr></thead><tbody>${device_rows}</tbody></table>`
								: this.format_empty(__('No device data.'))
						}
					</div>
					<div>
						<div class='iv-micro' style='margin-bottom: 8px;'>${__(
							'Top sources',
						)}</div>
						${
							source_rows
								? `<table class='iv-table'><thead><tr><th>${__(
										'Source',
								  )}</th><th class='num'>${__(
										'Views',
								  )}</th><th class='num'>${__(
										'Adds',
								  )}</th></tr></thead><tbody>${source_rows}</tbody></table>`
								: this.format_empty(__('No source data.'))
						}
					</div>
				</div>
				<div style='margin-top: 14px;'>
					<div class='iv-micro' style='margin-bottom: 8px;'>${__(
						'Recent orders',
					)}</div>
					${
						order_rows
							? `<div class='iv-scroll-x'><table class='iv-table'><thead><tr><th>${__(
									'Order',
							  )}</th><th>${__('Date')}</th><th class='num'>${__(
									'Qty',
							  )}</th><th class='num'>${__(
									'Amount',
							  )}</th></tr></thead><tbody>${order_rows}</tbody></table></div>`
							: this.format_empty(__('No orders in this period.'))
					}
				</div>
			</div>
		`;
	}

	format_item_totals(totals) {
		const rate = Number(totals.purchase_to_view_rate) || 0;
		const store_avg = totals.store_avg_purchase_to_view_rate;
		let avg_caption = '';
		if (store_avg !== null && store_avg !== undefined) {
			const above = rate >= Number(store_avg);
			avg_caption = `<span class='iv-item-avg ${above ? 'up' : 'down'}'>${
				above ? '▲' : '▼'
			} ${__('store avg')} ${this.format_percent(store_avg)}</span>`;
		}
		const chips = [
			{ label: __('Views'), value: this.format_count(totals.views) },
			{ label: __('Adds'), value: this.format_count(totals.adds) },
			{ label: __('Checkouts'), value: this.format_count(totals.checkouts) },
			{ label: __('Units sold'), value: this.format_count(totals.units_sold) },
			{
				label: __('Revenue'),
				value: this.format_money(totals.revenue),
				title: this.format_money_full(totals.revenue),
			},
			{
				label: __('View → purchase'),
				value: this.format_percent(rate),
				caption: avg_caption,
			},
		];
		return `
			<div class='iv-stat-chips'>
				${chips
					.map(
						(chip) => `
					<div class='iv-stat-chip'>
						<span class='iv-micro'>${chip.label}</span>
						<strong ${
							chip.title
								? `title='${frappe.utils.escape_html(chip.title)}'`
								: ''
						}>${chip.value}</strong>
						${chip.caption || ''}
					</div>`,
					)
					.join('')}
			</div>
		`;
	}

	refresh_item_chart() {
		const data = this.cache.item_detail;
		const canvas = this.item_dialog
			? this.item_dialog.$wrapper.find('canvas.iv-item-chart')[0]
			: null;
		if (!data || !canvas || typeof Chart === 'undefined') return;
		if (this.charts.item_detail) this.charts.item_detail.destroy();
		const daily = data.daily || {};
		const palette = this.get_palette();
		const line_defaults = {
			type: 'line',
			borderWidth: 2,
			cubicInterpolationMode: 'monotone',
			pointRadius: 0,
			pointHoverRadius: 4,
			pointHoverBorderColor: palette.surface,
			pointHoverBorderWidth: 2,
		};
		this.charts.item_detail = new Chart(canvas, {
			type: 'bar',
			data: {
				labels: (daily.labels || []).map((label) =>
					this.format_short_date(label),
				),
				datasets: [
					{
						...line_defaults,
						label: __('Views'),
						data: daily.views || [],
						borderColor: palette.cat1,
						pointHoverBackgroundColor: palette.cat1,
					},
					{
						...line_defaults,
						label: __('Adds'),
						data: daily.adds || [],
						borderColor: palette.cat2,
						pointHoverBackgroundColor: palette.cat2,
					},
					{
						type: 'bar',
						label: __('Units sold'),
						data: daily.units || [],
						backgroundColor: this.with_alpha(palette.cat3, 0.5),
						hoverBackgroundColor: this.with_alpha(palette.cat3, 0.7),
						maxBarThickness: 14,
						borderRadius: { topLeft: 4, topRight: 4 },
						borderSkipped: 'start',
					},
				],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				interaction: { mode: 'index', intersect: false },
				plugins: {
					legend: {
						position: 'top',
						align: 'end',
						labels: {
							usePointStyle: true,
							pointStyle: 'circle',
							boxWidth: 7,
							boxHeight: 7,
							color: palette.muted,
							font: { size: 11 },
						},
					},
				},
				scales: {
					x: {
						grid: { display: false },
						ticks: {
							color: palette.muted,
							font: { size: 11 },
							maxTicksLimit: 10,
							maxRotation: 0,
						},
					},
					y: {
						beginAtZero: true,
						grid: { color: palette.grid, drawTicks: false },
						border: { display: false },
						ticks: {
							color: palette.muted,
							font: { size: 11 },
							maxTicksLimit: 6,
							callback: (value) => this.format_compact(value),
						},
					},
				},
			},
		});
	}

	// ── formatting helpers ───────────────────────────────────────────────

	format_money(value) {
		const amount = Number(value) || 0;
		if (this.currency !== 'INR') {
			return this.format_currency_fallback(amount, 0);
		}
		const magnitude = Math.abs(amount);
		const sign = amount < 0 ? '−' : '';
		if (magnitude >= 1e7)
			return `${sign}₹${this.strip_trailing_zeros(
				(magnitude / 1e7).toFixed(2),
			)} Cr`;
		if (magnitude >= 1e5)
			return `${sign}₹${this.strip_trailing_zeros(
				(magnitude / 1e5).toFixed(1),
			)} L`;
		return new Intl.NumberFormat('en-IN', {
			style: 'currency',
			currency: 'INR',
			maximumFractionDigits: 0,
		}).format(amount);
	}

	format_money_full(value) {
		const amount = Number(value) || 0;
		if (this.currency !== 'INR') {
			return this.format_currency_fallback(amount, 2);
		}
		return new Intl.NumberFormat('en-IN', {
			style: 'currency',
			currency: 'INR',
			maximumFractionDigits: 2,
		}).format(amount);
	}

	format_currency_fallback(amount, fraction_digits) {
		try {
			return new Intl.NumberFormat('en-IN', {
				style: 'currency',
				currency: this.currency,
				maximumFractionDigits: fraction_digits,
			}).format(amount);
		} catch {
			return `${this.currency} ${amount.toLocaleString('en-IN')}`;
		}
	}

	strip_trailing_zeros(text) {
		return text.replace(/\.?0+$/, '');
	}

	format_count(value) {
		return Math.round(Number(value) || 0).toLocaleString('en-IN');
	}

	format_compact(value) {
		const amount = Number(value) || 0;
		const magnitude = Math.abs(amount);
		if (magnitude >= 1e7)
			return `${this.strip_trailing_zeros((amount / 1e7).toFixed(1))} Cr`;
		if (magnitude >= 1e5)
			return `${this.strip_trailing_zeros((amount / 1e5).toFixed(1))} L`;
		if (magnitude >= 1e3)
			return `${this.strip_trailing_zeros((amount / 1e3).toFixed(1))}K`;
		return this.format_count(amount);
	}

	format_percent(value, digits = 1) {
		return `${(Number(value) || 0).toFixed(digits)}%`;
	}

	format_short_date(label) {
		if (!/^\d{4}-\d{2}-\d{2}$/.test(String(label))) return String(label);
		return new Date(`${label}T00:00:00`).toLocaleDateString('en-IN', {
			day: 'numeric',
			month: 'short',
		});
	}

	format_hour(hour) {
		if (hour === 0) return '12 AM';
		if (hour === 12) return '12 PM';
		return hour < 12 ? `${hour} AM` : `${hour - 12} PM`;
	}

	format_empty(message) {
		return `
			<div class='iv-empty'>
				<svg width='28' height='28' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'><path d='M21 21H4a1 1 0 0 1-1-1V3'/><path d='M7 14l4-4 3 3 5-6'/></svg>
				<span>${message}</span>
			</div>
		`;
	}

	format_error(widget) {
		return `
			<div class='iv-error'>
				<svg width='28' height='28' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='10'/><path d='M12 8v4'/><path d='M12 16h.01'/></svg>
				<span>${__("Couldn't load this card.")}</span>
				<a data-widget-retry='${widget}'>${__('Retry')}</a>
			</div>
		`;
	}

	format_warning(message) {
		return `
			<div class='iv-warnrow'>
				<svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z'/><path d='M12 9v4'/><path d='M12 17h.01'/></svg>
				<span>${frappe.utils.escape_html(String(message))}</span>
			</div>
		`;
	}

	get_series_values(rows) {
		if (!Array.isArray(rows)) return [];
		return rows.map((row) => {
			if (typeof row === 'number') return row;
			if (row && typeof row === 'object') {
				const numeric = Object.values(row).find(
					(value) => typeof value === 'number',
				);
				return numeric || 0;
			}
			return Number(row) || 0;
		});
	}

	get_palette() {
		const styles = getComputedStyle(this.$root[0]);
		const read = (name, fallback) =>
			(styles.getPropertyValue(name) || fallback).trim();
		return {
			cat1: read('--iv-cat-1', '#4f46e5'),
			cat2: read('--iv-cat-2', '#0891b2'),
			cat3: read('--iv-cat-3', '#d97706'),
			cat4: read('--iv-cat-4', '#db2777'),
			grid: read('--iv-border', '#ededed'),
			muted: read('--text-muted', '#74808b'),
			surface: read('--card-bg', '#ffffff'),
		};
	}

	with_alpha(hex_color, alpha) {
		const hex = hex_color.replace('#', '');
		const red = Number.parseInt(hex.substring(0, 2), 16);
		const green = Number.parseInt(hex.substring(2, 4), 16);
		const blue = Number.parseInt(hex.substring(4, 6), 16);
		return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
	}
}
