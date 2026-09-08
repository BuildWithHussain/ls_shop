no_cache = True

from ls_shop.www.account.orders import index


def get_context(context):
	index.get_context(context)
	return context
