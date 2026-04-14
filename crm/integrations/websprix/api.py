import hashlib
import re
import uuid

import frappe
import requests
from dateutil.parser import parse
from frappe import _

from crm.integrations.api import get_contact_by_phone_number

QUEUE_CACHE_KEY = "websprix_queue_status"


@frappe.whitelist()
def fetch_all_call_logs() -> dict:
	"""Run incoming + outgoing + missed call-log sync for the current user.

	Used by the manual "Sync Call Logs" button in the Call Logs page.
	Returns a per-direction summary so the UI can show what happened.
	"""
	if not frappe.has_permission("CRM Call Log", "create"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	results = {
		"incoming": _safe_run(fetch_and_process_incoming_call_logs),
		"outgoing": _safe_run(fetch_and_process_outgoing_call_logs),
		"missed": _safe_run(fetch_and_process_missed_call_logs),
	}
	return results


def _safe_run(fn):
	"""Invoke a fetch function, capture exceptions, return a status dict."""
	try:
		return fn() or {"status": "success"}
	except Exception as e:
		frappe.log_error(str(e), f"WebSprix {fn.__name__}")
		return {"status": "error", "message": str(e)}


def sync_call_logs_for_all_agents():
	"""Scheduler entry point: pull call logs from WebSprix for every enabled agent.

	Iterates over CRM Telephony Agent rows where the WebSprix flag is on, and
	runs the three fetchers under each agent's user context so the existing
	per-user queries (which key off `frappe.session.user`) work unchanged.
	Skips silently when WebSprix integration is disabled.
	"""
	if not frappe.db.get_single_value("CRM WebSprix Settings", "enabled"):
		return

	agents = frappe.get_all(
		"CRM Telephony Agent",
		filters={"websprix": 1},
		fields=["user", "websprix_number"],
	)

	original_user = frappe.session.user
	for agent in agents:
		if not agent.websprix_number:
			continue
		try:
			frappe.set_user(agent.user)
			_safe_run(fetch_and_process_incoming_call_logs)
			_safe_run(fetch_and_process_outgoing_call_logs)
			_safe_run(fetch_and_process_missed_call_logs)
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"WebSprix sync_call_logs_for_all_agents [{agent.user}]")
		finally:
			frappe.set_user(original_user)


def _get_settings():
	"""Return the CRM WebSprix Settings single document."""
	return frappe.get_single("CRM WebSprix Settings")


def _get_base_url():
	"""Return the configured base URL for the WebSprix PBX REST API."""
	settings = _get_settings()
	return (settings.base_url or "").rstrip("/")


def _get_headers():
	"""Return the auth headers required by the WebSprix API."""
	settings = _get_settings()
	return {"x-api-key": settings.api_key}


@frappe.whitelist()
def get_user_settings():
	"""Fetch SIP connection details (SIP server, username, password) for the current user."""
	user = frappe.session.user
	agent = frappe.db.get_value("CRM Telephony Agent", user, "websprix_number")
	if not agent:
		return None

	settings = _get_settings()
	url = f"{_get_base_url()}/onboard//get_ip_info/{settings.organization_id}/{agent}/1"

	try:
		resp = requests.get(url, headers=_get_headers(), timeout=10)
		if resp.status_code in [200, 201]:
			return resp.json()
	except requests.exceptions.RequestException as e:
		frappe.log_error(str(e), "WebSprix get_user_settings")
	return None


@frappe.whitelist()
def fetch_users_to_transfer():
	"""Return the list of organization users available for call transfer."""
	settings = _get_settings()
	url = f"{_get_base_url()}/cust_ext/{settings.organization_id}/cust"

	try:
		resp = requests.get(url, headers=_get_headers(), timeout=10)
		if resp.status_code in [200, 201]:
			return resp.json()
	except requests.exceptions.RequestException as e:
		frappe.log_error(str(e), "WebSprix fetch_users_to_transfer")
	return None


@frappe.whitelist()
def get_deal_lead_or_contact_from_number(phone_number: str) -> dict:
	"""Get contact, lead or deal from the given phone number."""
	contact = get_contact_by_phone_number(phone_number)

	if contact.get("name"):
		doctype = "Contact"
		docname = contact.get("name")

		if contact.get("lead"):
			doctype = "CRM Lead"
			docname = contact.get("lead")
		elif contact.get("deal"):
			doctype = "CRM Deal"
			docname = contact.get("deal")

		return {
			"docname": docname,
			"doctype": doctype,
			"mobile_no": contact.get("mobile_no"),
			"full_name": contact.get("full_name"),
			"user_link": f"/crm/{frappe.scrub(doctype).replace('crm_', '')}s/{docname}",
		}

	return {
		"docname": None,
		"doctype": None,
		"mobile_no": None,
		"full_name": None,
		"user_link": None,
	}


@frappe.whitelist()
def get_contact_info(phone_number: str) -> dict:
	return get_deal_lead_or_contact_from_number(phone_number)


@frappe.whitelist()
def queue_status() -> dict:
	"""Return the queue id configured for the user and whether they have joined."""
	user = frappe.session.user
	queue_id = frappe.db.get_value("CRM Telephony Agent", user, "websprix_queue_id")
	joined = frappe.cache().hget(QUEUE_CACHE_KEY, user) == "joined"
	return {"queue_id": queue_id, "joined": joined}


def _require_queue_config(user: str) -> tuple[str, str]:
	"""Ensure the user has both extension and queue id configured."""
	if not frappe.db.exists("CRM Telephony Agent", user):
		frappe.throw(
			_("You don't have a Telephony Agent profile. Ask a manager to create one."),
			title=_("Telephony Agent Not Configured"),
		)

	agent = frappe.db.get_value(
		"CRM Telephony Agent",
		user,
		["websprix_number", "websprix_queue_id", "websprix"],
		as_dict=True,
	)

	if not agent.get("websprix"):
		frappe.throw(
			_("WebSprix is not enabled on your Telephony Agent profile. Enable it in Settings → Telephony."),
			title=_("WebSprix Not Enabled"),
		)

	if not agent.get("websprix_number"):
		frappe.throw(
			_("Your WebSprix extension number is not set. Configure it in Settings → Telephony."),
			title=_("WebSprix Number Missing"),
		)

	if not agent.get("websprix_queue_id"):
		frappe.throw(
			_("Your WebSprix Queue ID is not set. Configure it in Settings → Telephony."),
			title=_("WebSprix Queue Not Configured"),
		)

	return agent["websprix_number"], agent["websprix_queue_id"]


@frappe.whitelist()
def join_queue() -> dict:
	"""Join the WebSprix queue configured for the current user."""
	user = frappe.session.user
	extension, queue_id = _require_queue_config(user)

	settings = _get_settings()
	url = f"{_get_base_url()}/queue/join/{settings.organization_id}/{queue_id}/{extension}"

	try:
		response = requests.post(url, headers=_get_headers(), timeout=10)
		response.raise_for_status()
	except requests.exceptions.Timeout:
		frappe.throw(
			_("WebSprix did not respond in time. Please try again."),
			title=_("Queue Join Failed"),
		)
	except requests.exceptions.HTTPError as e:
		frappe.log_error(
			f"{e}\nStatus: {getattr(e.response, 'status_code', '?')}\nBody: {getattr(e.response, 'text', '')}",
			"WebSprix join_queue",
		)
		frappe.throw(
			_("WebSprix rejected the join request ({0}).").format(
				getattr(e.response, "status_code", "error")
			),
			title=_("Queue Join Failed"),
		)
	except requests.exceptions.RequestException as e:
		frappe.log_error(str(e), "WebSprix join_queue")
		frappe.throw(
			_("Could not reach WebSprix. Check your network and the Base URL in settings."),
			title=_("Queue Join Failed"),
		)

	frappe.cache().hset(QUEUE_CACHE_KEY, user, "joined")
	return {"joined": True, "queue_id": queue_id}


@frappe.whitelist()
def leave_queue() -> dict:
	"""Leave the WebSprix queue configured for the current user."""
	user = frappe.session.user
	extension, queue_id = _require_queue_config(user)

	settings = _get_settings()
	url = f"{_get_base_url()}/queue/leave/{settings.organization_id}/{queue_id}/{extension}"

	try:
		response = requests.post(url, headers=_get_headers(), timeout=10)
		response.raise_for_status()
	except requests.exceptions.Timeout:
		frappe.throw(
			_("WebSprix did not respond in time. Please try again."),
			title=_("Queue Leave Failed"),
		)
	except requests.exceptions.HTTPError as e:
		frappe.log_error(
			f"{e}\nStatus: {getattr(e.response, 'status_code', '?')}\nBody: {getattr(e.response, 'text', '')}",
			"WebSprix leave_queue",
		)
		frappe.throw(
			_("WebSprix rejected the leave request ({0}).").format(
				getattr(e.response, "status_code", "error")
			),
			title=_("Queue Leave Failed"),
		)
	except requests.exceptions.RequestException as e:
		frappe.log_error(str(e), "WebSprix leave_queue")
		frappe.throw(
			_("Could not reach WebSprix. Check your network and the Base URL in settings."),
			title=_("Queue Leave Failed"),
		)

	frappe.cache().hdel(QUEUE_CACHE_KEY, user)
	return {"joined": False, "queue_id": queue_id}


@frappe.whitelist()
def get_queue_settings() -> dict:
	"""Return DTMF codes for join/leave queue actions for the current user."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("You must be logged in to access this method"), frappe.PermissionError)

	agent = frappe.db.get_value(
		"CRM Telephony Agent",
		user,
		["websprix_number", "websprix_queue_id"],
		as_dict=True,
	)
	if not agent:
		return {}
	return {
		"extension": agent.websprix_number,
		"queue_id": agent.websprix_queue_id,
	}


def _get_user_queue_interface():
	"""Build the `{customer_id}S{extension}` interface string used by queue APIs."""
	user = frappe.session.user
	agent = frappe.db.get_value(
		"CRM Telephony Agent",
		{"user": user},
		["websprix_number", "websprix_queue_id"],
		as_dict=True,
	)
	if not agent:
		return None, None

	settings = _get_settings()
	interface = f"{settings.customer_id}S{agent.websprix_number}"
	return agent, interface


@frappe.whitelist()
def add_to_queue() -> dict:
	"""Add the current agent to the configured queue."""
	agent, interface = _get_user_queue_interface()
	if not agent:
		return {"status": "error", "message": "Settings not found for user"}

	settings = _get_settings()
	url = f"{_get_base_url()}/member/{settings.customer_id}/add"

	body = {"queue_name": agent.websprix_queue_id, "interface": interface}
	try:
		response = requests.post(url, json=body, headers=_get_headers(), timeout=10)
		if response.status_code in [200, 201]:
			return {"status": "success", "message": "added"}
		frappe.log_error(
			f"Failed to add to queue: {response.status_code} - {response.text}",
			"WebSprix add_to_queue",
		)
		return {
			"status": "error",
			"message": "Failed to add to queue",
			"details": response.text,
		}
	except requests.exceptions.RequestException as e:
		frappe.log_error(str(e), "WebSprix add_to_queue")
		return {"status": "error", "message": "Failed to add to queue due to request error"}


@frappe.whitelist()
def remove_from_queue() -> dict:
	"""Remove the current agent from the configured queue."""
	agent, interface = _get_user_queue_interface()
	if not agent:
		return {"status": "error", "message": "Settings not found for user"}

	settings = _get_settings()
	url = f"{_get_base_url()}/member/{settings.customer_id}/remove"

	body = {"queue_name": agent.websprix_queue_id, "interface": interface}
	try:
		response = requests.delete(url, json=body, headers=_get_headers(), timeout=10)
		if response.status_code in [200, 201]:
			return {"status": "success", "message": "removed"}
		frappe.log_error(
			f"Failed to remove from queue: {response.status_code} - {response.text}",
			"WebSprix remove_from_queue",
		)
		return {
			"status": "error",
			"message": "Failed to remove from queue",
			"details": response.text,
		}
	except requests.exceptions.RequestException as e:
		frappe.log_error(str(e), "WebSprix remove_from_queue")
		return {"status": "error", "message": "Failed to remove from queue due to request error"}


@frappe.whitelist()
def get_queue_status() -> dict:
	"""Report whether the current agent is a member of their configured queue."""
	agent, interface = _get_user_queue_interface()
	if not agent:
		return {"status": "error", "message": "Settings not found for user"}

	settings = _get_settings()
	url = f"{_get_base_url()}/member/{settings.customer_id}/queues_for_agent?interface={interface}"

	try:
		response = requests.get(url, headers=_get_headers(), timeout=10)
		if response.status_code not in [200, 201]:
			frappe.log_error(
				f"Failed to fetch queues: {response.status_code} - {response.text}",
				"WebSprix get_queue_status",
			)
			return {
				"status": "error",
				"message": "Failed to fetch queue status",
				"details": response.text,
			}

		queues = response.json()
		for queue in queues.get("result", []):
			if queue.get("full_queue_name") == agent.websprix_queue_id:
				return {"status": "success", "is_member": queue.get("is_member")}
		return {"status": "error", "message": "Queue not found for the agent"}
	except requests.exceptions.RequestException as e:
		frappe.log_error(str(e), "WebSprix get_queue_status")
		return {"status": "error", "message": "Failed to fetch queue status due to request error"}


@frappe.whitelist()
def fetch_and_process_incoming_call_logs() -> dict:
	"""Fetch incoming call logs from WebSprix and sync into CRM Call Log."""
	user = frappe.session.user
	agent = frappe.db.get_value(
		"CRM Telephony Agent",
		{"user": user},
		["websprix_number"],
		as_dict=True,
	)
	if not agent:
		return {"status": "error", "message": "Settings not found for the current user"}

	settings = _get_settings()
	url = f"{_get_base_url()}/cust_ext/{settings.organization_id}/call_logs/{agent.websprix_number}?dir=in"

	try:
		response = requests.get(url, headers=_get_headers(), timeout=30)
		if response.status_code not in [200, 201]:
			frappe.log_error(
				f"Failed to fetch incoming calls: {response.status_code} - {response.text}",
				"WebSprix fetch_and_process_incoming_call_logs",
			)
			return {"status": "error", "message": "Failed to fetch calls", "details": response.text}

		call_logs = response.json() or {}
		sorted_logs = sort_logs_by_date(call_logs.get("result", []))
		for log in sorted_logs:
			_create_incoming_call_log(log=log, user_link=user)

		frappe.db.commit()
		return {"status": "success", "message": "Call logs processed successfully"}
	except requests.exceptions.RequestException as e:
		frappe.log_error(str(e), "WebSprix fetch_and_process_incoming_call_logs")
		return {"status": "error", "message": "API request failed", "details": str(e)}


def _create_incoming_call_log(log, user_link=None, off_hour=False):
	"""Insert a CRM Call Log for an incoming call from the WebSprix export."""
	try:
		if frappe.db.exists("CRM Call Log", log.get("id")):
			return

		if not off_hour:
			new_call_log = {
				"doctype": "CRM Call Log",
				"telephony_medium": "WebSprix",
				"type": "Incoming",
				"id": log["id"],
				"from": format_phone_number(log["src"]),
				"to": log["dst"],
				"receiver": user_link,
				"duration": log.get("duration") or 0,
				"recording_url": log.get("recording_url") or "",
				"status": _map_log_status(log.get("disposition")),
				"start_time": log.get("created_at"),
			}
		else:
			unique_id = str(uuid.uuid4())
			short_id = hashlib.sha256(unique_id.encode()).hexdigest()[:10]
			new_call_log = {
				"doctype": "CRM Call Log",
				"telephony_medium": "WebSprix",
				"id": short_id,
				"type": "Incoming",
				"from": log.get("phone"),
				"status": "No Answer",
				"start_time": log.get("created_at"),
			}

		frappe.get_doc(new_call_log).insert(ignore_permissions=True)
	except Exception as e:
		frappe.log_error(str(e), "WebSprix _create_incoming_call_log")


@frappe.whitelist()
def fetch_and_process_outgoing_call_logs() -> dict:
	"""Fetch outgoing call logs from WebSprix and sync into CRM Call Log."""
	user = frappe.session.user
	agent = frappe.db.get_value(
		"CRM Telephony Agent",
		{"user": user},
		["websprix_number"],
		as_dict=True,
	)
	if not agent:
		return {"status": "error", "message": "Settings not found for the current user"}

	settings = _get_settings()
	url = f"{_get_base_url()}/cust_ext/{settings.organization_id}/call_logs/{agent.websprix_number}?dir=out"

	try:
		response = requests.get(url, headers=_get_headers(), timeout=30)
		if response.status_code not in [200, 201]:
			frappe.log_error(
				f"Failed to fetch outgoing calls: {response.status_code} - {response.text}",
				"WebSprix fetch_and_process_outgoing_call_logs",
			)
			return {"status": "error", "message": "Failed to fetch calls", "details": response.text}

		call_logs = response.json() or {}
		for log in call_logs.get("result", []):
			call_id = log.get("id")
			if not call_id or frappe.db.exists("CRM Call Log", call_id):
				continue

			start_date = None
			if log.get("created_at"):
				try:
					start_date = parse(log["created_at"]).replace(tzinfo=None)
				except (ValueError, TypeError):
					start_date = log["created_at"]

			new_call_log = {
				"doctype": "CRM Call Log",
				"telephony_medium": "WebSprix",
				"type": "Outgoing",
				"id": call_id,
				"from": log.get("src"),
				"to": format_phone_number(log.get("dst", "")),
				"caller": user,
				"duration": log.get("duration") or 0,
				"status": _map_log_status(log.get("disposition")),
				"recording_url": log.get("recording_url") or "",
				"start_time": start_date,
			}
			frappe.get_doc(new_call_log).insert(ignore_permissions=True)

		frappe.db.commit()
		return {"status": "success", "message": "Call logs processed successfully"}
	except requests.exceptions.RequestException as e:
		frappe.log_error(str(e), "WebSprix fetch_and_process_outgoing_call_logs")
		return {"status": "error", "message": "API request failed", "details": str(e)}


@frappe.whitelist()
def fetch_and_process_missed_call_logs() -> dict:
	"""Fetch missed call (no-answer) logs when no agent was available."""
	user = frappe.session.user
	agent = frappe.db.get_value(
		"CRM Telephony Agent",
		{"user": user},
		["websprix_number", "websprix_queue_id"],
		as_dict=True,
	)
	if not agent:
		return {"status": "error", "message": "Settings not found for the current user"}

	queue_name = (agent.websprix_queue_id or "").split("Q", 1)[0]
	settings = _get_settings()
	url = f"{_get_base_url()}/new-report/{settings.organization_id}/{queue_name}/noanswer?page=1&per_page=50"

	try:
		response = requests.get(url, headers=_get_headers(), timeout=30)
		if response.status_code not in [200, 201]:
			frappe.log_error(
				f"Failed to fetch missed calls: {response.status_code} - {response.text}",
				"WebSprix fetch_and_process_missed_call_logs",
			)
			return {"status": "error", "message": "Failed to fetch calls", "details": response.text}

		call_logs = response.json() or {}
		for log in call_logs.get("result", []):
			call_id = log.get("id")
			if not call_id or frappe.db.exists("CRM Call Log", call_id):
				continue

			to_value = log.get("agent", "")
			if to_value and to_value != "NONE" and "S" in to_value:
				to_value = to_value.split("S", 1)[1]

			new_call_log = {
				"doctype": "CRM Call Log",
				"telephony_medium": "WebSprix",
				"id": call_id,
				"type": "Incoming",
				"from": log.get("phone"),
				"to": to_value,
				"status": "No Answer",
				"start_time": log.get("ctime"),
			}
			frappe.get_doc(new_call_log).insert(ignore_permissions=True)

		frappe.db.commit()
		return {"status": "success", "message": "Call logs processed successfully"}
	except requests.exceptions.RequestException as e:
		frappe.log_error(str(e), "WebSprix fetch_and_process_missed_call_logs")
		return {"status": "error", "message": "API request failed", "details": str(e)}


def format_phone_number(phone_number: str) -> str:
	"""Normalize a phone number to Ethiopian E.164 format (+251...)."""
	if not phone_number:
		return ""
	digits = re.sub(r"\D", "", phone_number)
	if len(digits) == 9:
		return "+251" + digits
	if len(digits) == 10:
		return "+251" + digits[1:]
	if len(digits) in (12, 13):
		return "+" + digits
	return phone_number


def sort_logs_by_date(logs):
	"""Sort call logs by `created_at` ascending so inserts follow chronology."""
	try:
		return sorted(logs, key=lambda log: parse(log["created_at"]))
	except Exception:
		return logs


def _map_log_status(disposition: str) -> str:
	"""Map WebSprix disposition strings to CRM Call Log status values."""
	if not disposition:
		return "Initiated"
	normalized = disposition.strip().upper()
	mapping = {
		"ANSWERED": "Completed",
		"COMPLETED": "Completed",
		"NO ANSWER": "No Answer",
		"NOANSWER": "No Answer",
		"BUSY": "Busy",
		"FAILED": "Failed",
		"ABANDON": "Canceled",
		"RINGCANCELED": "Canceled",
		"QUEUED": "Queued",
	}
	return mapping.get(normalized, "Initiated")
