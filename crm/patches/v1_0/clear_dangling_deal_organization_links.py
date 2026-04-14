"""Clear CRM Deal.organization values that don't resolve to a real CRM Organization.

Earlier versions of `CRMLead.create_organization()` returned a free-text string
from `CRM Lead.organization` without checking whether a matching CRM Organization
record existed. When `create_deal()` wrote that string into the Link field
`CRM Deal.organization`, the row could be saved (historically) but later fail
`_validate_links()` on any subsequent save.

This patch scrubs orphaned links so the affected rows become saveable again.
The company name is still readable on `CRM Deal.organization_name` (Data field),
which is populated by the normal field-copy in the lead-to-deal conversion.
"""

import frappe


def execute():
	if not frappe.db.table_exists("CRM Deal"):
		return

	meta = frappe.get_meta("CRM Deal")
	if not meta.has_field("organization"):
		return

	# Find deals whose organization link doesn't resolve.
	dangling_rows = frappe.db.sql(
		"""
		SELECT d.name, d.organization
		FROM `tabCRM Deal` d
		LEFT JOIN `tabCRM Organization` o ON o.name = d.organization
		WHERE d.organization IS NOT NULL
		  AND d.organization != ''
		  AND o.name IS NULL
		""",
		as_dict=True,
	)

	if not dangling_rows:
		return

	for row in dangling_rows:
		frappe.db.set_value(
			"CRM Deal",
			row.name,
			"organization",
			None,
			update_modified=False,
		)

	frappe.db.commit()
	print(f"[crm] Cleared orphaned organization link on {len(dangling_rows)} CRM Deal rows")
