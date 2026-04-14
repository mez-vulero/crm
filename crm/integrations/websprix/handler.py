import frappe
import requests
from frappe import _
from frappe.integrations.utils import create_request_log
from frappe.utils import strip_html_tags


def _get_settings():
	return frappe.get_single("CRM WebSprix Settings")


def _get_base_url():
	settings = _get_settings()
	return (settings.base_url or "").rstrip("/")


def _get_headers():
	return {"x-api-key": _get_settings().api_key}


@frappe.whitelist(allow_guest=True)
def handle_request(**kwargs):
	"""Webhook endpoint — WebSprix posts call status updates here."""
	validate_request()
	if not is_integration_enabled():
		return

	request_log = create_request_log(
		kwargs,
		request_description="WebSprix Call",
		service_name="WebSprix",
		request_headers=frappe.request.headers if frappe.request else {},
		is_remote_request=1,
	)

	try:
		request_log.status = "Completed"
		settings = _get_settings()
		if not settings.enabled:
			return

		call_payload = kwargs
		frappe.publish_realtime("websprix_call", call_payload)

		status = call_payload.get("CallStatus")
		if status == "free":
			return

		call_log = get_call_log(call_payload)
		if call_log:
			update_call_log(call_payload, call_log=call_log)
		else:
			create_call_log(
				call_id=call_payload.get("CallUUID"),
				from_number=call_payload.get("From"),
				to_number=call_payload.get("To"),
				medium="WebSprix",
				status=get_call_log_status(call_payload),
				agent=call_payload.get("AgentEmail"),
			)
	except Exception:
		request_log.status = "Failed"
		request_log.error = frappe.get_traceback()
		frappe.db.rollback()
		frappe.log_error(title="WebSprix handle_request")
		frappe.db.commit()
	finally:
		request_log.save(ignore_permissions=True)
		frappe.db.commit()


@frappe.whitelist()
def make_a_call(to_number: str, from_number: str | None = None, caller_id: str | None = None) -> dict:
	"""Initiate an outgoing call via the WebSprix REST API."""
	if not is_integration_enabled():
		frappe.throw(_("Please setup WebSprix integration"), title=_("Integration Not Enabled"))

	settings = _get_settings()
	endpoint = f"{_get_base_url()}/Account/{settings.customer_id}/Call/"

	user = frappe.session.user
	if not from_number:
		from_number = frappe.db.get_value("CRM Telephony Agent", {"user": user}, "mobile_no")

	if not caller_id:
		caller_id = frappe.db.get_value("CRM Telephony Agent", {"user": user}, "websprix_number")

	if not from_number:
		frappe.throw(
			_("You do not have a mobile number set in your Telephony Agent profile."),
			title=_("Mobile Number Missing"),
		)

	try:
		response = requests.post(
			endpoint,
			headers=_get_headers(),
			data={
				"from": caller_id or from_number,
				"to": to_number,
				"answer_url": _get_status_updater_url(),
			},
			timeout=15,
		)
		response.raise_for_status()
	except requests.exceptions.HTTPError:
		error_body = {}
		try:
			error_body = response.json() or {}
		except Exception:
			pass
		exc = error_body.get("error")
		if exc:
			# Strip any HTML the PBX may have wrapped around the error message.
			frappe.throw(strip_html_tags(str(exc)), title=_("WebSprix Exception"))
		frappe.throw(_("WebSprix call failed"), title=_("WebSprix Exception"))

	res = response.json() or {}
	call_payload = res.get("", {}) if isinstance(res.get(""), dict) else res
	create_call_log(
		call_id=call_payload.get("request_uuid") or call_payload.get("CallUUID"),
		from_number=from_number,
		to_number=to_number,
		medium="WebSprix",
		call_type="Outgoing",
		agent=user,
	)

	call_details = dict(res)
	call_details["CallUUID"] = call_details.get("request_uuid") or call_details.get("CallUUID") or ""
	return call_details


def _get_status_updater_url():
	from frappe.utils.data import get_url

	return get_url("api/method/crm.integrations.websprix.handler.handle_request")


def validate_request():
	"""Placeholder for webhook signature validation. Matches reference behaviour."""
	pass


@frappe.whitelist()
def is_integration_enabled():
	return frappe.db.get_single_value("CRM WebSprix Settings", "enabled", True)


def create_call_log(call_id, from_number, to_number, medium, agent, status="Ringing", call_type="Incoming"):
	"""Create a new CRM Call Log for a WebSprix call."""
	if call_id and frappe.db.exists("CRM Call Log", call_id):
		return frappe.get_doc("CRM Call Log", call_id)

	call_log = frappe.new_doc("CRM Call Log")
	call_log.id = call_id
	call_log.to = to_number
	call_log.medium = medium
	call_log.type = call_type
	call_log.status = status
	call_log.telephony_medium = "WebSprix"
	setattr(call_log, "from", from_number)

	if call_type == "Incoming":
		call_log.receiver = agent
	else:
		call_log.caller = agent

	call_log.save(ignore_permissions=True)
	frappe.db.commit()
	return call_log


def get_call_log(call_payload):
	"""Return an existing CRM Call Log matching the payload's CallUUID, if any."""
	call_log_id = call_payload.get("CallUUID")
	if call_log_id and frappe.db.exists("CRM Call Log", call_log_id):
		return frappe.get_doc("CRM Call Log", call_log_id)


def get_call_log_status(call_payload):
	"""Map a WebSprix webhook status code to a CRM Call Log status value."""
	status = (call_payload.get("CallStatus") or "").lower()
	mapping = {
		"completed": "Completed",
		"in-progress": "In Progress",
		"ringing": "Ringing",
		"initiating": "Initiated",
		"busy": "Busy",
		"no-answer": "No Answer",
		"failed": "Failed",
	}
	return mapping.get(status, "Initiated")


def update_call_log(call_payload, call_log=None):
	"""Update an existing call log with the latest webhook payload."""
	call_log = call_log or get_call_log(call_payload)
	if not call_log:
		return None

	try:
		call_log.status = get_call_log_status(call_payload)
		if call_payload.get("To"):
			call_log.to = call_payload.get("To")
		if call_payload.get("Duration") is not None:
			call_log.duration = call_payload.get("Duration") or 0
		if call_payload.get("RecordingUrl"):
			call_log.recording_url = call_payload.get("RecordingUrl")
		if call_payload.get("StartTime"):
			call_log.start_time = call_payload.get("StartTime")
		if call_payload.get("EndTime"):
			call_log.end_time = call_payload.get("EndTime")
		if call_payload.get("AgentEmail") and call_log.type == "Incoming":
			call_log.receiver = call_payload.get("AgentEmail")
		call_log.save(ignore_permissions=True)
		frappe.db.commit()
		return call_log
	except Exception:
		frappe.log_error(title="WebSprix update_call_log")
		frappe.db.commit()
		return None
