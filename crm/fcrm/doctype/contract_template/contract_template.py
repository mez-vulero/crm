import frappe
from frappe import _
from frappe.model.document import Document


class ContractTemplate(Document):
	@staticmethod
	def default_list_data():
		columns = [
			{"label": "Template Name", "type": "Data", "key": "template_name", "width": "16rem"},
			{"label": "Description", "type": "Small Text", "key": "description", "width": "20rem"},
			{"label": "Last Modified", "type": "Datetime", "key": "modified", "width": "8rem"},
		]
		rows = ["name", "template_name", "description", "modified"]
		return {"columns": columns, "rows": rows}


@frappe.whitelist()
def get_preview(template_name: str, contract_name: str | None = None) -> str:
	if not frappe.has_permission("Contract Template", "read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	template = frappe.get_doc("Contract Template", template_name)
	context = {}

	if contract_name:
		contract = frappe.get_doc("Property Contract", contract_name)
		unit_doc = frappe.get_doc("Property Unit", contract.unit) if contract.unit else frappe._dict()
		project_doc = frappe.get_doc("Real Estate Project", contract.project) if contract.project else frappe._dict()
		context = {
			"buyer_name": contract.buyer_name or "",
			"buyer_email": contract.buyer_email or "",
			"buyer_phone": contract.buyer_phone or "",
			"purchase_price": contract.purchase_price or 0,
			"contract_date": str(contract.contract_date or ""),
			"deed_date": str(contract.deed_date or ""),
			"unit_number": unit_doc.get("unit_number", ""),
			"floor": unit_doc.get("floor", ""),
			"size_sqm": unit_doc.get("size_sqm", ""),
			"project_name": project_doc.get("project_name", ""),
		}
	else:
		context = {
			"buyer_name": "John Doe",
			"buyer_email": "john@example.com",
			"buyer_phone": "+1234567890",
			"purchase_price": "500,000",
			"contract_date": "2026-01-01",
			"deed_date": "2026-06-01",
			"unit_number": "A-101",
			"floor": "1",
			"size_sqm": "120",
			"project_name": "Sample Project",
		}

	header = frappe.render_template(template.header_html or "", context)
	body = frappe.render_template(template.body, context)
	footer = frappe.render_template(template.footer_html or "", context)

	return f"{header}{body}{footer}"
