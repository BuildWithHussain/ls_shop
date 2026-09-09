from frappe.utils import get_url

from commera.www.sitemap_segment import (
	SEGMENT_CONFIG,
	latest_lastmod,
	segment_page_count,
)


def get_context(context):
	# Index of paginated child sitemaps — the catalogue exceeds the 50k-URL cap of a single file.
	sitemaps = []
	for seg_type in SEGMENT_CONFIG:
		lastmod = latest_lastmod(seg_type)
		for page in range(1, segment_page_count(seg_type) + 1):
			sitemaps.append(
				{
					"loc": get_url(f"/sitemap-{seg_type}-{page}.xml"),
					"lastmod": lastmod,
				}
			)

	context.sitemaps = sitemaps
	context.no_cache = 1
