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

	# Unit sales funnel
	units = frappe.get_all(
		"Property Unit",
		fields=["status"],
	)
	unit_funnel = {
		"total": len(units),
		"available": sum(1 for u in units if u.status == "Available"),
		"reserved": sum(1 for u in units if u.status == "Reserved"),
		"sold": sum(1 for u in units if u.status == "Sold"),
		"blocked": sum(1 for u in units if u.status == "Blocked"),
	}

	# Revenue collection progress
	total_scheduled = frappe.db.sql(
		"""SELECT COALESCE(SUM(ps.amount), 0)
		FROM `tabPayment Schedule` ps
		WHERE ps.parenttype = 'CRM Deal'""",
	)[0][0]

	total_collected = frappe.db.sql(
		"""SELECT COALESCE(SUM(pc.amount_received), 0)
		FROM `tabPayment Collection` pc
		WHERE pc.status != 'Refunded'""",
	)[0][0]

	# Overdue payments
	today = frappe.utils.today()
	overdue_count = frappe.db.sql(
		"""SELECT COUNT(*) FROM `tabPayment Schedule`
		WHERE parenttype = 'CRM Deal'
		AND due_date < %s AND status != 'Paid'""",
		today,
	)[0][0]

	overdue_amount = frappe.db.sql(
		"""SELECT COALESCE(SUM(amount), 0) FROM `tabPayment Schedule`
		WHERE parenttype = 'CRM Deal'
		AND due_date < %s AND status != 'Paid'""",
		today,
	)[0][0]

	# Commission summary
	commission_pending = frappe.db.sql(
		"""SELECT COALESCE(SUM(final_commission), 0)
		FROM `tabSales Commission` WHERE status = 'Pending'""",
	)[0][0]

	commission_approved = frappe.db.sql(
		"""SELECT COALESCE(SUM(final_commission), 0)
		FROM `tabSales Commission` WHERE status = 'Approved'""",
	)[0][0]

	commission_paid = frappe.db.sql(
		"""SELECT COALESCE(SUM(final_commission), 0)
		FROM `tabSales Commission` WHERE status = 'Paid'""",
	)[0][0]

	return {
		"unit_funnel": unit_funnel,
		"revenue": {
			"scheduled": total_scheduled,
			"collected": total_collected,
			"outstanding": total_scheduled - total_collected,
		},
		"overdue": {
			"count": overdue_count,
			"amount": overdue_amount,
		},
		"commissions": {
			"pending": commission_pending,
			"approved": commission_approved,
			"paid": commission_paid,
		},
	}
