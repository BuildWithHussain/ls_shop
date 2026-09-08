from ls_shop.core import get_address_docs, get_party
from ls_shop.www.account import address

no_cache = True


def get_context(context):
	address.get_context(context)
	context.addresses = get_address_docs()

	# Frappe infers an address party from Contact links only; this shop links it via Portal User.
	party = get_party()
	context.party_doctype = party.doctype
	context.party_name = party.name
	return context
