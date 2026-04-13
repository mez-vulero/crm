## Additional Module: Contracts, Payments, Invoicing & Commissions

---

### 8. `Property Contract` (new DocType)

File path: `crm/fcrm/doctype/property_contract/`

This DocType represents the purchase agreement between the developer and the buyer.

Fields:
- `contract_number` (Data, read-only, auto-named — e.g. `CONT-2024-0001`)
- `deal` (Link → CRM Deal, mandatory)
- `lead` (Link → CRM Lead)
- `project` (Link → Real Estate Project, fetched from deal)
- `unit` (Link → Property Unit, fetched from deal)
- `buyer_name` (Data, fetched from deal/lead)
- `buyer_email` (Data)
- `buyer_phone` (Data)
- `purchase_price` (Currency, fetched from `re_purchase_price` on deal)
- `contract_date` (Date, default: today)
- `deed_date` (Date)
- `status` (Select: Draft / Sent / Signed / Cancelled, default: Draft)
- `signed_date` (Date, read-only — set when status changes to Signed)
- `template` (Link → Contract Template)
- `contract_body` (Text Editor, read-only — rendered output of the template after merge)
- `pdf_attachment` (Attach, read-only — stored after generation)

Python controller (`property_contract.py`):
- `autoname`: use a naming series like `CONT-.YYYY.-.#####`
- On insert, auto-fetch `project`, `unit`, `buyer_name`, `buyer_email`, `purchase_price` from the linked Deal
- Expose `@frappe.whitelist()` method `generate_contract(contract_name)`:
  - Fetches the linked `Contract Template`
  - Performs token replacement (see Contract Template below) to produce `contract_body`
  - Renders the body to PDF using `frappe.utils.pdf.get_pdf(html)`
  - Attaches the PDF to the document and populates `pdf_attachment`
  - Returns the file URL
- Expose `@frappe.whitelist()` method `mark_as_signed(contract_name, signed_date)`:
  - Sets `status = Signed` and `signed_date`
  - Sets `re_contract_date` on the linked CRM Deal

---

### 9. `Contract Template` (new DocType)

File path: `crm/fcrm/doctype/contract_template/`

Fields:
- `template_name` (Data, mandatory, title field)
- `description` (Small Text)
- `body` (Text Editor, mandatory)
  - Supports Jinja2-style tokens e.g. `{{ buyer_name }}`, `{{ unit_number }}`, `{{ purchase_price }}`, `{{ contract_date }}`, `{{ project_name }}`, `{{ floor }}`, `{{ size_sqm }}`, `{{ deed_date }}`
- `header_html` (Text Editor — optional letterhead HTML injected before body)
- `footer_html` (Text Editor — optional footer HTML)

Python controller (`contract_template.py`):
- Expose `@frappe.whitelist()` method `get_preview(template_name, contract_name)`:
  - Renders the template using the data from the given `Property Contract` record
  - Returns the rendered HTML string for live preview in the frontend

---

### 10. `Payment Collection` (new DocType)

File path: `crm/fcrm/doctype/payment_collection/`

This DocType tracks each actual payment received against a deal's payment schedule.

Fields:
- `payment_number` (Data, read-only, auto-named — e.g. `PAY-2024-0001`)
- `deal` (Link → CRM Deal, mandatory)
- `project` (Link → Real Estate Project, fetched from deal)
- `unit` (Link → Property Unit, fetched from deal)
- `buyer_name` (Data, fetched from deal)
- `payment_schedule_row` (Data — stores the `name` of the child row in the Payment Schedule this payment covers)
- `milestone_description` (Data, read-only — fetched from the payment schedule row)
- `scheduled_amount` (Currency, read-only — the expected amount from the schedule row)
- `amount_received` (Currency, mandatory)
- `payment_date` (Date, mandatory, default: today)
- `payment_method` (Select: Bank Transfer / Cash / Cheque / Online)
- `reference_number` (Data — bank ref, cheque number, etc.)
- `status` (Select: Received / Partially Received / Refunded, default: Received)
- `notes` (Small Text)
- `invoice` (Link → Property Invoice, read-only — set after invoice generation)

Python controller (`payment_collection.py`):
- `autoname`: naming series `PAY-.YYYY.-.#####`
- On save, update the linked Payment Schedule child row on the CRM Deal:
  - If `amount_received >= scheduled_amount`: set row `status = Paid` and `payment_date = today`
  - If `amount_received < scheduled_amount`: set row `status = Partially Received`
- Recalculate the deal's total collected amount (sum all `Payment Collection` records for that deal) and store it in a custom field `re_total_collected` on CRM Deal
- Expose `@frappe.whitelist()` method `get_payment_summary(deal)` returning:
  - `total_scheduled`: sum of all schedule rows
  - `total_collected`: sum of all Payment Collection records
  - `outstanding`: difference
  - `overdue_rows`: schedule rows with `due_date < today` and `status != Paid`

Add to `custom_field.json` for CRM Deal:
- `re_total_collected` (Currency, label: "Total Collected", read-only)
- `re_outstanding_amount` (Currency, label: "Outstanding", read-only — formula: `re_purchase_price - re_total_collected`)
- `re_payment_status` (Select: Not Started / In Progress / Fully Paid / Overdue, label: "Payment Status", read-only — auto-set by controller)

---

### 11. `Property Invoice` (new DocType)

File path: `crm/fcrm/doctype/property_invoice/`

Fields:
- `invoice_number` (Data, read-only, auto-named — e.g. `INV-2024-0001`)
- `deal` (Link → CRM Deal, mandatory)
- `payment_collection` (Link → Payment Collection — the payment this invoice is for)
- `project` (Link → Real Estate Project)
- `unit` (Link → Property Unit)
- `buyer_name` (Data)
- `buyer_email` (Data)
- `buyer_address` (Small Text)
- `invoice_date` (Date, default: today)
- `due_date` (Date)
- `line_items` (Table → Invoice Line Item)
- `subtotal` (Currency, read-only — sum of line items)
- `tax_rate` (Percent)
- `tax_amount` (Currency, read-only — subtotal × tax_rate / 100)
- `total_amount` (Currency, read-only — subtotal + tax_amount)
- `status` (Select: Draft / Sent / Paid / Cancelled, default: Draft)
- `pdf_attachment` (Attach, read-only)
- `notes` (Small Text)

Python controller (`property_invoice.py`):
- `autoname`: naming series `INV-.YYYY.-.#####`
- On insert, auto-populate buyer fields from the linked Deal
- Expose `@frappe.whitelist()` method `generate_invoice_pdf(invoice_name)`:
  - Builds an HTML invoice using the line items, tax, totals, and company letterhead (fetched from a System Settings custom field or hardcoded fallback)
  - Renders to PDF using `frappe.utils.pdf.get_pdf(html)`
  - Attaches the PDF, sets `pdf_attachment`, updates linked `Payment Collection.invoice`
  - Returns file URL
- Expose `@frappe.whitelist()` method `send_invoice_by_email(invoice_name)`:
  - Sends the PDF as an email attachment to `buyer_email`
  - Uses Frappe's built-in `frappe.sendmail()`

---

### 12. `Invoice Line Item` (new DocType — child table)

File path: `crm/fcrm/doctype/invoice_line_item/`

Set `istable: 1`.

Fields:
- `description` (Data, mandatory)
- `quantity` (Float, default: 1)
- `unit_price` (Currency)
- `amount` (Currency, read-only — quantity × unit_price)

---

### 13. `Sales Commission` (new DocType)

File path: `crm/fcrm/doctype/sales_commission/`

This DocType tracks commission earned by sales agents per deal, supporting split commissions when multiple agents are involved.

Fields:
- `deal` (Link → CRM Deal, mandatory)
- `project` (Link → Real Estate Project, fetched from deal)
- `unit` (Link → Property Unit, fetched from deal)
- `agent` (Link → User, mandatory, label: "Sales Agent")
- `agent_name` (Data, read-only, fetched from User)
- `role` (Select: Primary Agent / Co-Agent / Referrer / Manager Override, label: "Agent Role")
- `commission_base` (Currency, read-only — fetched from deal's `re_purchase_price`)
- `commission_rate` (Percent, mandatory)
- `commission_amount` (Currency, read-only — commission_base × commission_rate / 100)
- `split_percentage` (Percent, default: 100 — for multi-agent splits)
- `final_commission` (Currency, read-only — commission_amount × split_percentage / 100)
- `trigger_event` (Select: On Reservation / On Contract Signing / On Full Payment, label: "Payable When")
- `status` (Select: Pending / Approved / Paid / Cancelled, default: Pending)
- `approved_by` (Link → User, read-only)
- `approved_date` (Date, read-only)
- `paid_date` (Date)
- `notes` (Small Text)

Python controller (`sales_commission.py`):
- On insert, auto-fetch `commission_base` from `CRM Deal.re_purchase_price`
- Auto-calculate `commission_amount` and `final_commission` on save
- Validate: if multiple `Sales Commission` records exist for the same deal, warn if total `split_percentage` across all agents for the same `role` group exceeds 100%
- Expose `@frappe.whitelist()` method `approve_commission(commission_name, approved_by)`:
  - Sets `status = Approved`, `approved_by`, `approved_date = today`
- Expose `@frappe.whitelist()` method `get_commissions_for_deal(deal)`:
  - Returns all commission records for the deal with agent names, rates, amounts, statuses
- Expose `@frappe.whitelist()` method `get_agent_commission_summary(agent, from_date=None, to_date=None)`:
  - Returns total pending, approved, and paid commissions for the given agent
  - Optionally filtered by date range on `deal` close date

Add to `custom_field.json` for CRM Deal:
- `re_total_commission` (Currency, label: "Total Commission Payable", read-only — sum of `final_commission` across all approved Sales Commission records for this deal)

---

## Additional Frontend Requirements

### Deal page: Contracts tab
- Add a **"Contracts"** tab on the CRM Deal detail page
- Lists all `Property Contract` records linked to this deal
- "Generate Contract" button — opens a dialog to select a `Contract Template`, then calls `generate_contract()` and shows a PDF preview link
- Each contract row shows: Contract Number, Status, Contract Date, PDF link, and a "Mark as Signed" button

### Deal page: Payments tab
- Add a **"Payments"** tab on the CRM Deal detail page showing two sub-sections:
  1. **Payment Schedule** (existing `re_payment_schedule` child table) — read-only view showing milestone, due date, amount, status, with overdue rows highlighted in red
  2. **Payment Collections** — list of `Payment Collection` records for this deal with columns: Payment Number, Date, Amount, Method, Reference, Status, Invoice link
  - "Record Payment" button opens a dialog:
    - Dropdown to select which Payment Schedule milestone this covers (shows milestone name + scheduled amount)
    - Fields: amount_received, payment_date, payment_method, reference_number
    - On submit, creates a `Payment Collection` record and refreshes the schedule view
  - "Generate Invoice" button next to each Payment Collection row — calls `generate_invoice_pdf()` and provides download link
  - Summary bar at the top: Total Scheduled | Total Collected | Outstanding | Payment Status badge

### Deal page: Commissions tab
- Add a **"Commissions"** tab on the CRM Deal detail page
- Lists all `Sales Commission` records for this deal
- Columns: Agent, Role, Rate %, Commission Amount, Split %, Final Commission, Trigger Event, Status
- "Add Commission" button opens a dialog with fields: agent, role, commission_rate, split_percentage, trigger_event
- Each row has an "Approve" button (visible to managers) that calls `approve_commission()`
- Footer row shows total commission payable

### New page: Agent Commission Dashboard (`/crm/commissions`)
- Create `frontend/src/pages/Commissions.vue`
- Add route and sidebar nav link labeled "Commissions"
- Shows the current logged-in user's commission summary:
  - Summary cards: Pending | Approved | Paid (currency totals)
  - Table of all their `Sales Commission` records with deal name, unit, project, amount, status, trigger event
- If the user has a manager role, show a toggle to view commissions for all agents with a filter by agent name

---

## Additional `custom_field.json` additions summary

All fields below go into `crm/fcrm/fixtures/custom_field.json` under their respective DocTypes:

**CRM Deal** (additions beyond what was listed earlier):
- `re_total_collected` (Currency, label: "Total Collected", read-only)
- `re_outstanding_amount` (Currency, label: "Outstanding", read-only)
- `re_payment_status` (Select: Not Started / In Progress / Fully Paid / Overdue, label: "Payment Status", read-only)
- `re_total_commission` (Currency, label: "Total Commission Payable", read-only)

---

## Updated Deliverables Checklist (additions only)

- [ ] `crm/fcrm/doctype/property_contract/` — with `.json`, `.py`, `__init__.py`
- [ ] `crm/fcrm/doctype/contract_template/` — with `.json`, `.py`, `__init__.py`
- [ ] `crm/fcrm/doctype/payment_collection/` — with `.json`, `.py`, `__init__.py`
- [ ] `crm/fcrm/doctype/property_invoice/` — with `.json`, `.py`, `__init__.py`
- [ ] `crm/fcrm/doctype/invoice_line_item/` — child table with `.json`, `.py`, `__init__.py`
- [ ] `crm/fcrm/doctype/sales_commission/` — with `.json`, `.py`, `__init__.py`
- [ ] CRM Deal detail page: Contracts tab added
- [ ] CRM Deal detail page: Payments tab added (schedule + collections + invoices + summary bar)
- [ ] CRM Deal detail page: Commissions tab added
- [ ] `frontend/src/pages/Commissions.vue` — agent commission dashboard
- [ ] Router updated with `/crm/commissions` route
- [ ] Sidebar updated with "Commissions" nav link
- [ ] `custom_field.json` updated with new Deal fields