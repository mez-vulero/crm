# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt
import click
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from crm.fcrm.doctype.crm_dashboard.crm_dashboard import create_default_manager_dashboard
from crm.fcrm.doctype.crm_products.crm_products import create_product_details_script


def before_install():
	pass


def after_install(force=False):
	add_default_lead_statuses()
	add_default_deal_statuses()
	add_default_communication_statuses()
	add_default_fields_layout(force)
	add_property_setter()
	add_email_template_custom_fields()
	add_email_account_custom_field()
	add_default_industries()
	add_default_lead_sources()
	add_default_lost_reasons()
	add_standard_dropdown_items()
	add_default_scripts()
	create_default_manager_dashboard(force)
	create_assignment_rule_custom_fields()
	add_assignment_rule_property_setters()
	hide_organization_from_layouts()
	hide_company_name_from_contact_side_panel()
	add_real_estate_custom_fields()
	upgrade_real_estate_custom_fields()
	add_real_estate_financial_custom_fields()
	add_real_estate_sidebar_sections()
	update_real_estate_data_fields_layout()
	frappe.db.commit()


def add_default_lead_statuses():
	statuses = {
		"New": {
			"color": "gray",
			"type": "Open",
			"position": 1,
		},
		"Contacted": {
			"color": "orange",
			"type": "Ongoing",
			"position": 2,
		},
		"Nurture": {
			"color": "blue",
			"type": "Ongoing",
			"position": 3,
		},
		"Qualified": {
			"color": "green",
			"type": "Won",
			"position": 4,
		},
		"Converted": {
			"color": "teal",
			"type": "Won",
			"position": 5,
		},
		"Unqualified": {
			"color": "red",
			"type": "Lost",
			"position": 6,
		},
		"Junk": {
			"color": "purple",
			"type": "Lost",
			"position": 7,
		},
	}

	for status in statuses:
		if frappe.db.exists("CRM Lead Status", status):
			continue

		doc = frappe.new_doc("CRM Lead Status")
		doc.lead_status = status
		doc.color = statuses[status]["color"]
		doc.type = statuses[status]["type"]
		doc.position = statuses[status]["position"]
		doc.insert()


def add_default_deal_statuses():
	statuses = {
		"Qualification": {
			"color": "gray",
			"type": "Open",
			"probability": 10,
			"position": 1,
		},
		"Demo/Making": {
			"color": "orange",
			"type": "Ongoing",
			"probability": 25,
			"position": 2,
		},
		"Proposal/Quotation": {
			"color": "blue",
			"type": "Ongoing",
			"probability": 50,
			"position": 3,
		},
		"Negotiation": {
			"color": "yellow",
			"type": "Ongoing",
			"probability": 70,
			"position": 4,
		},
		"Ready to Close": {
			"color": "purple",
			"type": "Ongoing",
			"probability": 90,
			"position": 5,
		},
		"Won": {
			"color": "green",
			"type": "Won",
			"probability": 100,
			"position": 6,
		},
		"Lost": {
			"color": "red",
			"type": "Lost",
			"probability": 0,
			"position": 7,
		},
	}

	for status in statuses:
		if frappe.db.exists("CRM Deal Status", status):
			continue

		doc = frappe.new_doc("CRM Deal Status")
		doc.deal_status = status
		doc.color = statuses[status]["color"]
		doc.type = statuses[status]["type"]
		doc.probability = statuses[status]["probability"]
		doc.position = statuses[status]["position"]
		doc.insert()


def add_default_communication_statuses():
	statuses = ["Open", "Replied"]

	for status in statuses:
		if frappe.db.exists("CRM Communication Status", status):
			continue

		doc = frappe.new_doc("CRM Communication Status")
		doc.status = status
		doc.insert()


def add_default_fields_layout(force=False):
	quick_entry_layouts = {
		"CRM Lead-Quick Entry": {
			"doctype": "CRM Lead",
			"layout": '[{"name": "person_section", "columns": [{"name": "column_5jrk", "fields": ["salutation", "email"]}, {"name": "column_5CPV", "fields": ["first_name", "mobile_no"]}, {"name": "column_gXOy", "fields": ["last_name", "gender"]}]}, {"name": "organization_section", "columns": [{"name": "column_GHfX", "fields": ["territory"]}, {"name": "column_hXjS", "fields": ["website", "annual_revenue"]}, {"name": "column_RDNA", "fields": ["no_of_employees", "industry"]}]}, {"name": "lead_section", "columns": [{"name": "column_EO1H", "fields": ["status"]}, {"name": "column_RWBe", "fields": ["lead_owner"]}]}]',
		},
		"CRM Deal-Quick Entry": {
			"doctype": "CRM Deal",
			"layout": '[{"name": "organization_details_section", "editable": false, "columns": [{"name": "column_S3tQ", "fields": ["organization_name", "territory"]}, {"name": "column_KqV1", "fields": ["website", "annual_revenue"]}, {"name": "column_1r67", "fields": ["no_of_employees", "industry"]}]}, {"name": "contact_section", "hidden": true, "editable": false, "columns": [{"name": "column_CeXr", "fields": ["contact"]}, {"name": "column_yHbk", "fields": []}]}, {"name": "contact_details_section", "editable": false, "columns": [{"name": "column_ZTWr", "fields": ["salutation", "email"]}, {"name": "column_tabr", "fields": ["first_name", "mobile_no"]}, {"name": "column_Qjdx", "fields": ["last_name", "gender"]}]}, {"name": "deal_section", "columns": [{"name": "column_mdps", "fields": ["status"]}, {"name": "column_H40H", "fields": ["deal_owner"]}]}]',
		},
		"Contact-Quick Entry": {
			"doctype": "Contact",
			"layout": '[{"name": "salutation_section", "columns": [{"name": "column_eXks", "fields": ["salutation"]}]}, {"name": "full_name_section", "hideBorder": true, "columns": [{"name": "column_cSxf", "fields": ["first_name"]}, {"name": "column_yBc7", "fields": ["last_name"]}]}, {"name": "email_section", "hideBorder": true, "columns": [{"name": "column_tH3L", "fields": ["email_id"]}]}, {"name": "mobile_gender_section", "hideBorder": true, "columns": [{"name": "column_lrfI", "fields": ["mobile_no"]}, {"name": "column_Tx3n", "fields": ["gender"]}]}, {"name": "organization_section", "hideBorder": true, "columns": [{"name": "column_S0J8", "fields": ["company_name"]}]}, {"name": "designation_section", "hideBorder": true, "columns": [{"name": "column_bsO8", "fields": ["designation"]}]}, {"name": "address_section", "hideBorder": true, "columns": [{"name": "column_W3VY", "fields": ["address"]}]}]',
		},
		"Address-Quick Entry": {
			"doctype": "Address",
			"layout": '[{"name": "details_section", "columns": [{"name": "column_uSSG", "fields": ["address_title", "address_type", "address_line1", "address_line2", "city", "state", "country", "pincode"]}]}]',
		},
		"CRM Call Log-Quick Entry": {
			"doctype": "CRM Call Log",
			"layout": '[{"name":"details_section","columns":[{"name":"column_uMSG","fields":["type","from","duration"]},{"name":"column_wiZT","fields":["to","status","caller","receiver"]}]}]',
		},
	}

	sidebar_fields_layouts = {
		"CRM Lead-Side Panel": {
			"doctype": "CRM Lead",
			"layout": '[{"label": "Details", "name": "details_section", "opened": true, "columns": [{"name": "column_kl92", "fields": ["website", "territory", "industry", "job_title", "source", "lead_owner"]}]}, {"label": "Person", "name": "person_section", "opened": true, "columns": [{"name": "column_XmW2", "fields": ["salutation", "first_name", "last_name", "email", "mobile_no"]}]}]',
		},
		"CRM Deal-Side Panel": {
			"doctype": "CRM Deal",
			"layout": '[{"label": "Contacts", "name": "contacts_section", "opened": true, "editable": false, "contacts": []}, {"label": "Details", "name": "organization_section", "opened": true, "columns": [{"name": "column_na2Q", "fields": ["website", "territory", "annual_revenue", "close_date", "probability", "next_step", "deal_owner"]}]}]',
		},
		"Contact-Side Panel": {
			"doctype": "Contact",
			"layout": '[{"label": "Details", "name": "details_section", "opened": true, "columns": [{"name": "column_eIWl", "fields": ["salutation", "first_name", "last_name", "email_id", "mobile_no", "gender", "designation", "address"]}]}]',
		},
	}

	data_fields_layouts = {
		"CRM Lead-Data Fields": {
			"doctype": "CRM Lead",
			"layout": '[{"label": "Details", "name": "details_section", "opened": true, "columns": [{"name": "column_ZgLG", "fields": ["industry", "lead_owner"]}, {"name": "column_TbYq", "fields": ["website", "job_title"]}, {"name": "column_OKSX", "fields": ["territory", "source"]}]}, {"label": "Person", "name": "person_section", "opened": true, "columns": [{"name": "column_6c5g", "fields": ["salutation", "email"]}, {"name": "column_1n7Q", "fields": ["first_name", "mobile_no"]}, {"name": "column_cT6C", "fields": ["last_name"]}]}, {"label": "Property Interest", "name": "property_interest_data_section", "opened": true, "columns": [{"name": "column_re_lead_d1", "fields": ["re_interested_project", "re_preferred_unit_type"]}, {"name": "column_re_lead_d2", "fields": ["re_budget_min", "re_budget_max"]}, {"name": "column_re_lead_d3", "fields": ["re_preferred_floor"]}]}]',
		},
		"CRM Deal-Data Fields": {
			"doctype": "CRM Deal",
			"layout": '[{"name":"first_tab","sections":[{"label":"Details","name":"details_section","opened":true,"columns":[{"name":"column_z9XL","fields":["annual_revenue","next_step"]},{"name":"column_gM4w","fields":["website","closed_date","deal_owner"]},{"name":"column_gWmE","fields":["territory","probability"]}]},{"label":"Real Estate","name":"real_estate_data_section","opened":true,"columns":[{"name":"column_re_deal_d1","fields":["re_project","re_unit","re_unit_status","re_purchase_price"]},{"name":"column_re_deal_d2","fields":["re_reservation_date","re_contract_date","re_deed_date","re_mortgage_status"]},{"name":"column_re_deal_d3","fields":["re_commission_rate","re_commission_amount"]}]},{"label":"Payment Schedule","name":"payment_schedule_data_section","opened":true,"columns":[{"name":"column_re_ps","fields":["re_payment_schedule"]}],"hideLabel":false}]}]',
		},
	}

	for layout in quick_entry_layouts:
		if frappe.db.exists("CRM Fields Layout", layout):
			if force:
				frappe.delete_doc("CRM Fields Layout", layout)
			else:
				continue

		doc = frappe.new_doc("CRM Fields Layout")
		doc.type = "Quick Entry"
		doc.dt = quick_entry_layouts[layout]["doctype"]
		doc.layout = quick_entry_layouts[layout]["layout"]
		doc.insert()

	for layout in sidebar_fields_layouts:
		if frappe.db.exists("CRM Fields Layout", layout):
			if force:
				frappe.delete_doc("CRM Fields Layout", layout)
			else:
				continue

		doc = frappe.new_doc("CRM Fields Layout")
		doc.type = "Side Panel"
		doc.dt = sidebar_fields_layouts[layout]["doctype"]
		doc.layout = sidebar_fields_layouts[layout]["layout"]
		doc.insert()

	for layout in data_fields_layouts:
		if frappe.db.exists("CRM Fields Layout", layout):
			if force:
				frappe.delete_doc("CRM Fields Layout", layout)
			else:
				continue

		doc = frappe.new_doc("CRM Fields Layout")
		doc.type = "Data Fields"
		doc.dt = data_fields_layouts[layout]["doctype"]
		doc.layout = data_fields_layouts[layout]["layout"]
		doc.insert()


def add_property_setter():
	if not frappe.db.exists("Property Setter", {"name": "Contact-main-search_fields"}):
		doc = frappe.new_doc("Property Setter")
		doc.doctype_or_field = "DocType"
		doc.doc_type = "Contact"
		doc.property = "search_fields"
		doc.property_type = "Data"
		doc.value = "email_id"
		doc.insert()


def add_email_template_custom_fields():
	if not frappe.get_meta("Email Template").has_field("enabled"):
		click.secho("* Installing Custom Fields in Email Template")

		create_custom_fields(
			{
				"Email Template": [
					{
						"default": "0",
						"fieldname": "enabled",
						"fieldtype": "Check",
						"label": "Enabled",
						"insert_after": "",
					},
					{
						"fieldname": "reference_doctype",
						"fieldtype": "Link",
						"label": "Doctype",
						"options": "DocType",
						"insert_after": "enabled",
					},
				]
			}
		)

		frappe.clear_cache(doctype="Email Template")


def add_email_account_custom_field():
	if not frappe.get_meta("Email Account").has_field("create_lead_from_incoming_email"):
		click.secho("* Installing Custom Fields in Email Account")

		create_custom_fields(
			{
				"Email Account": [
					{
						"default": "0",
						"fieldname": "create_lead_from_incoming_email",
						"fieldtype": "Check",
						"label": "Create Lead from Incoming Emails",
						"description": "Automatically create a lead when an incoming email is received from an unknown contact",
						"insert_after": "create_contact",
					}
				]
			}
		)

		frappe.clear_cache(doctype="Email Account")


def add_default_industries():
	industries = [
		"Accounting",
		"Advertising",
		"Aerospace",
		"Agriculture",
		"Airline",
		"Apparel & Accessories",
		"Automotive",
		"Banking",
		"Biotechnology",
		"Broadcasting",
		"Brokerage",
		"Chemical",
		"Computer",
		"Consulting",
		"Consumer Products",
		"Cosmetics",
		"Defense",
		"Department Stores",
		"Education",
		"Electronics",
		"Energy",
		"Entertainment & Leisure, Executive Search",
		"Financial Services",
		"Food",
		"Beverage & Tobacco",
		"Grocery",
		"Health Care",
		"Internet Publishing",
		"Investment Banking",
		"Legal",
		"Manufacturing",
		"Motion Picture & Video",
		"Music",
		"Newspaper Publishers",
		"Online Auctions",
		"Pension Funds",
		"Pharmaceuticals",
		"Private Equity",
		"Publishing",
		"Real Estate",
		"Retail & Wholesale",
		"Securities & Commodity Exchanges",
		"Service",
		"Soap & Detergent",
		"Software",
		"Sports",
		"Technology",
		"Telecommunications",
		"Television",
		"Transportation",
		"Venture Capital",
	]

	for industry in industries:
		if frappe.db.exists("CRM Industry", industry):
			continue

		doc = frappe.new_doc("CRM Industry")
		doc.industry = industry
		doc.insert()


def add_default_lead_sources():
	lead_sources = [
		"Email",
		"Existing Customer",
		"Reference",
		"Advertisement",
		"Cold Calling",
		"Exhibition",
		"Supplier Reference",
		"Mass Mailing",
		"Customer's Vendor",
		"Campaign",
		"Walk In",
		"Facebook",
		"Website",
	]

	for source in lead_sources:
		if frappe.db.exists("CRM Lead Source", source):
			continue

		doc = frappe.new_doc("CRM Lead Source")
		doc.source_name = source
		doc.insert()


def add_default_lost_reasons():
	lost_reasons = [
		{
			"reason": "Pricing",
			"description": "The prospect found the pricing to be too high or not competitive.",
		},
		{"reason": "Competition", "description": "The prospect chose a competitor's product or service."},
		{
			"reason": "Budget Constraints",
			"description": "The prospect did not have the budget to proceed with the purchase.",
		},
		{
			"reason": "Missing Features",
			"description": "The prospect felt that the product or service was missing key features they needed.",
		},
		{
			"reason": "Long Sales Cycle",
			"description": "The sales process took too long, leading to loss of interest.",
		},
		{
			"reason": "No Decision-Maker",
			"description": "The prospect was not the decision-maker and could not proceed.",
		},
		{"reason": "Unresponsive Prospect", "description": "The prospect did not respond to follow-ups."},
		{"reason": "Poor Fit", "description": "The prospect was not a good fit for the product or service."},
		{"reason": "Other", "description": ""},
	]

	for reason in lost_reasons:
		if frappe.db.exists("CRM Lost Reason", reason["reason"]):
			continue

		doc = frappe.new_doc("CRM Lost Reason")
		doc.lost_reason = reason["reason"]
		doc.description = reason["description"]
		doc.insert()


def add_standard_dropdown_items():
	crm_settings = frappe.get_single("FCRM Settings")

	# don't add dropdown items if they're already present
	if crm_settings.dropdown_items:
		return

	crm_settings.dropdown_items = []

	for item in frappe.get_hooks("standard_dropdown_items"):
		crm_settings.append("dropdown_items", item)

	crm_settings.save()


def add_default_scripts():
	from crm.fcrm.doctype.fcrm_settings.fcrm_settings import create_forecasting_script

	for doctype in ["CRM Lead", "CRM Deal"]:
		create_product_details_script(doctype)
	create_forecasting_script()


def add_assignment_rule_property_setters():
	"""Add a property setter to the Assignment Rule DocType for assign_condition and unassign_condition."""

	default_fields = {
		"doctype": "Property Setter",
		"doctype_or_field": "DocField",
		"doc_type": "Assignment Rule",
		"property_type": "Data",
		"is_system_generated": 1,
	}

	if not frappe.db.exists("Property Setter", {"name": "Assignment Rule-assign_condition-depends_on"}):
		frappe.get_doc(
			{
				**default_fields,
				"name": "Assignment Rule-assign_condition-depends_on",
				"field_name": "assign_condition",
				"property": "depends_on",
				"value": "eval: !doc.assign_condition_json",
			}
		).insert()
	else:
		frappe.db.set_value(
			"Property Setter",
			{"name": "Assignment Rule-assign_condition-depends_on"},
			"value",
			"eval: !doc.assign_condition_json",
		)
	if not frappe.db.exists("Property Setter", {"name": "Assignment Rule-unassign_condition-depends_on"}):
		frappe.get_doc(
			{
				**default_fields,
				"name": "Assignment Rule-unassign_condition-depends_on",
				"field_name": "unassign_condition",
				"property": "depends_on",
				"value": "eval: !doc.unassign_condition_json",
			}
		).insert()
	else:
		frappe.db.set_value(
			"Property Setter",
			{"name": "Assignment Rule-unassign_condition-depends_on"},
			"value",
			"eval: !doc.unassign_condition_json",
		)


def create_assignment_rule_custom_fields():
	if not frappe.get_meta("Assignment Rule").has_field("assign_condition_json"):
		click.secho("* Installing Custom Fields in Assignment Rule")

		create_custom_fields(
			{
				"Assignment Rule": [
					{
						"description": "Autogenerated field by CRM App",
						"fieldname": "assign_condition_json",
						"fieldtype": "Code",
						"label": "Assign Condition JSON",
						"insert_after": "assign_condition",
						"depends_on": "eval: doc.assign_condition_json",
					},
					{
						"description": "Autogenerated field by CRM App",
						"fieldname": "unassign_condition_json",
						"fieldtype": "Code",
						"label": "Unassign Condition JSON",
						"insert_after": "unassign_condition",
						"depends_on": "eval: doc.unassign_condition_json",
					},
				],
			}
		)

		frappe.clear_cache(doctype="Assignment Rule")


def hide_organization_from_layouts():
	"""Remove organization field references from existing CRM Fields Layout records."""
	import json

	layout_names = [
		"CRM Lead-Quick Entry",
		"CRM Lead-Side Panel",
		"CRM Lead-Data Fields",
		"CRM Deal-Quick Entry",
		"CRM Deal-Side Panel",
		"CRM Deal-Data Fields",
	]

	for layout_name in layout_names:
		if not frappe.db.exists("CRM Fields Layout", layout_name):
			continue

		doc = frappe.get_doc("CRM Fields Layout", layout_name)
		if not doc.layout:
			continue

		layout = json.loads(doc.layout)
		changed = False

		def remove_org_from_sections(sections):
			nonlocal changed
			for section in sections:
				# Remove entire section if it only contains organization in a hidden section
				if section.get("hidden") and section.get("columns"):
					all_fields = []
					for col in section["columns"]:
						all_fields.extend(col.get("fields", []))
					if all_fields == ["organization"]:
						sections.remove(section)
						changed = True
						continue

				# Remove organization from field lists in columns
				for col in section.get("columns", []):
					fields = col.get("fields", [])
					if "organization" in fields:
						fields.remove("organization")
						changed = True

				# Rename "Organization Details" label to "Details"
				if section.get("label") == "Organization Details":
					section["label"] = "Details"
					changed = True

		# Handle tabbed structure (CRM Deal-Data Fields)
		if layout and isinstance(layout[0], dict) and "sections" in layout[0]:
			for tab in layout:
				remove_org_from_sections(tab.get("sections", []))
		else:
			remove_org_from_sections(layout)

		if changed:
			doc.layout = json.dumps(layout)
			doc.save(ignore_permissions=True)


def upgrade_real_estate_custom_fields():
	"""Patch CRM Lead.re_preferred_unit_type (Select \u2192 Link) and add fetch_from on
	CRM Deal.re_purchase_price for existing installations.

	Frappe forbids changing a Custom Field's fieldtype in place, so for the
	Select \u2192 Link migration we delete and recreate the field while preserving
	existing lead values (and backfilling matching CRM Unit Type rows).
	"""
	lead_field = "CRM Lead-re_preferred_unit_type"
	if frappe.db.exists("Custom Field", lead_field):
		cf = frappe.get_doc("Custom Field", lead_field)
		if cf.fieldtype != "Link" or cf.options != "CRM Unit Type":
			existing_data = frappe.db.sql(
				"""SELECT name, re_preferred_unit_type
				   FROM `tabCRM Lead`
				   WHERE re_preferred_unit_type IS NOT NULL
				     AND re_preferred_unit_type != ''""",
				as_dict=True,
			)

			for value in {row.re_preferred_unit_type for row in existing_data}:
				if not frappe.db.exists("CRM Unit Type", value):
					frappe.get_doc(
						{"doctype": "CRM Unit Type", "unit_type": value}
					).insert(ignore_permissions=True)

			insert_after = cf.insert_after
			frappe.delete_doc(
				"Custom Field", lead_field, ignore_permissions=True, force=True
			)
			frappe.clear_cache(doctype="CRM Lead")

			frappe.get_doc(
				{
					"doctype": "Custom Field",
					"dt": "CRM Lead",
					"fieldname": "re_preferred_unit_type",
					"label": "Preferred Unit Type",
					"fieldtype": "Link",
					"options": "CRM Unit Type",
					"insert_after": insert_after or "re_interested_project",
					"module": "FCRM",
				}
			).insert(ignore_permissions=True)

			# Re-write any values that the column drop/recreate may have wiped
			for row in existing_data:
				if frappe.db.exists("CRM Lead", row.name):
					frappe.db.set_value(
						"CRM Lead",
						row.name,
						"re_preferred_unit_type",
						row.re_preferred_unit_type,
						update_modified=False,
					)

	deal_field = "CRM Deal-re_purchase_price"
	if frappe.db.exists("Custom Field", deal_field):
		cf = frappe.get_doc("Custom Field", deal_field)
		changed = False
		if cf.fetch_from != "re_unit.base_price":
			cf.fetch_from = "re_unit.base_price"
			changed = True
		if not cf.fetch_if_empty:
			cf.fetch_if_empty = 1
			changed = True
		if changed:
			cf.save(ignore_permissions=True)


def hide_company_name_from_contact_side_panel():
	"""Strip company_name from the Contact Side Panel layout (idempotent)."""
	import json

	layout_name = "Contact-Side Panel"
	if not frappe.db.exists("CRM Fields Layout", layout_name):
		return

	doc = frappe.get_doc("CRM Fields Layout", layout_name)
	if not doc.layout:
		return

	layout = json.loads(doc.layout)
	changed = False

	for section in layout:
		# Drop a section that exists only to hold company_name
		if section.get("columns"):
			all_fields = []
			for col in section["columns"]:
				all_fields.extend(col.get("fields", []))
			if all_fields == ["company_name"]:
				layout.remove(section)
				changed = True
				continue

		for col in section.get("columns", []):
			fields = col.get("fields", [])
			if "company_name" in fields:
				fields.remove("company_name")
				changed = True

	if changed:
		doc.layout = json.dumps(layout)
		doc.save(ignore_permissions=True)


def add_real_estate_custom_fields():
	if frappe.get_meta("CRM Deal").has_field("re_project"):
		return

	click.secho("* Installing Real Estate Custom Fields on CRM Deal and CRM Lead")

	create_custom_fields(
		{
			"CRM Deal": [
				{
					"fieldname": "re_section_break",
					"fieldtype": "Section Break",
					"label": "Real Estate",
					"insert_after": "lost_notes",
				},
				{
					"fieldname": "re_project",
					"fieldtype": "Link",
					"label": "Project",
					"options": "Real Estate Project",
					"insert_after": "re_section_break",
				},
				{
					"fieldname": "re_unit",
					"fieldtype": "Link",
					"label": "Unit",
					"options": "Property Unit",
					"insert_after": "re_project",
				},
				{
					"fieldname": "re_unit_status",
					"fieldtype": "Data",
					"label": "Unit Status",
					"fetch_from": "re_unit.status",
					"read_only": 1,
					"insert_after": "re_unit",
				},
				{
					"fieldname": "re_column_break_01",
					"fieldtype": "Column Break",
					"insert_after": "re_unit_status",
				},
				{
					"fieldname": "re_purchase_price",
					"fieldtype": "Currency",
					"label": "Purchase Price",
					"options": "currency",
					"insert_after": "re_column_break_01",
					"fetch_from": "re_unit.base_price",
					"fetch_if_empty": 1,
				},
				{
					"fieldname": "re_reservation_date",
					"fieldtype": "Date",
					"label": "Reservation Date",
					"insert_after": "re_purchase_price",
				},
				{
					"fieldname": "re_contract_date",
					"fieldtype": "Date",
					"label": "Contract Date",
					"insert_after": "re_reservation_date",
				},
				{
					"fieldname": "re_dates_section",
					"fieldtype": "Section Break",
					"insert_after": "re_contract_date",
				},
				{
					"fieldname": "re_deed_date",
					"fieldtype": "Date",
					"label": "Deed / Transfer Date",
					"insert_after": "re_dates_section",
				},
				{
					"fieldname": "re_mortgage_status",
					"fieldtype": "Select",
					"label": "Mortgage Status",
					"options": "Not Applicable\nPending\nApproved\nRejected",
					"default": "Not Applicable",
					"insert_after": "re_deed_date",
				},
				{
					"fieldname": "re_column_break_02",
					"fieldtype": "Column Break",
					"insert_after": "re_mortgage_status",
				},
				{
					"fieldname": "re_commission_rate",
					"fieldtype": "Percent",
					"label": "Commission %",
					"insert_after": "re_column_break_02",
				},
				{
					"fieldname": "re_commission_amount",
					"fieldtype": "Currency",
					"label": "Commission Amount",
					"options": "currency",
					"read_only": 1,
					"insert_after": "re_commission_rate",
				},
				{
					"fieldname": "re_payment_schedule_section",
					"fieldtype": "Section Break",
					"label": "Payment Schedule",
					"insert_after": "re_commission_amount",
				},
				{
					"fieldname": "re_payment_schedule",
					"fieldtype": "Table",
					"label": "Payment Schedule",
					"options": "Payment Schedule",
					"insert_after": "re_payment_schedule_section",
				},
			],
			"CRM Lead": [
				{
					"fieldname": "re_section_break",
					"fieldtype": "Section Break",
					"label": "Property Interest",
					"insert_after": "lost_notes",
				},
				{
					"fieldname": "re_interested_project",
					"fieldtype": "Link",
					"label": "Interested In",
					"options": "Real Estate Project",
					"insert_after": "re_section_break",
				},
				{
					"fieldname": "re_preferred_unit_type",
					"fieldtype": "Link",
					"label": "Preferred Unit Type",
					"options": "CRM Unit Type",
					"insert_after": "re_interested_project",
				},
				{
					"fieldname": "re_column_break_01",
					"fieldtype": "Column Break",
					"insert_after": "re_preferred_unit_type",
				},
				{
					"fieldname": "re_budget_min",
					"fieldtype": "Currency",
					"label": "Min Budget",
					"options": "currency",
					"insert_after": "re_column_break_01",
				},
				{
					"fieldname": "re_budget_max",
					"fieldtype": "Currency",
					"label": "Max Budget",
					"options": "currency",
					"insert_after": "re_budget_min",
				},
				{
					"fieldname": "re_preferred_floor",
					"fieldtype": "Int",
					"label": "Preferred Floor",
					"insert_after": "re_budget_max",
				},
			],
		}
	)

	frappe.clear_cache(doctype="CRM Deal")
	frappe.clear_cache(doctype="CRM Lead")


def add_real_estate_financial_custom_fields():
	if frappe.get_meta("CRM Deal").has_field("re_total_collected"):
		return

	click.secho("* Installing Real Estate Financial Custom Fields on CRM Deal")

	create_custom_fields(
		{
			"CRM Deal": [
				{
					"fieldname": "re_financial_section",
					"fieldtype": "Section Break",
					"label": "Financial Summary",
					"insert_after": "re_payment_schedule",
				},
				{
					"fieldname": "re_total_collected",
					"fieldtype": "Currency",
					"label": "Total Collected",
					"options": "currency",
					"read_only": 1,
					"insert_after": "re_financial_section",
				},
				{
					"fieldname": "re_outstanding_amount",
					"fieldtype": "Currency",
					"label": "Outstanding",
					"options": "currency",
					"read_only": 1,
					"insert_after": "re_total_collected",
				},
				{
					"fieldname": "re_financial_column_break",
					"fieldtype": "Column Break",
					"insert_after": "re_outstanding_amount",
				},
				{
					"fieldname": "re_payment_status",
					"fieldtype": "Select",
					"label": "Payment Status",
					"options": "Not Started\nIn Progress\nFully Paid\nOverdue",
					"read_only": 1,
					"insert_after": "re_financial_column_break",
				},
				{
					"fieldname": "re_total_commission",
					"fieldtype": "Currency",
					"label": "Total Commission Payable",
					"options": "currency",
					"read_only": 1,
					"insert_after": "re_payment_status",
				},
			],
		}
	)

	frappe.clear_cache(doctype="CRM Deal")


def add_real_estate_sidebar_sections():
	import json

	lead_section = {
		"label": "Property Interest",
		"name": "property_interest_section",
		"opened": True,
		"columns": [
			{
				"name": "column_re_lead",
				"fields": [
					"re_interested_project",
					"re_preferred_unit_type",
					"re_budget_min",
					"re_budget_max",
					"re_preferred_floor",
				],
			}
		],
	}

	deal_section = {
		"label": "Property",
		"name": "property_section",
		"opened": True,
		"columns": [
			{
				"name": "column_re_deal",
				"fields": [
					"re_project",
					"re_unit",
					"re_unit_status",
					"re_purchase_price",
					"re_reservation_date",
					"re_contract_date",
					"re_deed_date",
					"re_mortgage_status",
					"re_commission_rate",
					"re_commission_amount",
				],
			}
		],
	}

	deal_financial_section = {
		"label": "Financial",
		"name": "financial_section",
		"opened": True,
		"columns": [
			{
				"name": "column_re_fin",
				"fields": [
					"re_total_collected",
					"re_outstanding_amount",
					"re_payment_status",
					"re_total_commission",
				],
			}
		],
	}

	_append_sidebar_section("CRM Lead", lead_section)
	_append_sidebar_section("CRM Deal", deal_section)
	_append_sidebar_section("CRM Deal", deal_financial_section)


def _append_sidebar_section(doctype, section):
	import json

	layout_name = f"{doctype}-Side Panel"
	if not frappe.db.exists("CRM Fields Layout", layout_name):
		return

	doc = frappe.get_doc("CRM Fields Layout", layout_name)
	layout = json.loads(doc.layout) if doc.layout else []

	if any(s.get("name") == section["name"] for s in layout):
		return

	layout.append(section)
	doc.layout = json.dumps(layout)
	doc.save(ignore_permissions=True)


def update_real_estate_data_fields_layout():
	import json

	# Update CRM Deal Data Fields: remove Products, add Real Estate
	_update_data_fields_layout(
		"CRM Deal",
		sections_to_remove=["section_jHhQ", "section_WNOQ"],
		sections_to_add=[
			{
				"label": "Real Estate",
				"name": "real_estate_data_section",
				"opened": True,
				"columns": [
					{
						"name": "column_re_deal_d1",
						"fields": [
							"re_project",
							"re_unit",
							"re_unit_status",
							"re_purchase_price",
						],
					},
					{
						"name": "column_re_deal_d2",
						"fields": [
							"re_reservation_date",
							"re_contract_date",
							"re_deed_date",
							"re_mortgage_status",
						],
					},
					{
						"name": "column_re_deal_d3",
						"fields": [
							"re_commission_rate",
							"re_commission_amount",
						],
					},
				],
			},
			{
				"label": "Payment Schedule",
				"name": "payment_schedule_data_section",
				"opened": True,
				"columns": [
					{
						"name": "column_re_ps",
						"fields": ["re_payment_schedule"],
					}
				],
				"hideLabel": False,
			},
			{
				"label": "Financial Summary",
				"name": "financial_data_section",
				"opened": True,
				"columns": [
					{
						"name": "column_re_fin_d1",
						"fields": [
							"re_total_collected",
							"re_outstanding_amount",
						],
					},
					{
						"name": "column_re_fin_d2",
						"fields": [
							"re_payment_status",
							"re_total_commission",
						],
					},
				],
			},
		],
	)

	# Update CRM Lead Data Fields: add Property Interest
	_update_data_fields_layout(
		"CRM Lead",
		sections_to_remove=[],
		sections_to_add=[
			{
				"label": "Property Interest",
				"name": "property_interest_data_section",
				"opened": True,
				"columns": [
					{
						"name": "column_re_lead_d1",
						"fields": [
							"re_interested_project",
							"re_preferred_unit_type",
						],
					},
					{
						"name": "column_re_lead_d2",
						"fields": [
							"re_budget_min",
							"re_budget_max",
						],
					},
					{
						"name": "column_re_lead_d3",
						"fields": [
							"re_preferred_floor",
						],
					},
				],
			},
		],
	)


def _update_data_fields_layout(doctype, sections_to_remove, sections_to_add):
	import json

	layout_name = f"{doctype}-Data Fields"
	if not frappe.db.exists("CRM Fields Layout", layout_name):
		return

	doc = frappe.get_doc("CRM Fields Layout", layout_name)
	layout = json.loads(doc.layout) if doc.layout else []

	changed = False

	# Deal uses a tabbed structure: [{name: "first_tab", sections: [...]}]
	# Lead uses a flat structure: [{label: "Details", ...}, ...]
	is_tabbed = layout and isinstance(layout[0], dict) and "sections" in layout[0]

	if is_tabbed:
		sections = layout[0].get("sections", [])
	else:
		sections = layout

	# Remove specified sections
	for section_name in sections_to_remove:
		original_len = len(sections)
		sections[:] = [s for s in sections if s.get("name") != section_name]
		if len(sections) != original_len:
			changed = True

	# Add new sections if not already present
	for section in sections_to_add:
		if not any(s.get("name") == section["name"] for s in sections):
			sections.append(section)
			changed = True

	if changed:
		if is_tabbed:
			layout[0]["sections"] = sections
		else:
			layout = sections
		doc.layout = json.dumps(layout)
		doc.save(ignore_permissions=True)
