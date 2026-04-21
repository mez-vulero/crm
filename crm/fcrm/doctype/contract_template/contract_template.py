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
		amenities = ", ".join(
			row.amenity for row in (project_doc.get("amenities") or []) if row.amenity
		) if project_doc else ""
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
			"project_type": project_doc.get("project_type", ""),
			"number_of_stories": project_doc.get("number_of_stories", ""),
			"gross_building_area": project_doc.get("gross_building_area", ""),
			"total_land_area": project_doc.get("total_land_area", ""),
			"project_parking_spaces": project_doc.get("parking_spaces", ""),
			"elevators": project_doc.get("elevators", ""),
			"amenities": amenities,
			"unit_type": unit_doc.get("unit_type", ""),
			"bedrooms": unit_doc.get("bedrooms", ""),
			"bathrooms": unit_doc.get("bathrooms", ""),
			"kitchen_count": unit_doc.get("kitchen_count", ""),
			"kitchen_layout": unit_doc.get("kitchen_layout", ""),
			"has_laundry_room": "Yes" if unit_doc.get("has_laundry_room") else "No",
			"balcony_count": unit_doc.get("balcony_count", ""),
			"balcony_size_sqm": unit_doc.get("balcony_size_sqm", ""),
			"maid_room": "Yes" if unit_doc.get("maid_room") else "No",
			"storage_room": "Yes" if unit_doc.get("storage_room") else "No",
			"unit_parking_spaces": unit_doc.get("unit_parking_spaces", ""),
			"furnishing": unit_doc.get("furnishing", ""),
			"ceiling_height_m": unit_doc.get("ceiling_height_m", ""),
			"view_direction": unit_doc.get("view_direction", ""),
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
			"project_type": "Residential",
			"number_of_stories": "12",
			"gross_building_area": "8,500",
			"total_land_area": "3,200",
			"project_parking_spaces": "150",
			"elevators": "4",
			"amenities": "Swimming Pool, Gym, 24/7 Security, Covered Parking",
			"unit_type": "2BR",
			"bedrooms": "2",
			"bathrooms": "2",
			"kitchen_count": "1",
			"kitchen_layout": "Open",
			"has_laundry_room": "Yes",
			"balcony_count": "1",
			"balcony_size_sqm": "8",
			"maid_room": "No",
			"storage_room": "Yes",
			"unit_parking_spaces": "1",
			"furnishing": "Semi-Furnished",
			"ceiling_height_m": "3.0",
			"view_direction": "Sea",
		}

	header = frappe.render_template(template.header_html or "", context)
	body = frappe.render_template(template.body, context)
	footer = frappe.render_template(template.footer_html or "", context)

	return f"{header}{body}{footer}"
