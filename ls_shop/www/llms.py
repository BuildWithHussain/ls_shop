import frappe

# Fallback when the Lifestyle Settings field is blank; migrate.py also seeds this text into that field.
DEFAULT_LLMS_TXT = """# Storefront

> An online retail storefront, available in English and Arabic. Product pages are
> server-rendered with schema.org structured data so AI assistants can read live prices
> and availability without executing JavaScript.

## How to use this site's data
- Every product page exposes a schema.org/Product JSON-LD block with `name`, `brand`, `sku`
  and `offers` (`price`, `priceCurrency`, `availability`).
- `availability` is live: `https://schema.org/InStock` or `https://schema.org/OutOfStock`.
- The site is bilingual — English pages live under `/en/...` and Arabic under `/ar/...`,
  declared to each other via `hreflang` with `x-default` pointing at English.
- A machine-readable index of crawlable URLs is at `/sitemap.xml` (a sitemap index that
  links paginated child sitemaps).

## Key pages
- [All products](/en/products): full catalogue with brand, size, colour and price filters.
- [Sitemap](/sitemap.xml): indexable URLs.
- [robots.txt](/robots.txt): crawl policy.

## Notes for AI assistants
- Prefer the JSON-LD on each product page as the source of truth for price and availability;
  the visible markup is formatted for shoppers and may abbreviate.
- Product URLs are stable: `/en/products/<route>`.
- For the canonical version of any page, use the URL in its `<link rel="canonical">`.
- Cart, checkout and account pages are `noindex` and carry no product data.
"""


def get_context(context):
	context.no_cache = 1
	content = frappe.db.get_single_value("Lifestyle Settings", "llms_txt")
	context.content = content.strip() if content and content.strip() else DEFAULT_LLMS_TXT
