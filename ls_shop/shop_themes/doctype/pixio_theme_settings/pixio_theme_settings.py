# Copyright (c) 2026, hussain@buildwithhussain.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class PixioThemeSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from frappe.website.doctype.website_slideshow_item.website_slideshow_item import WebsiteSlideshowItem

		from ls_shop.lifestyle_shop_ecommerce.doctype.recommended_variant.recommended_variant import (
			RecommendedVariant,
		)
		from ls_shop.shop_themes.doctype.pixio_hero_slide.pixio_hero_slide import PixioHeroSlide
		from ls_shop.shop_themes.doctype.pixio_promo_banner.pixio_promo_banner import PixioPromoBanner

		best_picks: DF.Table[RecommendedVariant]
		categories_description: DF.SmallText | None
		categories_title: DF.Data | None
		collection_banners: DF.Table[PixioPromoBanner]
		deal_picks: DF.Table[RecommendedVariant]
		deals_link_label: DF.Data | None
		deals_title: DF.Data | None
		deals_url: DF.Data | None
		featured_picks: DF.Table[RecommendedVariant]
		featured_title: DF.Data | None
		hero_caption: DF.Data | None
		hero_caption_label: DF.Data | None
		hero_slides: DF.Table[PixioHeroSlide]
		offer_banners: DF.Table[PixioPromoBanner]
		offers_title: DF.Data | None
		products_title: DF.Data | None
		shop_by_category: DF.Table[WebsiteSlideshowItem]
	# end: auto-generated types

	_DOCTYPE_NAME = "Pixio Theme Settings"
