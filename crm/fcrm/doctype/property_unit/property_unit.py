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


@frappe.whitelist()
def bulk_update_status(units: list[str], status: str) -> int:
	if not frappe.has_permission("Property Unit", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	if status not in ("Available", "Reserved", "Sold", "Blocked"):
		frappe.throw(_("Invalid status: {0}").format(status))

	count = 0
	for unit_name in units:
		unit = frappe.get_doc("Property Unit", unit_name)
		if unit.status != status:
			unit.status = status
			unit.save(ignore_permissions=True)
			count += 1

	return count


@frappe.whitelist()
def bulk_update_price(units: list[str], adjustment_type: str, adjustment_value: float) -> int:
	if not frappe.has_permission("Property Unit", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	if adjustment_type not in ("percentage", "fixed"):
		frappe.throw(_("Invalid adjustment type"))

	count = 0
	for unit_name in units:
		unit = frappe.get_doc("Property Unit", unit_name)
		current_price = unit.price_override or unit.base_price or 0
		if adjustment_type == "percentage":
			new_price = current_price * (1 + adjustment_value / 100)
		else:
			new_price = current_price + adjustment_value

		unit.price_override = new_price
		unit.save(ignore_permissions=True)
		count += 1

	return count
