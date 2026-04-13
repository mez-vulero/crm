import frappe
from frappe import _
from frappe.model.document import Document


class PaymentCollection(Document):
	def on_update(self):
		self.update_payment_schedule_row()
		self.update_deal_totals()

	def update_payment_schedule_row(self):
		if not self.payment_schedule_row or not self.deal:
			return
		deal = frappe.get_doc("CRM Deal", self.deal)
		for row in deal.get("re_payment_schedule", []):
			if row.name == self.payment_schedule_row:
				if self.amount_received >= (self.scheduled_amount or 0):
					row.status = "Paid"
				else:
					row.status = "Pending"
				row.payment_date = self.payment_date
				break
		deal.save(ignore_permissions=True)

	def update_deal_totals(self):
		if not self.deal:
			return
		total_collected = frappe.db.sql(
			"""SELECT COALESCE(SUM(amount_received), 0)
			FROM `tabPayment Collection`
			WHERE deal = %s AND status != 'Refunded'""",
			self.deal,
		)[0][0]

		purchase_price = frappe.db.get_value("CRM Deal", self.deal, "re_purchase_price") or 0
		outstanding = purchase_price - total_collected

		if total_collected <= 0:
			payment_status = "Not Started"
		elif outstanding <= 0:
			payment_status = "Fully Paid"
		else:
			today = frappe.utils.today()
			overdue = frappe.db.sql(
				"""SELECT COUNT(*) FROM `tabPayment Schedule`
				WHERE parent = %s AND parenttype = 'CRM Deal'
				AND due_date < %s AND status != 'Paid'""",
				(self.deal, today),
			)[0][0]
			payment_status = "Overdue" if overdue else "In Progress"

		frappe.db.set_value("CRM Deal", self.deal, {
			"re_total_collected": total_collected,
			"re_outstanding_amount": outstanding,
			"re_payment_status": payment_status,
		})

	@staticmethod
	def default_list_data():
		columns = [
			{"label": "Payment #", "type": "Data", "key": "name", "width": "10rem"},
			{"label": "Deal", "type": "Link", "key": "deal", "options": "CRM Deal", "width": "10rem"},
			{"label": "Amount", "type": "Currency", "key": "amount_received", "width": "8rem"},
			{"label": "Date", "type": "Date", "key": "payment_date", "width": "8rem"},
			{"label": "Method", "type": "Select", "key": "payment_method", "width": "8rem"},
			{"label": "Status", "type": "Select", "key": "status", "width": "8rem"},
			{"label": "Last Modified", "type": "Datetime", "key": "modified", "width": "8rem"},
		]
		rows = [
			"name", "deal", "project", "unit", "buyer_name", "amount_received",
			"payment_date", "payment_method", "reference_number", "status",
			"invoice", "milestone_description", "modified",
		]
		return {"columns": columns, "rows": rows}


@frappe.whitelist()
def get_payment_summary(deal: str) -> dict:
	if not frappe.has_permission("CRM Deal", "read", deal):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	total_collected = frappe.db.sql(
		"""SELECT COALESCE(SUM(amount_received), 0)
		FROM `tabPayment Collection`
		WHERE deal = %s AND status != 'Refunded'""",
		deal,
	)[0][0]

	schedule_rows = frappe.get_all(
		"Payment Schedule",
		filters={"parent": deal, "parenttype": "CRM Deal"},
		fields=["name", "milestone", "due_date", "amount", "status", "payment_date"],
	)
	total_scheduled = sum(r.amount or 0 for r in schedule_rows)
	outstanding = total_scheduled - total_collected

	today = frappe.utils.today()
	overdue_rows = [
		r for r in schedule_rows
		if r.due_date and str(r.due_date) < today and r.status != "Paid"
	]

	return {
		"total_scheduled": total_scheduled,
		"total_collected": total_collected,
		"outstanding": outstanding,
		"overdue_count": len(overdue_rows),
	}
