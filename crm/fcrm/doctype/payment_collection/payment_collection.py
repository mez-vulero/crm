import frappe
from frappe import _
from frappe.model.document import Document


class PaymentCollection(Document):
	def validate(self):
		self._warn_if_already_paid()

	def _warn_if_already_paid(self):
		if not self.payment_schedule_row or not self.deal:
			return
		existing = frappe.db.sql(
			"""SELECT name FROM `tabPayment Collection`
			WHERE deal = %s AND payment_schedule_row = %s
			AND status != 'Refunded' AND name != %s""",
			(self.deal, self.payment_schedule_row, self.name or ""),
		)
		if existing:
			frappe.msgprint(
				_("A payment already exists for this schedule milestone ({0}). This may result in duplicate payments.").format(
					self.milestone_description or self.payment_schedule_row
				),
				indicator="orange",
				alert=True,
			)

	def on_update(self):
		if not self.deal:
			return
		if not self.has_value_changed("amount_received") and not self.has_value_changed("status") and not self.has_value_changed("payment_schedule_row"):
			return
		deal = frappe.get_doc("CRM Deal", self.deal)
		self._update_payment_schedule_row(deal)
		self._update_deal_totals(deal)
		deal.save(ignore_permissions=True)

	def on_trash(self):
		if not self.deal:
			return
		deal = frappe.get_doc("CRM Deal", self.deal)
		self._update_deal_totals(deal)
		deal.save(ignore_permissions=True)

	def _update_payment_schedule_row(self, deal):
		if not self.payment_schedule_row:
			return
		for row in deal.get("re_payment_schedule", []):
			if row.name == self.payment_schedule_row:
				if self.amount_received >= (self.scheduled_amount or 0):
					row.status = "Paid"
				else:
					row.status = "Pending"
				row.payment_date = self.payment_date
				break

	def _update_deal_totals(self, deal):
		total_collected = frappe.db.sql(
			"""SELECT COALESCE(SUM(amount_received), 0)
			FROM `tabPayment Collection`
			WHERE deal = %s AND status != 'Refunded'""",
			self.deal,
		)[0][0]

		purchase_price = deal.get("re_purchase_price") or 0
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

		deal.re_total_collected = total_collected
		deal.re_outstanding_amount = outstanding
		deal.re_payment_status = payment_status

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
