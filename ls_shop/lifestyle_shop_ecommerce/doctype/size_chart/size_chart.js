// Copyright (c) 2025, company@bwhstudios.com and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Size Chart", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on('Size Chart', {
	refresh(frm) {
		// Check XLSX file type
		if (
			frm.doc.size_chart &&
			!frm.doc.size_chart.toLowerCase().endsWith('.xlsx')
		) {
			frappe.throw(__('Only .xlsx files are allowed for Size Chart'));
			frm.set_value('size_chart', null);
		}

		// Render table preview if saved and JSON is present
		if (frm.doc.size_chart_json) {
			render_chart_preview(frm);
		} else {
			frm.fields_dict.chart_preview.$wrapper.empty();
		}
	},
	validate(frm) {
		if (
			frm.doc.size_chart &&
			!frm.doc.size_chart.toLowerCase().endsWith('.xlsx')
		) {
			frappe.throw(__('Only .xlsx files are allowed for Size Chart'));
			frm.set_value('size_chart', null);
		}
	},
});

function render_chart_preview(frm) {
	let data;
	try {
		data = JSON.parse(frm.doc.size_chart_json);
	} catch (e) {
		frm.fields_dict.chart_preview.$wrapper.html(
			"<div class='alert alert-danger p-2 mb-2'>Invalid JSON data</div>",
		);
		return;
	}

	if (!data.length) {
		frm.fields_dict.chart_preview.$wrapper.html(
			"<div class='alert alert-warning p-2 mb-2'>No data to display</div>",
		);
		return;
	}

	const headerCells = data[0]
		.map((cell) => `<th scope="col">${cell ?? ''}</th>`)
		.join('');

	const bodyRows = data
		.slice(1)
		.map((row) => {
			const cells = row.map((cell) => `<td>${cell ?? ''}</td>`).join('');
			return `<tr>${cells}</tr>`;
		})
		.join('');

	const html = `
		<div class="table-responsive">
			<table class="table table-bordered table-sm table-hover align-middle">
				<thead class="table-light">
					<tr>${headerCells}</tr>
				</thead>
				<tbody>${bodyRows}</tbody>
			</table>
		</div>`;

	frm.fields_dict.chart_preview.$wrapper.html(html);
}
