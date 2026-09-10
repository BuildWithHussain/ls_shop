no_cache = True

from commera.www.account.orders import index


def get_context(context):
	index.get_context(context)
	return context
