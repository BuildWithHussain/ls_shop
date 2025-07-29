import frappe


def after_install():
	create_payment_modes()
	try:
		create_ecommerce_group()
	except Exception as _:
		frappe.errprint("Error creating Ecommerce groups")


def create_payment_modes():
	modes = {"Telr"}

	for mode in modes:
		frappe.get_doc(
			{
				"doctype": "Mode of Payment",
				"mode_of_payment": mode,
				"enabled": True,
				"type": "Bank",
			}
		).insert(ignore_if_duplicate=True)


# Create ecommerce item group


def create_ecommerce_group():
	parent = "Ecommerce Website"
	parent_categories = {"Men", "Women", "Kids"}
	# Create parent group
	frappe.get_doc(
		{
			"doctype": "Item Group",
			"item_group_name": parent,
			"is_group": True,
			"parent_item_group": "All Item Groups",
		}
	).insert(ignore_if_duplicate=True)
	for category in parent_categories:
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": category,
				"is_group": True,
				"parent_item_group": parent,
				"custom_item_group_display_name": category,
			}
		).insert(ignore_if_duplicate=True)
