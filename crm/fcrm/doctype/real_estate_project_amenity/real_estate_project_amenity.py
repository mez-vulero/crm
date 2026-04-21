from frappe.model.document import Document


class RealEstateProjectAmenity(Document):
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amenity: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data

	pass
