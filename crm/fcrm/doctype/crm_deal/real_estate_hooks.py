import frappe


def calculate_commission(doc, method=None):
	if doc.get("re_purchase_price") and doc.get("re_commission_rate"):
		doc.re_commission_amount = (doc.re_purchase_price * doc.re_commission_rate) / 100
	elif not doc.get("re_purchase_price") or not doc.get("re_commission_rate"):
		doc.re_commission_amount = 0


def sync_purchase_price_to_unit(doc, method=None):
	"""When the deal's purchase price differs from the linked unit's base price,
	persist the override on the unit so the unit reflects the negotiated price.
	If the deal price matches the unit's base price, clear any existing override.
	"""
	if not doc.get("re_unit"):
		return

	new_price = doc.get("re_purchase_price")
	if new_price is None:
		return

	unit_price = frappe.db.get_value(
		"Property Unit", doc.re_unit, ["base_price", "price_override"], as_dict=True
	)
	if not unit_price:
		return

	base = unit_price.base_price or 0
	override = unit_price.price_override or 0

	if new_price and new_price != base:
		if override != new_price:
			frappe.db.set_value("Property Unit", doc.re_unit, "price_override", new_price)
	elif override:
		frappe.db.set_value("Property Unit", doc.re_unit, "price_override", 0)
