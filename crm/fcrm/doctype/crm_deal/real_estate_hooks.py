import frappe


def calculate_commission(doc, method=None):
	if doc.get("re_purchase_price") and doc.get("re_commission_rate"):
		doc.re_commission_amount = (doc.re_purchase_price * doc.re_commission_rate) / 100
	elif not doc.get("re_purchase_price") or not doc.get("re_commission_rate"):
		doc.re_commission_amount = 0
