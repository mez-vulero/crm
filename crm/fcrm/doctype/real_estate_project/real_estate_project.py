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
