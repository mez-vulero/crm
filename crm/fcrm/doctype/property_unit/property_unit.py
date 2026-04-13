import frappe
from frappe import _
from frappe.model.document import Document


class PropertyUnit(Document):
	def validate(self):
		self.on_status_change()

	def on_status_change(self):
		if self.has_value_changed("status") and self.status == "Available":
			self.linked_deal = None

	def on_update(self):
		self.update_project_counts()

	def after_delete(self):
		self.update_project_counts()

	def update_project_counts(self):
		if self.project:
			project = frappe.get_doc("Real Estate Project", self.project)
			project.update_unit_counts()
			project.save(ignore_permissions=True)


@frappe.whitelist()
def get_available_units(project: str, unit_type: str | None = None) -> list[dict]:
	if not frappe.has_permission("Property Unit", "read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	filters = {"project": project, "status": "Available"}
	if unit_type:
		filters["unit_type"] = unit_type

	return frappe.get_all(
		"Property Unit",
		filters=filters,
		fields=[
			"name",
			"unit_number",
			"unit_type",
			"floor",
			"size_sqm",
			"base_price",
			"price_override",
			"view_direction",
		],
		order_by="floor asc, unit_number asc",
	)
