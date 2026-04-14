import frappe
from frappe import _
from frappe.model.document import Document


class SalesCommission(Document):
	def validate(self):
		self.fetch_commission_base()
		self.calculate_commission()
		self.validate_split_percentage()
		self.warn_if_deal_not_won()

	def fetch_commission_base(self):
		if self.deal and not self.commission_base:
			self.commission_base = frappe.db.get_value(
				"CRM Deal", self.deal, "re_purchase_price"
			) or 0

	def calculate_commission(self):
		if self.commission_base and self.commission_rate:
			self.commission_amount = (self.commission_base * self.commission_rate) / 100
		else:
			self.commission_amount = 0
		self.final_commission = (self.commission_amount * (self.split_percentage or 100)) / 100

	def validate_split_percentage(self):
		if not self.deal or not self.role:
			return
		total_split = frappe.db.sql(
			"""SELECT COALESCE(SUM(split_percentage), 0)
			FROM `tabSales Commission`
			WHERE deal = %s AND role = %s AND status != 'Cancelled'
			AND name != %s""",
			(self.deal, self.role, self.name or ""),
		)[0][0]
		if total_split + (self.split_percentage or 0) > 100:
			frappe.msgprint(
				_("Total split percentage for {0} on this deal is {1}%, adding {2}% would exceed 100%").format(
					self.role, total_split, self.split_percentage
				),
				indicator="orange",
				alert=True,
			)

	def warn_if_deal_not_won(self):
		if not self.deal:
			return
		deal_status = frappe.db.get_value("CRM Deal", self.deal, "deal_status")
		if not deal_status:
			return
		status_type = frappe.db.get_value("CRM Deal Status", deal_status, "status_type")
		if status_type != "Won":
			frappe.msgprint(
				_("Deal {0} is not in a Won status (current: {1}). Commission may be premature.").format(
					self.deal, deal_status
				),
				indicator="orange",
				alert=True,
			)

	def on_update(self):
		self.update_deal_commission_total()

	def update_deal_commission_total(self):
		if not self.deal:
			return
		total = frappe.db.sql(
			"""SELECT COALESCE(SUM(final_commission), 0)
			FROM `tabSales Commission`
			WHERE deal = %s AND status IN ('Approved', 'Paid')""",
			self.deal,
		)[0][0]
		deal = frappe.get_doc("CRM Deal", self.deal)
		deal.re_total_commission = total
		deal.save(ignore_permissions=True)

	@staticmethod
	def default_list_data():
		columns = [
			{"label": "Deal", "type": "Link", "key": "deal", "options": "CRM Deal", "width": "10rem"},
			{"label": "Agent", "type": "Data", "key": "agent_name", "width": "10rem"},
			{"label": "Role", "type": "Select", "key": "role", "width": "8rem"},
			{"label": "Rate %", "type": "Percent", "key": "commission_rate", "width": "6rem"},
			{"label": "Final Commission", "type": "Currency", "key": "final_commission", "width": "10rem"},
			{"label": "Status", "type": "Select", "key": "status", "width": "8rem"},
			{"label": "Last Modified", "type": "Datetime", "key": "modified", "width": "8rem"},
		]
		rows = [
			"name", "deal", "agent", "agent_name", "role", "commission_rate",
			"commission_amount", "split_percentage", "final_commission",
			"trigger_event", "status", "project", "unit", "modified",
		]
		return {"columns": columns, "rows": rows}


@frappe.whitelist()
def approve_commission(commission_name: str) -> None:
	if not frappe.has_permission("Sales Commission", "write", commission_name):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	commission = frappe.get_doc("Sales Commission", commission_name)
	commission.status = "Approved"
	commission.approved_by = frappe.session.user
	commission.approved_date = frappe.utils.today()
	commission.save(ignore_permissions=True)


@frappe.whitelist()
def get_commissions_for_deal(deal: str) -> list[dict]:
	if not frappe.has_permission("CRM Deal", "read", deal):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	return frappe.get_all(
		"Sales Commission",
		filters={"deal": deal},
		fields=[
			"name", "agent", "agent_name", "role", "commission_base",
			"commission_rate", "commission_amount", "split_percentage",
			"final_commission", "trigger_event", "status",
			"approved_by", "approved_date", "paid_date",
		],
		order_by="creation desc",
	)


@frappe.whitelist()
def get_agent_commission_summary(
	agent: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict:
	if not agent:
		agent = frappe.session.user

	if agent != frappe.session.user and agent != "__all__" and "Sales Manager" not in frappe.get_roles():
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	date_condition = ""
	date_params: list = []
	if from_date:
		date_condition += " AND sc.creation >= %s"
		date_params.append(from_date)
	if to_date:
		date_condition += " AND sc.creation <= %s"
		date_params.append(to_date)

	agent_condition = ""
	agent_params: list = []
	if agent and agent != "__all__":
		agent_condition = "AND sc.agent = %s"
		agent_params = [agent]

	params = agent_params + date_params

	pending = frappe.db.sql(
		f"""SELECT COALESCE(SUM(sc.final_commission), 0)
		FROM `tabSales Commission` sc WHERE sc.status = 'Pending' {agent_condition} {date_condition}""",
		params,
	)[0][0]

	approved = frappe.db.sql(
		f"""SELECT COALESCE(SUM(sc.final_commission), 0)
		FROM `tabSales Commission` sc WHERE sc.status = 'Approved' {agent_condition} {date_condition}""",
		params,
	)[0][0]

	paid = frappe.db.sql(
		f"""SELECT COALESCE(SUM(sc.final_commission), 0)
		FROM `tabSales Commission` sc WHERE sc.status = 'Paid' {agent_condition} {date_condition}""",
		params,
	)[0][0]

	filters = {}
	if agent and agent != "__all__":
		filters["agent"] = agent
	if from_date:
		filters["creation"] = [">=", from_date]
	if to_date:
		filters["creation"] = ["<=", to_date] if "creation" not in filters else ["between", [from_date, to_date]]

	records = frappe.get_all(
		"Sales Commission",
		filters=filters,
		fields=[
			"name", "deal", "project", "unit", "agent", "agent_name",
			"role", "commission_rate", "final_commission",
			"trigger_event", "status", "modified",
		],
		order_by="creation desc",
		page_length=100,
	)

	return {
		"pending": pending,
		"approved": approved,
		"paid": paid,
		"records": records,
	}
