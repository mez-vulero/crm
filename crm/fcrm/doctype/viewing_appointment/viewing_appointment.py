import frappe
from frappe import _
from frappe.model.document import Document


class ViewingAppointment(Document):
	@staticmethod
	def default_list_data():
		columns = [
			{"label": "Date", "type": "Date", "key": "appointment_date", "width": "8rem"},
			{"label": "Time", "type": "Time", "key": "appointment_time", "width": "6rem"},
			{"label": "Status", "type": "Select", "key": "status", "width": "8rem"},
			{"label": "Agent", "type": "Link", "key": "assigned_agent", "options": "User", "width": "10rem"},
			{"label": "Lead", "type": "Link", "key": "lead", "options": "CRM Lead", "width": "10rem"},
			{"label": "Deal", "type": "Link", "key": "deal", "options": "CRM Deal", "width": "10rem"},
			{"label": "Project", "type": "Link", "key": "project", "options": "Real Estate Project", "width": "10rem"},
			{"label": "Unit", "type": "Link", "key": "unit", "options": "Property Unit", "width": "8rem"},
			{"label": "Last Modified", "type": "Datetime", "key": "modified", "width": "8rem"},
		]
		rows = [
			"name", "appointment_date", "appointment_time", "status",
			"assigned_agent", "lead", "deal", "project", "unit",
			"feedback", "notes", "modified",
		]
		return {"columns": columns, "rows": rows}


@frappe.whitelist()
def schedule_viewing(
	appointment_date: str,
	appointment_time: str | None = None,
	lead: str | None = None,
	deal: str | None = None,
	project: str | None = None,
	unit: str | None = None,
	assigned_agent: str | None = None,
	notes: str | None = None,
) -> str:
	if not frappe.has_permission("Viewing Appointment", "create"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	appointment = frappe.new_doc("Viewing Appointment")
	appointment.update({
		"appointment_date": appointment_date,
		"appointment_time": appointment_time,
		"lead": lead,
		"deal": deal,
		"project": project,
		"unit": unit,
		"assigned_agent": assigned_agent or frappe.session.user,
		"notes": notes,
	})
	appointment.insert()
	return appointment.name


@frappe.whitelist()
def get_appointments(
	lead: str | None = None,
	deal: str | None = None,
	project: str | None = None,
	unit: str | None = None,
) -> list[dict]:
	if not frappe.has_permission("Viewing Appointment", "read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	filters = {}
	if lead:
		filters["lead"] = lead
	if deal:
		filters["deal"] = deal
	if project:
		filters["project"] = project
	if unit:
		filters["unit"] = unit

	return frappe.get_all(
		"Viewing Appointment",
		filters=filters,
		fields=[
			"name", "appointment_date", "appointment_time", "status",
			"assigned_agent", "lead", "deal", "project", "unit",
			"feedback", "notes", "modified",
		],
		order_by="appointment_date desc, appointment_time desc",
	)


@frappe.whitelist()
def update_status(appointment_name: str, status: str, feedback: str | None = None) -> None:
	if not frappe.has_permission("Viewing Appointment", "write", appointment_name):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	if status not in ("Scheduled", "Completed", "No-Show", "Cancelled"):
		frappe.throw(_("Invalid status: {0}").format(status))

	appointment = frappe.get_doc("Viewing Appointment", appointment_name)
	appointment.status = status
	if feedback is not None:
		appointment.feedback = feedback
	appointment.save(ignore_permissions=True)
