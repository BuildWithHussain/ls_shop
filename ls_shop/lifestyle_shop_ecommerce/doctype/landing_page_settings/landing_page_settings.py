# Copyright (c) 2025, company@bwhstudios.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class LandingPageSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from frappe.website.doctype.website_slideshow_item.website_slideshow_item import (
			WebsiteSlideshowItem,
		)

		from ls_shop.lifestyle_shop_ecommerce.doctype.landing_page_hero_banner.landing_page_hero_banner import (
			LandingPageHeroBanner,
		)
		from ls_shop.lifestyle_shop_ecommerce.doctype.recommended_variant.recommended_variant import (
			RecommendedVariant,
		)

		banner_1: DF.AttachImage | None
		banner_1_ar: DF.AttachImage | None
		banner_2: DF.AttachImage | None
		banner_2_ar: DF.AttachImage | None
		banner_3: DF.AttachImage | None
		banner_3_ar: DF.AttachImage | None
		banner_4: DF.AttachImage | None
		banner_4_ar: DF.AttachImage | None
		banner_5: DF.AttachImage | None
		banner_5_ar: DF.AttachImage | None
		banner_url_1: DF.Data | None
		banner_url_1_ar: DF.Data | None
		banner_url_2: DF.Data | None
		banner_url_2_ar: DF.Data | None
		banner_url_3: DF.Data | None
		banner_url_3_ar: DF.Data | None
		banner_url_4: DF.Data | None
		banner_url_4_ar: DF.Data | None
		banner_url_5: DF.Data | None
		banner_url_5_ar: DF.Data | None
		best_picks: DF.Table[RecommendedVariant]
		browse_by_brands: DF.Table[WebsiteSlideshowItem]
		browse_by_brands_ar: DF.Table[WebsiteSlideshowItem]
		gif_1: DF.Attach | None
		gif_1_ar: DF.Attach | None
		gif_2: DF.Attach | None
		gif_2_ar: DF.Attach | None
		gif_3: DF.Attach | None
		gif_3_ar: DF.Attach | None
		gif_4: DF.Attach | None
		gif_4_ar: DF.Attach | None
		gif_url_1: DF.Data | None
		gif_url_1_ar: DF.Data | None
		gif_url_2: DF.Data | None
		gif_url_2_ar: DF.Data | None
		gif_url_3: DF.Data | None
		gif_url_3_ar: DF.Data | None
		gif_url_4: DF.Data | None
		gif_url_4_ar: DF.Data | None
		hero_banner: DF.Table[LandingPageHeroBanner]
		hero_banner_ar: DF.Table[LandingPageHeroBanner]
		new_arrivals: DF.Table[RecommendedVariant]
		other_products: DF.Table[RecommendedVariant]
	# end: auto-generated types
	pass
