from frappe.model.document import Document


class CRMUnitType(Document):
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		unit_type: DF.Data

	pass
