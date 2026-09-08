from ls_shop.www.cart import checkout


def get_context(context):
	checkout.get_context(context)
	return context
