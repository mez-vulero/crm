import frappe
from frappe.model.document import Document


class CRMWebSprixSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		api_key: DF.Data | None
		base_url: DF.Data | None
		customer_id: DF.Data | None
		enabled: DF.Check
		organization_id: DF.Data | None
		record_call: DF.Check
		ringtone: DF.Attach | None
	# end: auto-generated types

	def validate(self):
		if self.enabled and not self.base_url:
			frappe.throw("Base URL is required when WebSprix is enabled")
