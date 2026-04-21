from frappe.model.document import Document


class CRMPropertyAmenity(Document):
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amenity: DF.Data

	pass
