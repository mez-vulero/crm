from frappe.model.document import Document


class CRMProjectType(Document):
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		project_type: DF.Data

	pass
