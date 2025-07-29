import frappe


@frappe.whitelist()
def return_items(sales_order_id, items):
	# Find the delivery note linked to this sales order
	delivery_note_item = frappe.get_all(
		"Delivery Note Item",
		filters={"against_sales_order": sales_order_id},
		fields=["parent", "item_code", "qty"],
		order_by="creation asc",
	)

	if not delivery_note_item:
		frappe.throw(frappe._("No Delivery Note found for this Sales Order."))

	# Get the Delivery Note doc (assuming first match)
	dn_name = delivery_note_item[0]["parent"]
	original_dn = frappe.get_doc("Delivery Note", dn_name)

	# Build the return delivery note
	return_dn = frappe.copy_doc(original_dn)
	return_dn.set("is_return", 1)
	return_dn.set("return_against", dn_name)
	return_dn.set("items", [])
	item_map = {i["item_code"]: i for i in items}
	for item in original_dn.items:
		if item.item_code in item_map:
			meta = item_map[item.item_code]
			return_dn.append(
				"items",
				{
					"item_code": item.item_code,
					"qty": -1 * item.qty,
					"against_sales_order": item.against_sales_order,
					"so_detail": item.so_detail,
					"dn_detail": item.name,
					"price_list_rate": item.price_list_rate,
					"rate": item.rate,
					"warehouse": item.warehouse,
					"is_free_item": item.is_free_item,
					"custom_reason_for_return": meta.get("reason"),
					"custom_return_remarks": meta.get("comment"),
				},
			)

	if not return_dn.items:
		frappe.throw(
			frappe._(
				"None of the items to return were found in the original Delivery Note."
			)
		)

	return_dn.insert(ignore_permissions=True)

	return {"success": True}


@frappe.whitelist()
def get_returned_items(sales_order_id):
	# Fetch all returned Delivery Note Items for this Sales Order
	sales_order = frappe.get_doc("Sales Order", sales_order_id)

	free_items_map = {}
	for pr in sales_order.get("pricing_rules") or []:
		pricing_rule = frappe.get_cached_doc("Pricing Rule", pr.pricing_rule)
		if pricing_rule.free_item:
			free_items_map[pr.item_code] = pricing_rule.free_item
	sales_order_items = frappe.get_all(
		"Sales Order Item", filters={"parent": sales_order_id}, fields=["item_code"]
	)
	ordered_item_codes = [item.item_code for item in sales_order_items]
	returned_items = frappe.get_all(
		"Delivery Note Item",
		filters={
			"against_sales_order": sales_order_id,
			"docstatus": 1,  # Only submitted
			"parenttype": "Delivery Note",
			"qty": ("<", 0),
		},
		fields=["item_code"],
	)
	returned_items_in_draft = frappe.get_all(
		"Delivery Note Item",
		filters={
			"against_sales_order": sales_order_id,
			"docstatus": 0,  # Only draft
			"parenttype": "Delivery Note",
			"qty": ("<", 0),
		},
		fields=["item_code"],
	)

	returned_item_codes = [item.item_code for item in returned_items]

	returned_draft_item_codes = [item.item_code for item in returned_items_in_draft]

	is_fully_returned = all(
		item_code in returned_item_codes for item_code in ordered_item_codes
	)
	partially_returned = len(returned_item_codes) > 0 and not is_fully_returned

	return {
		"returned_items": returned_item_codes,
		"returned_items_in_draft": returned_draft_item_codes,
		"is_fully_returned": is_fully_returned,
		"free_items_map": free_items_map,
		"partially_returned": partially_returned,
	}
