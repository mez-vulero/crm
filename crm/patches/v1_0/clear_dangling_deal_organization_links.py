import frappe


def execute():
	"""Clear references to non-existent CRM Organizations on CRM Lead and CRM Deal.

	Older datasets (and demo seeds) sometimes carry an organization name on
	leads/deals that was never created as a CRM Organization. With link
	validation enforced this raises LinkValidationError on save / convert.
	"""

	for doctype in ("CRM Lead", "CRM Deal"):
		if not frappe.db.has_column(doctype, "organization"):
			continue
		rows = frappe.db.sql(
			f"""SELECT name, organization FROM `tab{doctype}`
			WHERE organization IS NOT NULL AND organization != ''""",
			as_dict=True,
		)
		for row in rows:
			if not frappe.db.exists("CRM Organization", row.organization):
				frappe.db.set_value(
					doctype, row.name, "organization", None, update_modified=False
				)

	frappe.db.commit()
