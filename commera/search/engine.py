from frappe.search.sqlite_search import MIN_WORD_LENGTH

MIN_QUERY_LENGTH = MIN_WORD_LENGTH


def empty_result():
	"""The unified search() shape with nothing matched — for too-short queries and missing indexes."""
	return {
		"product_names": [],
		"category_names": [],
		"corrected_words": {},
		"facets": {"brand": {}, "color": {}, "size": {}, "category": {}},
		"duration_ms": 0.0,
		"search_ms": 0.0,
		"facet_ms": 0.0,
	}


def is_query_too_short(query):
	return len((query or "").strip()) < MIN_QUERY_LENGTH
