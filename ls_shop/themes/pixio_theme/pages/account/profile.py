from ls_shop.www.account import profile


def get_context(context):
	profile.get_context(context)
	return context
