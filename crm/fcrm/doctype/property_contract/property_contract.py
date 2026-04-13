import frappe
from frappe import _
from frappe.model.document import Document


class PropertyContract(Document):
	def after_insert(self):
		self.fetch_deal_data()

	def fetch_deal_data(self):
		if not self.deal:
			return
		deal = frappe.get_doc("CRM Deal", self.deal)
		updates = {}
		if not self.buyer_name:
			updates["buyer_name"] = deal.get("first_name") or deal.get("lead_name") or ""
		if not self.buyer_email:
			updates["buyer_email"] = deal.get("email") or ""
		if not self.buyer_phone:
			updates["buyer_phone"] = deal.get("mobile_no") or ""
		if not self.purchase_price:
			updates["purchase_price"] = deal.get("re_purchase_price") or 0
		if not self.project:
			updates["project"] = deal.get("re_project") or ""
		if not self.unit:
			updates["unit"] = deal.get("re_unit") or ""
		if updates:
			for key, val in updates.items():
				self.db_set(key, val, update_modified=False)

	@staticmethod
	def default_list_data():
		columns = [
			{"label": "Contract #", "type": "Data", "key": "name", "width": "10rem"},
			{"label": "Deal", "type": "Link", "key": "deal", "options": "CRM Deal", "width": "10rem"},
			{"label": "Project", "type": "Link", "key": "project", "options": "Real Estate Project", "width": "10rem"},
			{"label": "Status", "type": "Select", "key": "status", "width": "8rem"},
			{"label": "Contract Date", "type": "Date", "key": "contract_date", "width": "8rem"},
			{"label": "Last Modified", "type": "Datetime", "key": "modified", "width": "8rem"},
		]
		rows = [
			"name", "deal", "project", "unit", "status", "contract_date",
			"signed_date", "buyer_name", "template", "pdf_attachment", "modified",
		]
		return {"columns": columns, "rows": rows}


@frappe.whitelist()
def generate_contract(contract_name: str) -> str:
	if not frappe.has_permission("Property Contract", "write", contract_name):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	contract = frappe.get_doc("Property Contract", contract_name)
	if not contract.template:
		frappe.throw(_("Please select a Contract Template first"))

	from crm.fcrm.doctype.contract_template.contract_template import get_preview

	rendered_html = get_preview(contract.template, contract_name)
	contract.db_set("contract_body", rendered_html, update_modified=False)

	from frappe.utils.pdf import get_pdf

	pdf_content = get_pdf(rendered_html)

	file_name = f"{contract_name}.pdf"
	_file = frappe.get_doc({
		"doctype": "File",
		"file_name": file_name,
		"content": pdf_content,
		"attached_to_doctype": "Property Contract",
		"attached_to_name": contract_name,
		"is_private": 1,
	})
	_file.save(ignore_permissions=True)

	contract.db_set("pdf_attachment", _file.file_url, update_modified=False)
	return _file.file_url


@frappe.whitelist()
def mark_as_signed(contract_name: str, signed_date: str | None = None) -> None:
	if not frappe.has_permission("Property Contract", "write", contract_name):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	signed_date = signed_date or frappe.utils.today()
	contract = frappe.get_doc("Property Contract", contract_name)
	contract.db_set("status", "Signed", update_modified=True)
	contract.db_set("signed_date", signed_date, update_modified=False)

	if contract.deal:
		frappe.db.set_value("CRM Deal", contract.deal, "re_contract_date", signed_date)
