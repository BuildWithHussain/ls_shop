from commera.www.account import wishlist


def get_context(context):
	wishlist.get_context(context)
	return context
