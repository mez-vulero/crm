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
def bulk_update_status(unit_names: list[str] | str, status: str) -> dict:
	if not frappe.has_permission("Property Unit", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	if isinstance(unit_names, str):
		import json
		unit_names = json.loads(unit_names)

	allowed = {"Available", "Reserved", "Sold", "Hold", "Blocked"}
	if status not in allowed:
		frappe.throw(_("Invalid status: {0}").format(status))

	updated = 0
	failed = []
	for name in unit_names:
		try:
			doc = frappe.get_doc("Property Unit", name)
			doc.status = status
			doc.save()
			updated += 1
		except Exception as exc:
			failed.append({"name": name, "error": str(exc)})

	return {"updated": updated, "failed": failed}


@frappe.whitelist()
def bulk_update_price(unit_names: list[str] | str, price: float) -> dict:
	if not frappe.has_permission("Property Unit", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	if isinstance(unit_names, str):
		import json
		unit_names = json.loads(unit_names)

	try:
		price = float(price)
	except (TypeError, ValueError):
		frappe.throw(_("Invalid price"))

	if price < 0:
		frappe.throw(_("Price cannot be negative"))

	updated = 0
	failed = []
	for name in unit_names:
		try:
			doc = frappe.get_doc("Property Unit", name)
			doc.price_override = price
			doc.save()
			updated += 1
		except Exception as exc:
			failed.append({"name": name, "error": str(exc)})

	return {"updated": updated, "failed": failed}


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
