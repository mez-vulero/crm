import hashlib
import re
import uuid

import frappe
import requests
from dateutil.parser import parse
from frappe import _

from crm.integrations.api import get_contact_by_phone_number

QUEUE_CACHE_KEY = "websprix_queue_status"

# Default lookback window for the PBX report endpoints. The vendor's report
# API requires explicit `from`/`to` query params; if a caller doesn't supply
# them we fall back to the last N days.
DEFAULT_LOOKBACK_DAYS = 7
MAX_PER_PAGE = 10000


def _date_range(from_date: str | None = None, to_date: str | None = None) -> tuple[str, str]:
	"""Return (from_date, to_date) as YYYY-MM-DD strings, defaulting to a recent window."""
	from datetime import date, timedelta

	today = date.today()
	if not to_date:
		to_date = today.isoformat()
	if not from_date:
		from_date = (today - timedelta(days=DEFAULT_LOOKBACK_DAYS)).isoformat()
	return from_date, to_date


def _numeric_queue_id(full_queue_id: str | None) -> str:
	"""Return the numeric portion of a WebSprix queue id.

	WebSprix exposes queues to the agent dashboard as composite strings like
	`162Qcustomer_service`, but the path-based REST endpoints (queue/join,
	queue/leave, new-report/.../noanswer) expect just the numeric prefix
	(e.g. `162`). The endpoints that take the queue in a JSON body (member/add,
	member/remove) want the full composite id — those callers should NOT use
	this helper.
	"""
	if not full_queue_id:
		return ""
	return full_queue_id.split("Q", 1)[0]


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
	"""Return the queue id configured for the user and whether they have joined.

	Source of truth is the WebSprix PBX (via `/member/{customer_id}/queues_for_agent`).
	The local cache is only used to avoid a PBX round-trip on every call, and is
	kept in sync with the PBX's answer on each request.
	"""
	user = frappe.session.user
	queue_id = frappe.db.get_value("CRM Telephony Agent", user, "websprix_queue_id")
	if not queue_id:
		return {"queue_id": None, "joined": False}

	cached = frappe.cache().hget(QUEUE_CACHE_KEY, user)
	if cached in ("joined", "not_joined"):
		return {"queue_id": queue_id, "joined": cached == "joined"}

	# Cache miss — ask the PBX directly (silent on failure to keep UI responsive)
	try:
		status_check = get_queue_status()
	except Exception:
		status_check = None

	if isinstance(status_check, dict) and status_check.get("status") == "success":
		is_member = bool(status_check.get("is_member"))
		frappe.cache().hset(
			QUEUE_CACHE_KEY, user, "joined" if is_member else "not_joined"
		)
		return {"queue_id": queue_id, "joined": is_member}

	# PBX unreachable or queue not found — assume not joined, don't cache.
	return {"queue_id": queue_id, "joined": False}


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


def _queue_membership_request(action: str) -> tuple:
	"""Fire a /member/{customer_id}/{action} request for the current user.

	WebSprix's REST verb differs per action:
	  - `add`    → POST   /member/{cust}/add     body={queue_name, interface}
	  - `remove` → DELETE /member/{cust}/remove  body={queue_name, interface}

	The legacy `/queue/join/{org}/{queue_num}/{ext}` path endpoint returns 404
	on current tenants and is no longer used. Returns (response, interface,
	queue_name).
	"""
	agent, interface = _get_user_queue_interface()
	if not agent:
		frappe.throw(
			_("Your WebSprix Queue ID or extension is missing from the Telephony Agent profile."),
			title=_("WebSprix Not Configured"),
		)

	settings = _get_settings()
	url = f"{_get_base_url()}/member/{settings.customer_id}/{action}"
	body = {
		"queue_name": agent.websprix_queue_id,
		"interface": interface,
	}

	if action == "remove":
		response = requests.delete(url, json=body, headers=_get_headers(), timeout=10)
	else:
		response = requests.post(url, json=body, headers=_get_headers(), timeout=10)
	return response, interface, agent.websprix_queue_id


def _short_pbx_error(response) -> str:
	"""Extract the most informative short message from a PBX error response."""
	if response is None:
		return ""
	try:
		payload = response.json()
	except (ValueError, AttributeError):
		return (getattr(response, "text", "") or "")[:300]

	# Walk common error shapes used by WebSprix / FastAPI-style servers
	for key in ("detail", "error", "message", "msg"):
		val = payload.get(key) if isinstance(payload, dict) else None
		if val:
			if isinstance(val, list):
				# FastAPI returns [{"loc": [...], "msg": "...", "type": "..."}]
				return "; ".join(
					f"{'.'.join(str(x) for x in item.get('loc', []))}: {item.get('msg', item)}"
					if isinstance(item, dict)
					else str(item)
					for item in val
				)[:300]
			return str(val)[:300]
	return (getattr(response, "text", "") or "")[:300]


def _handle_queue_http_error(e, action_label: str, body: dict):
	"""Log the full PBX response + request body, then throw a human-readable error."""
	response = getattr(e, "response", None)
	status = getattr(response, "status_code", "error")
	pbx_msg = _short_pbx_error(response)
	frappe.log_error(
		f"{e}\nStatus: {status}\nRequest body: {body}\nResponse body: {getattr(response, 'text', '')}",
		f"WebSprix {action_label}",
	)
	if pbx_msg:
		frappe.throw(
			_("WebSprix rejected the {0} request ({1}): {2}").format(
				action_label, status, pbx_msg
			),
			title=_("Queue {0} Failed").format(action_label.title()),
		)
	frappe.throw(
		_("WebSprix rejected the {0} request ({1}).").format(action_label, status),
		title=_("Queue {0} Failed").format(action_label.title()),
	)


def _is_already_member_error(pbx_msg: str) -> bool:
	msg = (pbx_msg or "").lower()
	return "already" in msg and ("exist" in msg or "member" in msg or "queue" in msg)


def _is_not_member_error(pbx_msg: str) -> bool:
	msg = (pbx_msg or "").lower()
	if "not" not in msg:
		return False
	return "member" in msg or "exist" in msg or "found" in msg


@frappe.whitelist()
def join_queue() -> dict:
	"""Join the WebSprix queue configured for the current user.

	Idempotent: if the PBX reports the agent is already a member, we treat
	that as success and sync our local cache accordingly.
	"""
	user = frappe.session.user
	_require_queue_config(user)

	body = None
	try:
		response, interface, queue_id = _queue_membership_request("add")
		body = {"queue_name": queue_id, "interface": interface}
		response.raise_for_status()
	except requests.exceptions.Timeout:
		frappe.throw(
			_("WebSprix did not respond in time. Please try again."),
			title=_("Queue Join Failed"),
		)
	except requests.exceptions.HTTPError as e:
		pbx_msg = _short_pbx_error(getattr(e, "response", None))
		if _is_already_member_error(pbx_msg):
			# Already in the queue — state the frontend wanted anyway.
			frappe.cache().hset(QUEUE_CACHE_KEY, user, "joined")
			queue_id = frappe.db.get_value(
				"CRM Telephony Agent", user, "websprix_queue_id"
			)
			return {"joined": True, "queue_id": queue_id}
		_handle_queue_http_error(e, "join", body or {})
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
	"""Leave the WebSprix queue configured for the current user.

	Idempotent: if the PBX reports the agent wasn't in the queue to begin
	with, we treat that as success and sync our local cache accordingly.
	"""
	user = frappe.session.user
	_require_queue_config(user)

	body = None
	try:
		response, interface, queue_id = _queue_membership_request("remove")
		body = {"queue_name": queue_id, "interface": interface}
		response.raise_for_status()
	except requests.exceptions.Timeout:
		frappe.throw(
			_("WebSprix did not respond in time. Please try again."),
			title=_("Queue Leave Failed"),
		)
	except requests.exceptions.HTTPError as e:
		pbx_msg = _short_pbx_error(getattr(e, "response", None))
		if _is_not_member_error(pbx_msg):
			# Wasn't in the queue — state the frontend wanted anyway.
			frappe.cache().hset(QUEUE_CACHE_KEY, user, "not_joined")
			queue_id = frappe.db.get_value(
				"CRM Telephony Agent", user, "websprix_queue_id"
			)
			return {"joined": False, "queue_id": queue_id}
		_handle_queue_http_error(e, "leave", body or {})
	except requests.exceptions.RequestException as e:
		frappe.log_error(str(e), "WebSprix leave_queue")
		frappe.throw(
			_("Could not reach WebSprix. Check your network and the Base URL in settings."),
			title=_("Queue Leave Failed"),
		)

	frappe.cache().hset(QUEUE_CACHE_KEY, user, "not_joined")
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
def fetch_and_process_incoming_call_logs(
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict:
	"""Fetch incoming call logs from WebSprix and sync into CRM Call Log."""
	user = frappe.session.user
	agent = frappe.db.get_value(
		"CRM Telephony Agent",
		{"user": user},
		["websprix_number"],
		as_dict=True,
	)
	if not agent or not agent.websprix_number:
		return {"status": "error", "message": "Settings not found for the current user"}

	settings = _get_settings()
	from_date, to_date = _date_range(from_date, to_date)

	# Ask for a full page with the date window — without `per_page` the PBX
	# returns a small default (≈5-10 rows), which is why prior syncs only
	# pulled a handful of entries.
	url = (
		f"{_get_base_url()}/cust_ext/{settings.organization_id}/call_logs/{agent.websprix_number}"
		f"?dir=in&page=1&per_page={MAX_PER_PAGE}&from={from_date}&to={to_date}"
	)

	try:
		response = requests.get(url, headers=_get_headers(), timeout=30)
	except requests.exceptions.RequestException as e:
		frappe.log_error(str(e), "WebSprix fetch_and_process_incoming_call_logs (request)")
		return {"status": "error", "message": "API request failed", "details": str(e)}

	if response.status_code not in [200, 201]:
		frappe.log_error(
			f"Failed to fetch incoming calls: {response.status_code} - {response.text[:500]}",
			"WebSprix fetch_and_process_incoming_call_logs",
		)
		return {"status": "error", "message": "Failed to fetch calls", "details": response.text[:500]}

	try:
		call_logs = response.json() or {}
	except ValueError as e:
		frappe.log_error(
			f"Non-JSON response: {response.text[:500]}",
			"WebSprix fetch_and_process_incoming_call_logs (json)",
		)
		return {"status": "error", "message": "Invalid response from PBX", "details": str(e)}

	rows = call_logs.get("result") or []
	sorted_logs = sort_logs_by_date(rows)
	inserted = 0
	for log in sorted_logs:
		before = frappe.db.exists("CRM Call Log", log.get("id"))
		_create_incoming_call_log(log=log, user_link=user)
		if not before and frappe.db.exists("CRM Call Log", log.get("id")):
			inserted += 1

	frappe.db.commit()
	return {
		"status": "success",
		"message": f"Incoming logs processed: {inserted} inserted from {len(rows)} PBX rows",
		"inserted": inserted,
		"fetched": len(rows),
	}


def _create_incoming_call_log(log, user_link=None, off_hour=False):
	"""Insert a CRM Call Log for an incoming call from the WebSprix export."""
	try:
		call_id = log.get("id")
		if call_id and frappe.db.exists("CRM Call Log", call_id):
			return

		if not off_hour:
			from_number = format_phone_number(log.get("src") or "") or log.get("src") or ""
			to_number = log.get("dst") or ""
			if not from_number or not to_number or not call_id:
				return
			new_call_log = {
				"doctype": "CRM Call Log",
				"telephony_medium": "WebSprix",
				"type": "Incoming",
				"id": call_id,
				"from": from_number,
				"to": to_number,
				"receiver": user_link,
				"duration": int(log.get("duration") or 0),
				"recording_url": log.get("recording_url") or "",
				"status": _map_log_status(log.get("disposition")),
				"start_time": log.get("created_at"),
			}
		else:
			from_number = log.get("phone") or ""
			if not from_number:
				return
			unique_id = str(uuid.uuid4())
			short_id = hashlib.sha256(unique_id.encode()).hexdigest()[:10]
			new_call_log = {
				"doctype": "CRM Call Log",
				"telephony_medium": "WebSprix",
				"id": short_id,
				"type": "Incoming",
				"from": from_number,
				"to": user_link or "Queue",
				"status": "No Answer",
				"start_time": log.get("created_at"),
			}

		frappe.get_doc(new_call_log).insert(ignore_permissions=True)
	except Exception as e:
		frappe.log_error(
			f"row={log}\nerror={e}",
			"WebSprix _create_incoming_call_log",
		)


@frappe.whitelist()
def fetch_and_process_outgoing_call_logs(
	from_date: str | None = None,
	to_date: str | None = None,
	all_agents: bool = False,
) -> dict:
	"""Fetch outgoing call logs from WebSprix's `cust_rep/outgoing_report` endpoint.

	The PBX exposes outgoing CDR via `/api/v2/cust_rep/outgoing_report/{org_id}`
	with `from`, `to`, and `agent` query params. `agent` can be the user's
	extension or `null` for org-wide.
	"""
	user = frappe.session.user
	agent_row = frappe.db.get_value(
		"CRM Telephony Agent",
		{"user": user},
		["websprix_number"],
		as_dict=True,
	)
	if not all_agents and (not agent_row or not agent_row.websprix_number):
		return {"status": "error", "message": "Settings not found for the current user"}

	settings = _get_settings()
	from_date, to_date = _date_range(from_date, to_date)
	agent_param = "null" if all_agents else agent_row.websprix_number
	base = _get_base_url()

	# The vendor's outgoing-report endpoints accept either the tenant's
	# organization_id or customer_id depending on how the account was
	# provisioned. We probe both before falling back to the legacy per-
	# extension path on cust_ext. The first URL that returns 2xx wins.
	ext = agent_row.websprix_number if agent_row else None
	candidate_urls = [
		f"{base}/cust_rep/outgoing_report/{settings.organization_id}"
		f"?from={from_date}&to={to_date}&agent={agent_param}",
		f"{base}/cust_rep/outgoing_report/{settings.customer_id}"
		f"?from={from_date}&to={to_date}&agent={agent_param}",
	]
	if not all_agents and ext:
		candidate_urls.extend([
			f"{base}/cust_ext/{settings.organization_id}/call_logs/{ext}"
			f"?dir=out&page=1&per_page={MAX_PER_PAGE}&from={from_date}&to={to_date}",
			f"{base}/cust_ext/{settings.customer_id}/call_logs/{ext}"
			f"?dir=out&page=1&per_page={MAX_PER_PAGE}&from={from_date}&to={to_date}",
		])

	response = None
	last_error_detail = ""
	for url in candidate_urls:
		try:
			response = requests.get(url, headers=_get_headers(), timeout=30)
		except requests.exceptions.RequestException as e:
			last_error_detail = f"{url}\n{e}"
			frappe.log_error(last_error_detail, "WebSprix fetch outgoing (request)")
			response = None
			continue

		if response.status_code in [200, 201]:
			break

		last_error_detail = f"{url}\n{response.status_code}: {response.text[:500]}"
		frappe.log_error(last_error_detail, "WebSprix fetch outgoing (http)")
		response = None

	if response is None:
		return {
			"status": "error",
			"message": "All WebSprix outgoing-report endpoints failed",
			"details": last_error_detail[:500],
		}

	try:
		payload = response.json() or {}
	except ValueError as e:
		frappe.log_error(
			f"Non-JSON response: {response.text[:500]}",
			"WebSprix fetch_and_process_outgoing_call_logs (json)",
		)
		return {"status": "error", "message": "Invalid response from PBX", "details": str(e)}

	# `outgoing_report` may return either a top-level list, {"result": [...]},
	# or {"data": [...]}. Be defensive about the shape.
	if isinstance(payload, list):
		rows = payload
	else:
		rows = (
			payload.get("result")
			or payload.get("data")
			or payload.get("records")
			or payload.get("items")
			or []
		)

	# First-row payload sample — logged so we can diagnose field-name
	# mismatches without needing server shell access. Only fires on sync,
	# so it's at most one error-log entry per manual/cron run.
	if rows:
		try:
			sample = rows[0] if isinstance(rows[0], dict) else {"_value": rows[0]}
			frappe.log_error(
				f"first row keys: {sorted(sample.keys()) if isinstance(sample, dict) else 'not-a-dict'}\n"
				f"first row: {sample}",
				"WebSprix outgoing payload sample",
			)
		except Exception:
			pass
	else:
		frappe.log_error(
			f"Empty row list.\npayload type: {type(payload).__name__}\n"
			f"top-level keys: {list(payload.keys()) if isinstance(payload, dict) else 'n/a'}\n"
			f"payload[:500]: {str(payload)[:500]}",
			"WebSprix outgoing empty response",
		)

	inserted = 0
	skipped = 0
	for row in rows:
		try:
			from_number = row.get("src") or row.get("caller") or row.get("from") or ""
			to_number_raw = (
				row.get("dst") or row.get("callee") or row.get("to") or row.get("number") or ""
			)
			to_number = format_phone_number(to_number_raw) or to_number_raw

			if not from_number or not to_number:
				skipped += 1
				continue

			start_date = _parse_pbx_datetime(
				row.get("created_at")
				or row.get("calldate")
				or row.get("start_time")
				or row.get("ctime")
				or row.get("datetime")
			)

			call_id = (
				row.get("id")
				or row.get("uniqueid")
				or row.get("call_id")
				or row.get("uuid")
				or row.get("unique_id")
			)
			if not call_id:
				# Synthesize a deterministic id so a re-run of the same row
				# doesn't double-insert. Key = from|to|start_time.
				key = f"wsout-{from_number}-{to_number}-{start_date or row.get('duration') or ''}"
				call_id = hashlib.sha256(key.encode()).hexdigest()[:20]

			if frappe.db.exists("CRM Call Log", call_id):
				skipped += 1
				continue

			new_call_log = {
				"doctype": "CRM Call Log",
				"telephony_medium": "WebSprix",
				"type": "Outgoing",
				"id": call_id,
				"from": from_number,
				"to": to_number,
				"caller": _resolve_agent_user(row.get("agent") or row.get("extension")) or user,
				"duration": int(row.get("duration") or row.get("billsec") or 0),
				"status": _map_log_status(row.get("disposition") or row.get("status")),
				"recording_url": (
					row.get("recording_url")
					or row.get("recording")
					or row.get("recordingfile")
					or row.get("recording_path")
					or ""
				),
				"start_time": start_date,
			}
			frappe.get_doc(new_call_log).insert(ignore_permissions=True)
			inserted += 1
		except Exception as e:
			frappe.log_error(
				f"row={row}\nerror={e}",
				"WebSprix outgoing call log insert",
			)
			skipped += 1

	frappe.db.commit()
	return {
		"status": "success",
		"message": f"Outgoing logs processed: {inserted} inserted, {skipped} skipped",
		"inserted": inserted,
		"skipped": skipped,
	}


@frappe.whitelist()
def fetch_and_process_missed_call_logs(
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict:
	"""Fetch missed call (no-answer) logs from WebSprix.

	The vendor's `new-report/{org}/{queue}/noanswer` endpoint requires `from`
	and `to` date params (YYYY-MM-DD) — without them the response is empty.
	"""
	user = frappe.session.user
	agent = frappe.db.get_value(
		"CRM Telephony Agent",
		{"user": user},
		["websprix_number", "websprix_queue_id"],
		as_dict=True,
	)
	if not agent or not agent.websprix_queue_id:
		return {"status": "error", "message": "Settings not found for the current user"}

	# The PBX queue path uses the bare numeric queue id (the part before "Q...")
	queue_name = _numeric_queue_id(agent.websprix_queue_id)
	settings = _get_settings()
	from_date, to_date = _date_range(from_date, to_date)
	url = (
		f"{_get_base_url()}/new-report/{settings.organization_id}/{queue_name}/noanswer"
		f"?page=1&per_page={MAX_PER_PAGE}&from={from_date}&to={to_date}&cphone=null"
	)

	try:
		response = requests.get(url, headers=_get_headers(), timeout=30)
	except requests.exceptions.RequestException as e:
		frappe.log_error(str(e), "WebSprix fetch_and_process_missed_call_logs (request)")
		return {"status": "error", "message": "API request failed", "details": str(e)}

	if response.status_code not in [200, 201]:
		frappe.log_error(
			f"Failed to fetch missed calls: {response.status_code} - {response.text[:500]}",
			"WebSprix fetch_and_process_missed_call_logs",
		)
		return {"status": "error", "message": "Failed to fetch calls", "details": response.text[:500]}

	try:
		call_logs = response.json() or {}
	except ValueError as e:
		frappe.log_error(
			f"Non-JSON response: {response.text[:500]}",
			"WebSprix fetch_and_process_missed_call_logs (json)",
		)
		return {"status": "error", "message": "Invalid response from PBX", "details": str(e)}

	inserted = 0
	skipped = 0
	for log in call_logs.get("result") or []:
		try:
			call_id = log.get("id")
			if not call_id or frappe.db.exists("CRM Call Log", call_id):
				skipped += 1
				continue

			to_value = log.get("agent") or ""
			if to_value and to_value != "NONE" and "S" in to_value:
				to_value = to_value.split("S", 1)[1]

			from_number = log.get("phone") or ""
			if not from_number or not to_value:
				skipped += 1
				continue

			new_call_log = {
				"doctype": "CRM Call Log",
				"telephony_medium": "WebSprix",
				"id": call_id,
				"type": "Incoming",
				"from": from_number,
				"to": to_value,
				"status": "No Answer",
				"start_time": log.get("ctime"),
			}
			frappe.get_doc(new_call_log).insert(ignore_permissions=True)
			inserted += 1
		except Exception as e:
			frappe.log_error(
				f"row={log}\nerror={e}",
				"WebSprix missed call log insert",
			)
			skipped += 1

	frappe.db.commit()
	return {
		"status": "success",
		"message": f"Missed logs processed: {inserted} inserted, {skipped} skipped",
		"inserted": inserted,
		"skipped": skipped,
	}


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


def _parse_pbx_datetime(value):
	"""Best-effort parse of various WebSprix date formats. Returns naive datetime or None."""
	if not value:
		return None
	try:
		return parse(value).replace(tzinfo=None)
	except (ValueError, TypeError):
		return None


def _resolve_agent_user(extension):
	"""Map a WebSprix extension to a Frappe User via CRM Telephony Agent."""
	if not extension:
		return None
	# Some payloads encode it as `{customer_id}S{extension}`
	if isinstance(extension, str) and "S" in extension:
		try:
			extension = extension.split("S", 1)[1]
		except IndexError:
			pass
	user = frappe.db.get_value(
		"CRM Telephony Agent",
		{"websprix_number": str(extension)},
		"user",
	)
	return user


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
