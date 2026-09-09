from commera.shop_themes.doctype.shop_theme_settings.shop_theme_settings import seed_default_routes


def execute():
	"""Give existing stores the themed /<lang>/page/<route> entry."""
	seed_default_routes()
