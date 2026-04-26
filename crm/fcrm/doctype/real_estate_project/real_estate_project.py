import frappe
from frappe import _
from frappe.model.document import Document


class RealEstateProject(Document):
	def validate(self):
		self.update_unit_counts()

	@staticmethod
	def default_list_data():
		columns = [
			{
				"label": "Project Name",
				"type": "Data",
				"key": "project_name",
				"width": "14rem",
			},
			{
				"label": "Status",
				"type": "Select",
				"key": "status",
				"width": "8rem",
			},
			{
				"label": "City",
				"type": "Data",
				"key": "city",
				"width": "8rem",
			},
			{
				"label": "Total Units",
				"type": "Int",
				"key": "total_units",
				"width": "7rem",
			},
			{
				"label": "Available",
				"type": "Int",
				"key": "available_units",
				"width": "7rem",
			},
			{
				"label": "Reserved",
				"type": "Int",
				"key": "reserved_units",
				"width": "7rem",
			},
			{
				"label": "Sold",
				"type": "Int",
				"key": "sold_units",
				"width": "7rem",
			},
			{
				"label": "Launch Date",
				"type": "Date",
				"key": "launch_date",
				"width": "8rem",
			},
			{
				"label": "Last Modified",
				"type": "Datetime",
				"key": "modified",
				"width": "8rem",
			},
		]
		rows = [
			"name",
			"project_name",
			"status",
			"city",
			"location",
			"total_units",
			"available_units",
			"reserved_units",
			"sold_units",
			"launch_date",
			"delivery_date",
			"image",
			"modified",
		]
		return {"columns": columns, "rows": rows}

	def update_unit_counts(self):
		units = frappe.get_all(
			"Property Unit",
			filters={"project": self.name},
			fields=["status"],
		)
		self.total_units = len(units)
		self.available_units = sum(1 for u in units if u.status == "Available")
		self.reserved_units = sum(1 for u in units if u.status == "Reserved")
		self.sold_units = sum(1 for u in units if u.status == "Sold")


@frappe.whitelist()
def get_unit_summary(project: str) -> dict:
	if not frappe.has_permission("Real Estate Project", "read", project):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	units = frappe.get_all(
		"Property Unit",
		filters={"project": project},
		fields=["status"],
	)
	summary = {
		"total": len(units),
		"available": sum(1 for u in units if u.status == "Available"),
		"reserved": sum(1 for u in units if u.status == "Reserved"),
		"sold": sum(1 for u in units if u.status == "Sold"),
		"blocked": sum(1 for u in units if u.status == "Blocked"),
	}
	return summary


@frappe.whitelist()
def get_real_estate_dashboard() -> dict:
	if not frappe.has_permission("Real Estate Project", "read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	unit_rows = frappe.db.sql(
		"""SELECT status, COUNT(*) AS cnt FROM `tabProperty Unit` GROUP BY status""",
		as_dict=True,
	)
	unit_funnel = {r.status or "Unknown": r.cnt for r in unit_rows}

	scheduled = frappe.db.sql(
		"""SELECT COALESCE(SUM(amount), 0)
		FROM `tabPayment Schedule`
		WHERE parenttype = 'CRM Deal'"""
	)[0][0]

	collected = frappe.db.sql(
		"""SELECT COALESCE(SUM(amount_received), 0)
		FROM `tabPayment Collection`
		WHERE status != 'Refunded'"""
	)[0][0]

	outstanding = (scheduled or 0) - (collected or 0)

	today = frappe.utils.today()
	overdue_rows = frappe.db.sql(
		"""SELECT COUNT(*) AS cnt, COALESCE(SUM(amount), 0) AS amt
		FROM `tabPayment Schedule`
		WHERE parenttype = 'CRM Deal'
		AND due_date < %s AND status != 'Paid'""",
		today,
		as_dict=True,
	)
	overdue = {
		"count": overdue_rows[0].cnt if overdue_rows else 0,
		"amount": overdue_rows[0].amt if overdue_rows else 0,
	}

	commission_rows = frappe.db.sql(
		"""SELECT status, COALESCE(SUM(final_commission), 0) AS amt
		FROM `tabSales Commission`
		GROUP BY status""",
		as_dict=True,
	)
	commissions = {r.status or "Unknown": r.amt for r in commission_rows}

	return {
		"unit_funnel": unit_funnel,
		"revenue": {
			"scheduled": scheduled or 0,
			"collected": collected or 0,
			"outstanding": outstanding,
		},
		"overdue": overdue,
		"commissions": {
			"pending": commissions.get("Pending", 0),
			"approved": commissions.get("Approved", 0),
			"paid": commissions.get("Paid", 0),
		},
	}
