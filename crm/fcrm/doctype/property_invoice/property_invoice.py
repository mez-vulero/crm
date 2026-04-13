import frappe
from frappe import _
from frappe.model.document import Document


class PropertyInvoice(Document):
	def validate(self):
		self.calculate_totals()

	def before_save(self):
		for item in self.get("line_items", []):
			item.amount = (item.quantity or 0) * (item.unit_price or 0)

	def after_insert(self):
		if self.deal and not self.buyer_name:
			deal = frappe.get_doc("CRM Deal", self.deal)
			self.db_set("buyer_name", deal.get("first_name") or "", update_modified=False)
			self.db_set("buyer_email", deal.get("email") or "", update_modified=False)

	def calculate_totals(self):
		self.subtotal = sum((item.quantity or 0) * (item.unit_price or 0) for item in self.get("line_items", []))
		self.tax_amount = (self.subtotal * (self.tax_rate or 0)) / 100
		self.total_amount = self.subtotal + self.tax_amount

	@staticmethod
	def default_list_data():
		columns = [
			{"label": "Invoice #", "type": "Data", "key": "name", "width": "10rem"},
			{"label": "Deal", "type": "Link", "key": "deal", "options": "CRM Deal", "width": "10rem"},
			{"label": "Buyer", "type": "Data", "key": "buyer_name", "width": "10rem"},
			{"label": "Total", "type": "Currency", "key": "total_amount", "width": "8rem"},
			{"label": "Status", "type": "Select", "key": "status", "width": "8rem"},
			{"label": "Date", "type": "Date", "key": "invoice_date", "width": "8rem"},
			{"label": "Last Modified", "type": "Datetime", "key": "modified", "width": "8rem"},
		]
		rows = [
			"name", "deal", "buyer_name", "buyer_email", "total_amount",
			"status", "invoice_date", "pdf_attachment", "modified",
		]
		return {"columns": columns, "rows": rows}


@frappe.whitelist()
def generate_invoice_pdf(invoice_name: str) -> str:
	if not frappe.has_permission("Property Invoice", "write", invoice_name):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	inv = frappe.get_doc("Property Invoice", invoice_name)

	rows_html = ""
	for item in inv.get("line_items", []):
		rows_html += f"""<tr>
			<td style="padding:8px;border-bottom:1px solid #eee">{item.description}</td>
			<td style="padding:8px;border-bottom:1px solid #eee;text-align:right">{item.quantity}</td>
			<td style="padding:8px;border-bottom:1px solid #eee;text-align:right">{item.unit_price:,.2f}</td>
			<td style="padding:8px;border-bottom:1px solid #eee;text-align:right">{item.amount:,.2f}</td>
		</tr>"""

	html = f"""
	<html><body style="font-family:Arial,sans-serif;padding:40px">
	<h1 style="color:#333">Invoice {inv.name}</h1>
	<table style="width:100%;margin-bottom:20px">
		<tr><td><strong>Buyer:</strong> {inv.buyer_name or ''}</td>
			<td style="text-align:right"><strong>Date:</strong> {inv.invoice_date or ''}</td></tr>
		<tr><td>{inv.buyer_email or ''}</td>
			<td style="text-align:right"><strong>Due:</strong> {inv.due_date or ''}</td></tr>
		<tr><td>{inv.buyer_address or ''}</td><td></td></tr>
	</table>
	<table style="width:100%;border-collapse:collapse">
		<thead><tr style="background:#f5f5f5">
			<th style="padding:8px;text-align:left">Description</th>
			<th style="padding:8px;text-align:right">Qty</th>
			<th style="padding:8px;text-align:right">Unit Price</th>
			<th style="padding:8px;text-align:right">Amount</th>
		</tr></thead>
		<tbody>{rows_html}</tbody>
		<tfoot>
			<tr><td colspan="3" style="padding:8px;text-align:right"><strong>Subtotal</strong></td>
				<td style="padding:8px;text-align:right">{inv.subtotal:,.2f}</td></tr>
			<tr><td colspan="3" style="padding:8px;text-align:right"><strong>Tax ({inv.tax_rate or 0}%)</strong></td>
				<td style="padding:8px;text-align:right">{inv.tax_amount:,.2f}</td></tr>
			<tr style="font-size:1.1em"><td colspan="3" style="padding:8px;text-align:right"><strong>Total</strong></td>
				<td style="padding:8px;text-align:right"><strong>{inv.total_amount:,.2f}</strong></td></tr>
		</tfoot>
	</table>
	{f'<p style="margin-top:20px;color:#666">{inv.notes}</p>' if inv.notes else ''}
	</body></html>
	"""

	from frappe.utils.pdf import get_pdf

	pdf_content = get_pdf(html)
	file_name = f"{inv.name}.pdf"
	_file = frappe.get_doc({
		"doctype": "File",
		"file_name": file_name,
		"content": pdf_content,
		"attached_to_doctype": "Property Invoice",
		"attached_to_name": invoice_name,
		"is_private": 1,
	})
	_file.save(ignore_permissions=True)

	inv.db_set("pdf_attachment", _file.file_url, update_modified=False)

	if inv.payment_collection:
		frappe.db.set_value("Payment Collection", inv.payment_collection, "invoice", inv.name)

	return _file.file_url


@frappe.whitelist()
def send_invoice_by_email(invoice_name: str) -> None:
	if not frappe.has_permission("Property Invoice", "write", invoice_name):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	inv = frappe.get_doc("Property Invoice", invoice_name)
	if not inv.buyer_email:
		frappe.throw(_("Buyer email is not set"))
	if not inv.pdf_attachment:
		frappe.throw(_("Please generate the PDF first"))

	frappe.sendmail(
		recipients=inv.buyer_email,
		subject=f"Invoice {inv.name}",
		message=f"<p>Dear {inv.buyer_name or 'Customer'},</p><p>Please find attached your invoice {inv.name} for the amount of {inv.total_amount:,.2f}.</p><p>Thank you.</p>",
		attachments=[{"file_url": inv.pdf_attachment}],
		now=True,
	)

	inv.db_set("status", "Sent", update_modified=True)
