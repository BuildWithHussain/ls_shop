"""Request-scoped cache for the storefront search engine, shared across a single render's read paths."""

import frappe

from commera.search.sqlite_product_search import SqliteProductSearch


def get_search_engine():
	engine = getattr(frappe.local, "commera_search_engine", None)
	if engine is None:
		engine = SqliteProductSearch()
		frappe.local.commera_search_engine = engine
	return engine


def clear_search_engine():
	"""Drop the request-scoped engine; only tests need it because frappe.local persists across tests."""
	frappe.local.commera_search_engine = None
