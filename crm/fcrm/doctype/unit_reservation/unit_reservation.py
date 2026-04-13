import frappe
from frappe import _
from frappe.model.document import Document


class UnitReservation(Document):
	def validate(self):
		if self.is_new():
			self.validate_unit_available()

	def after_insert(self):
		self.reserve_unit()

	def on_update(self):
		if self.has_value_changed("status"):
			if self.status in ("Cancelled", "Expired"):
				self.release_unit()
			elif self.status == "Active":
				self.reserve_unit()

	def validate_unit_available(self):
		unit_status = frappe.db.get_value("Property Unit", self.unit, "status")
		if unit_status not in ("Available", "Reserved"):
			frappe.throw(
				_("Unit {0} is {1} and cannot be reserved").format(self.unit, unit_status)
			)

	def reserve_unit(self):
		frappe.db.set_value("Property Unit", self.unit, {
			"status": "Reserved",
			"linked_deal": self.deal,
		})

	def release_unit(self):
		frappe.db.set_value("Property Unit", self.unit, {
			"status": "Available",
			"linked_deal": None,
		})


@frappe.whitelist()
def reserve_unit(
	unit: str,
	deal: str | None = None,
	lead: str | None = None,
	reservation_type: str = "Soft",
	deposit_amount: float = 0,
	expiry_date: str | None = None,
) -> str:
	if not frappe.has_permission("Unit Reservation", "create"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	reservation = frappe.new_doc("Unit Reservation")
	reservation.update({
		"unit": unit,
		"deal": deal,
		"lead": lead,
		"reservation_type": reservation_type,
		"deposit_amount": deposit_amount,
		"expiry_date": expiry_date,
	})
	reservation.insert()
	return reservation.name


def expire_soft_reservations():
	"""Daily scheduler: expire soft reservations past their expiry date.
	Hard reservations with deposit_paid are never auto-expired."""
	today = frappe.utils.today()
	expired = frappe.get_all(
		"Unit Reservation",
		filters={
			"status": "Active",
			"expiry_date": ["<", today],
		},
	)
	for r in expired:
		doc = frappe.get_doc("Unit Reservation", r.name)
		# Skip hard reservations with deposit paid
		if doc.reservation_type == "Hard" and doc.deposit_paid:
			continue
		doc.status = "Expired"
		doc.save(ignore_permissions=True)
	if expired:
		frappe.db.commit()
