# Copyright (c) 2026, company@bwhstudios.com and contributors
# For license information, please see license.txt

import frappe
from frappe.contacts.doctype.address.address import get_address_display, get_default_address
from frappe.utils.data import cint, cstr, flt, getdate

from ls_shop.utils import get_address_lines

SETTINGS_DOCTYPE = "Lifestyle Settings"
BRANDING_DOCTYPE = "Website Settings"

# Payload keys are the pre-move names on purpose: the Vue tab and the sidebar bind to them.
BRANDING_FIELDS = {
	"brand_logo": "banner_image",
	"footer_logo": "footer_logo",
	"favicon": "favicon",
}

STORE_DETAIL_FIELDS = (
	"store_name",
	"brand_logo",
	"footer_logo",
	"favicon",
	"contact_email",
	"contact_phone",
	"working_hours",
	"company",
)

STORE_DETAIL_SETTINGS_FIELDS = tuple(
	fieldname for fieldname in STORE_DETAIL_FIELDS if fieldname not in BRANDING_FIELDS
)

SHIPPING_FIELDS = ("shipping_rule", "return_period")

PAYMENT_FIELDS = (
	"cod_enabled",
	"cod_charge",
	"cod_charge_applicable_below",
	"charge_account_head",
)

FOOTER_FIELDS = (
	"facebook_url",
	"twitter_url",
	"instagram_url",
	"snapchat_url",
	"tiktok_url",
	"newsletter_title",
	"newsletter_description",
	"copyright_text",
	"payment_methods_image",
	"vat_certificate_image",
)

# Fields the four curated tabs own, so the Advanced tab does not render a second copy.
CURATED_FIELDS = frozenset(STORE_DETAIL_FIELDS + SHIPPING_FIELDS + PAYMENT_FIELDS + FOOTER_FIELDS)

# Fieldtypes the generic renderer cannot express as one input. Color is skipped for a different
# reason: colour is moving to the theme, though format_theme_css() still reads these fields.
ADVANCED_SKIPPED_FIELDTYPES = frozenset(
	{"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Table", "Color"}
)

NUMERIC_FIELDTYPES = frozenset({"Currency", "Float", "Percent"})
INTEGER_FIELDTYPES = frozenset({"Int", "Check"})


def read_settings_fields(fieldnames):
	"""Read a fixed set of Lifestyle Settings fields for a settings tab."""
	frappe.has_permission(SETTINGS_DOCTYPE, ptype="read", throw=True)

	settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
	return {fieldname: settings.get(fieldname) for fieldname in fieldnames}


def coerce_field_value(fieldtype, value):
	"""Cast an incoming form value to what the docfield expects."""
	if value is None:
		return None
	if fieldtype in INTEGER_FIELDTYPES:
		return cint(value)
	if fieldtype in NUMERIC_FIELDTYPES:
		return flt(value)
	return cstr(value)


def write_settings_fields(allowed_fieldnames, values):
	"""Write only the whitelisted fields, casting each by its docfield type."""
	frappe.has_permission(SETTINGS_DOCTYPE, ptype="write", throw=True)

	meta = frappe.get_meta(SETTINGS_DOCTYPE)
	settings = frappe.get_doc(SETTINGS_DOCTYPE)
	for fieldname in allowed_fieldnames:
		if fieldname not in values:
			continue
		docfield = meta.get_field(fieldname)
		if not docfield:
			frappe.throw(frappe._("Unknown setting {0}").format(fieldname))
		settings.set(fieldname, coerce_field_value(docfield.fieldtype, values[fieldname]))

	settings.save()
	return {fieldname: settings.get(fieldname) for fieldname in allowed_fieldnames}


def read_branding_fields():
	"""The three brand assets, off Website Settings, under the payload's own key names."""
	frappe.has_permission(SETTINGS_DOCTYPE, ptype="read", throw=True)

	website_settings = frappe.get_cached_doc(BRANDING_DOCTYPE)
	return {key: website_settings.get(fieldname) for key, fieldname in BRANDING_FIELDS.items()}


def write_branding_fields(values):
	"""Write whichever brand assets the payload carries."""
	if not any(key in values for key in BRANDING_FIELDS):
		return read_branding_fields()

	frappe.has_permission(SETTINGS_DOCTYPE, ptype="write", throw=True)

	meta = frappe.get_meta(BRANDING_DOCTYPE)
	website_settings = frappe.get_doc(BRANDING_DOCTYPE)
	for key, fieldname in BRANDING_FIELDS.items():
		if key in values:
			fieldtype = meta.get_field(fieldname).fieldtype
			website_settings.set(fieldname, coerce_field_value(fieldtype, values[key]))

	# Website Settings is Website Manager's doctype; the store owner never holds that role, so the
	# brand assets are authorised by Lifestyle Settings above and Website Settings is only storage.
	website_settings.save(ignore_permissions=True)
	return {key: website_settings.get(fieldname) for key, fieldname in BRANDING_FIELDS.items()}


def validate_store_details(values):
	"""Guard store_name: ls_shop.seo falls back to the literal "Store", silently rebranding every <title>."""
	if "store_name" in values and not cstr(values["store_name"]).strip():
		frappe.throw(frappe._("Store Name is required"), frappe.MandatoryError)


@frappe.whitelist()
def get_store_settings():
	"""Branding and contact details - the fields a store owner touches most."""
	return read_settings_fields(STORE_DETAIL_SETTINGS_FIELDS) | read_branding_fields()


@frappe.whitelist(methods=["POST"])
def save_store_settings(**kwargs):
	validate_store_details(kwargs)
	return write_settings_fields(STORE_DETAIL_SETTINGS_FIELDS, kwargs) | write_branding_fields(kwargs)


@frappe.whitelist()
def get_shipping_settings():
	"""Shipping rule and returns window, plus the return reasons for reference."""
	settings = read_settings_fields(SHIPPING_FIELDS)

	# ponytail: return reasons are read-only here, edit them in Desk until the dashboard
	# grows a child-table editor
	settings["reason_for_return"] = frappe.get_all(
		"Return Reason",
		filters={"parent": SETTINGS_DOCTYPE, "parenttype": SETTINGS_DOCTYPE},
		fields=["name", "display_name", "description"],
		order_by="idx asc",
	)
	return settings


@frappe.whitelist(methods=["POST"])
def save_shipping_settings(**kwargs):
	return write_settings_fields(SHIPPING_FIELDS, kwargs)


@frappe.whitelist()
def get_payment_settings():
	"""Cash on delivery switches and the account the COD charge posts to."""
	return read_settings_fields(PAYMENT_FIELDS)


@frappe.whitelist(methods=["POST"])
def save_payment_settings(**kwargs):
	return write_settings_fields(PAYMENT_FIELDS, kwargs)


@frappe.whitelist()
def get_footer_settings():
	"""Social links, newsletter copy, and the footer trust badges."""
	return read_settings_fields(FOOTER_FIELDS)


@frappe.whitelist(methods=["POST"])
def save_footer_settings(**kwargs):
	return write_settings_fields(FOOTER_FIELDS, kwargs)


def get_advanced_docfields():
	"""Every editable docfield the four curated tabs do not already cover, in layout order."""
	docfields = []
	for docfield in frappe.get_meta(SETTINGS_DOCTYPE).fields:
		if docfield.fieldtype in ADVANCED_SKIPPED_FIELDTYPES:
			continue
		if docfield.fieldname in CURATED_FIELDS:
			continue
		if docfield.hidden or docfield.read_only:
			continue
		docfields.append(docfield)

	return docfields


@frappe.whitelist()
def get_advanced_settings():
	"""The long tail of setup fields, grouped by the section they sit under in Desk."""
	frappe.has_permission(SETTINGS_DOCTYPE, ptype="read", throw=True)

	settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
	advanced_fieldnames = {docfield.fieldname for docfield in get_advanced_docfields()}

	groups = []
	group_by_label = {}
	child_tables = []
	current_group_label = "General"

	for docfield in frappe.get_meta(SETTINGS_DOCTYPE).fields:
		if docfield.fieldtype in ("Tab Break", "Section Break"):
			if docfield.label:
				current_group_label = docfield.label
			continue

		if docfield.fieldtype == "Table":
			if docfield.fieldname not in CURATED_FIELDS:
				child_tables.append({"label": docfield.label, "options": docfield.options})
			continue

		if docfield.fieldname not in advanced_fieldnames:
			continue

		group = group_by_label.get(current_group_label)
		if group is None:
			group = {"label": current_group_label, "fields": []}
			group_by_label[current_group_label] = group
			groups.append(group)

		group["fields"].append(
			{
				"fieldname": docfield.fieldname,
				"label": docfield.label,
				"fieldtype": docfield.fieldtype,
				"options": docfield.options,
				"description": docfield.description,
				"value": settings.get(docfield.fieldname),
			}
		)

	return {"groups": groups, "child_tables": child_tables}


@frappe.whitelist(methods=["POST"])
def save_advanced_settings(**kwargs):
	advanced_fieldnames = [docfield.fieldname for docfield in get_advanced_docfields()]
	unknown = set(kwargs) - set(advanced_fieldnames)
	if unknown:
		frappe.throw(frappe._("Not an advanced setting: {0}").format(", ".join(sorted(unknown))))

	return write_settings_fields(advanced_fieldnames, kwargs)


def get_linked_doctypes():
	"""Doctypes reachable through a Lifestyle Settings Link field."""
	return {
		docfield.options
		for docfield in frappe.get_meta(SETTINGS_DOCTYPE).fields
		if docfield.fieldtype == "Link" and docfield.options
	}


@frappe.whitelist()
def get_link_options(doctype: str, search_text: str | None = None):
	"""Options for a Link control on the settings screen."""
	frappe.has_permission(SETTINGS_DOCTYPE, ptype="read", throw=True)

	if doctype not in get_linked_doctypes():
		frappe.throw(frappe._("{0} is not linked from {1}").format(doctype, SETTINGS_DOCTYPE))

	filters = {}
	if search_text:
		filters["name"] = ("like", f"%{cstr(search_text)}%")

	# ponytail: first 100 matches only - the picker searches server-side, so anything further
	# down is reachable by typing; paginate if a doctype outgrows even a searched list
	records = frappe.get_all(doctype, filters=filters, pluck="name", order_by="name asc", limit=100)
	return [{"label": name, "value": name} for name in records]


def read_company_address(company: str) -> str | None:
	"""The company's default address as plain text. get_address_display renders the address template,
	which is HTML, so it goes through the dashboard's own <br>-to-newline pass."""
	address = get_default_address("Company", company)
	return get_address_lines(get_address_display(address)) if address else None


def read_fiscal_year(company: str) -> str | None:
	"""The fiscal year today falls in. A site can be missing one entirely, hence raise_on_missing."""
	from erpnext.accounts.utils import get_fiscal_year

	fiscal_year = get_fiscal_year(getdate(), company=company, raise_on_missing=False)
	return fiscal_year[0] if fiscal_year else None


@frappe.whitelist()
def get_company_profile():
	"""The store's real accounting identity, read-only — edited in Desk, never here. None on a
	half-configured site so the settings dialog still opens."""
	frappe.has_permission(SETTINGS_DOCTYPE, ptype="read", throw=True)

	company = frappe.get_cached_value(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE, "company")
	if not company:
		return None

	details = frappe.get_cached_value(
		"Company", company, ["name", "abbr", "default_currency", "country", "tax_id"], as_dict=True
	)
	if not details:
		return None

	return {
		"name": details.name,
		"abbr": details.abbr,
		"currency": details.default_currency,
		"country": details.country,
		"tax_id": details.tax_id,
		"fiscal_year": read_fiscal_year(company),
		"address": read_company_address(company),
	}


@frappe.whitelist()
def get_locations():
	"""The warehouse the storefront sells out of. This shop is single-warehouse, so the list is one
	entry or none — it is a list only because the screen renders it as one."""
	frappe.has_permission(SETTINGS_DOCTYPE, ptype="read", throw=True)

	warehouse = frappe.get_cached_value(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE, "ecommerce_warehouse")
	if not warehouse:
		return []

	details = frappe.get_cached_value(
		"Warehouse", warehouse, ["name", "warehouse_name", "company", "disabled"], as_dict=True
	)
	if not details:
		return []

	return [
		{
			"name": details.name,
			"warehouse_name": details.warehouse_name,
			"company": details.company,
			"disabled": cint(details.disabled),
		}
	]


PROFILE_FIELDS = ("first_name", "last_name", "user_image")


@frappe.whitelist()
def get_profile():
	"""The signed-in user's own profile. Always self-scoped - this is not user administration."""
	user = frappe.get_cached_doc("User", frappe.session.user)
	return {
		"name": user.name,
		"email": user.email,
		"full_name": user.full_name,
		"first_name": user.first_name,
		"last_name": user.last_name,
		"user_image": user.user_image,
	}


@frappe.whitelist(methods=["POST"])
def save_profile(**kwargs):
	"""Edit your own profile only; changing anyone else's is User administration's job."""
	user = frappe.get_doc("User", frappe.session.user)
	for field in PROFILE_FIELDS:
		if field in kwargs:
			user.set(field, kwargs[field])
	user.save(ignore_permissions=True)

	return get_profile()
