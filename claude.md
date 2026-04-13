# Task: Add Real Estate Developer Module to Frappe CRM

## Codebase Overview

This is **Frappe CRM** (https://github.com/frappe/crm) — an open-source CRM built on the Frappe Framework. The architecture is:

- **Backend**: Python + Frappe Framework. DocTypes are defined as JSON files in `crm/fcrm/doctype/<doctype_name>/` alongside a Python controller `.py` file. Each DocType folder contains: `<name>.json`, `<name>.py`, `__init__.py`.
- **Frontend**: Vue.js 3 in the `frontend/` folder using Frappe UI components. Routes are in `frontend/src/router.js`. Page components are in `frontend/src/pages/`.
- **API**: Whitelisted Python methods exposed via `@frappe.whitelist()` and called from Vue with `call('crm.fcrm.doctype.xxx.xxx.method_name', {...})`.
- **Existing core DocTypes**: `CRM Lead`, `CRM Deal`, `CRM Contact`, `CRM Organization`, `CRM Task`, `CRM Note`, `CRM Call Log`. Do not rename or modify the JSON of these — extend them only via fixtures.
- **CRM Form Scripts**: Class-based JS scripts stored in the DB, used to add UI behaviour to Lead/Deal pages without rebuilding the frontend.

---

## What to Build

Add a **Real Estate Developer** module as a new feature group within the app. All **new** DocTypes in this module must be named **without** a "CRM" prefix (e.g. `Real Estate Project`, not `CRM Real Estate Project`). Create the following DocTypes and enhancements:

---

### 1. `Real Estate Project` (new DocType)

File path: `crm/fcrm/doctype/real_estate_project/`

Fields:
- `project_name` (Data, mandatory, title field)
- `status` (Select: Pre-Launch / Active / Sold Out / Delivered, default: Active)
- `location` (Data)
- `city` (Data)
- `description` (Text Editor)
- `total_units` (Int, read-only — auto-calculated from linked units)
- `available_units` (Int, read-only — auto-calculated)
- `reserved_units` (Int, read-only — auto-calculated)
- `sold_units` (Int, read-only — auto-calculated)
- `launch_date` (Date)
- `delivery_date` (Date)
- `image` (Attach Image)

Python controller (`real_estate_project.py`):
- On save, recalculate `total_units`, `available_units`, `reserved_units`, `sold_units` by querying `Property Unit`.
- Expose a `@frappe.whitelist()` method `get_unit_summary(project)` that returns counts per status.

---

### 2. `Property Unit` (new DocType)

File path: `crm/fcrm/doctype/property_unit/`

Fields:
- `unit_number` (Data, mandatory, title field)
- `project` (Link → Real Estate Project, mandatory, in list view)
- `floor` (Int)
- `unit_type` (Select: Studio / 1BR / 2BR / 3BR / 4BR / Penthouse)
- `size_sqm` (Float)
- `base_price` (Currency)
- `price_override` (Currency — if set, overrides base_price for display)
- `view_direction` (Select: Garden / City / Sea / Courtyard / Street)
- `status` (Select: Available / Reserved / Sold / Blocked, default: Available, in list view)
- `floor_plan` (Attach)
- `notes` (Small Text)
- `linked_deal` (Link → CRM Deal, read-only — set automatically on reservation)

Python controller (`property_unit.py`):
- On status change to `Available`, clear `linked_deal`.
- Expose `@frappe.whitelist()` method `get_available_units(project, unit_type=None)` returning a list of available units with key fields.

---

### 3. `Unit Reservation` (new DocType)

File path: `crm/fcrm/doctype/unit_reservation/`

Fields:
- `unit` (Link → Property Unit, mandatory)
- `project` (Link → Real Estate Project — auto-fetched from unit)
- `deal` (Link → CRM Deal)
- `lead` (Link → CRM Lead)
- `reservation_type` (Select: Soft / Hard, default: Soft)
- `reservation_date` (Date, default: today)
- `expiry_date` (Date — for soft reservations)
- `deposit_amount` (Currency)
- `deposit_paid` (Check)
- `status` (Select: Active / Expired / Cancelled / Converted, default: Active)
- `notes` (Small Text)

Python controller (`unit_reservation.py`):
- On insert, set `Property Unit.status = Reserved` and `Property Unit.linked_deal = self.deal`.
- On cancellation (status → Cancelled / Expired), reset `Property Unit.status = Available` and clear `linked_deal`.
- On `reservation_type = Hard` and `deposit_paid = 1`, do not auto-expire.
- Expose `@frappe.whitelist()` method `reserve_unit(unit, deal=None, lead=None, reservation_type='Soft', deposit_amount=0, expiry_date=None)`.

---

### 4. `Viewing Appointment` (new DocType)

File path: `crm/fcrm/doctype/viewing_appointment/`

Fields:
- `appointment_date` (Date, mandatory)
- `appointment_time` (Time)
- `lead` (Link → CRM Lead)
- `deal` (Link → CRM Deal)
- `project` (Link → Real Estate Project)
- `unit` (Link → Property Unit — optional, if a specific unit is being viewed)
- `assigned_agent` (Link → User)
- `status` (Select: Scheduled / Completed / No-Show / Cancelled, default: Scheduled)
- `feedback` (Small Text — filled after the visit)
- `notes` (Small Text)

---

### 5. `Payment Schedule` (new DocType — child table)

File path: `crm/fcrm/doctype/payment_schedule/`

Set `istable: 1` in the DocType JSON.

Fields:
- `milestone` (Data, label: "Milestone / Description")
- `due_date` (Date)
- `amount` (Currency)
- `percentage` (Percent)
- `status` (Select: Pending / Paid / Overdue, default: Pending)
- `payment_date` (Date — actual payment date when marked Paid)

---

### 6. Extend `CRM Deal` with real estate fields

Add custom fields to the existing `CRM Deal` DocType via a fixture file at:
`crm/fcrm/fixtures/custom_field.json`

Fields to add to CRM Deal:
- `re_project` (Link → Real Estate Project, label: "Project")
- `re_unit` (Link → Property Unit, label: "Unit")
- `re_unit_status` (Data, label: "Unit Status", fetch_from: `re_unit.status`, read-only)
- `re_purchase_price` (Currency, label: "Purchase Price")
- `re_reservation_date` (Date, label: "Reservation Date")
- `re_contract_date` (Date, label: "Contract Date")
- `re_deed_date` (Date, label: "Deed / Transfer Date")
- `re_mortgage_status` (Select: Not Applicable / Pending / Approved / Rejected, label: "Mortgage Status")
- `re_commission_rate` (Percent, label: "Commission %")
- `re_commission_amount` (Currency, label: "Commission Amount", read-only — auto-calculated as `re_purchase_price × re_commission_rate / 100`)
- `re_payment_schedule` (Table → Payment Schedule, label: "Payment Schedule")

---

### 7. Extend `CRM Lead` with real estate fields

Add to the same `custom_field.json` fixture:

Fields to add to CRM Lead:
- `re_budget_min` (Currency, label: "Min Budget")
- `re_budget_max` (Currency, label: "Max Budget")
- `re_preferred_unit_type` (Select: Studio / 1BR / 2BR / 3BR / 4BR / Penthouse, label: "Preferred Unit Type")
- `re_interested_project` (Link → Real Estate Project, label: "Interested In")
- `re_preferred_floor` (Int, label: "Preferred Floor")

---

## Frontend Requirements

### Page 1: `Real Estate Projects` (`/crm/real-estate`)

- Create `frontend/src/pages/RealEstate.vue`
- Add route in `frontend/src/router.js`: `{ path: '/real-estate', component: RealEstate }`
- Add a sidebar nav link labeled "Properties" (use a building icon from lucide-vue or heroicons, matching the style of existing nav links)
- The page shows a list of `Real Estate Project` records with columns: Project Name, Status, City, Total Units, Available, Reserved, Sold, Launch Date
- Clicking a row navigates to the project detail page

### Page 2: `Project Detail` (`/crm/real-estate/:projectId`)

- Create `frontend/src/pages/RealEstateProject.vue`
- Header: project name, status badge, city, launch/delivery dates
- Body: a filterable **unit grid** of all `Property Unit` records for this project
  - Columns: Unit Number, Floor, Type, Size (sqm), Price, View Direction, Status
  - Status shown as a colored badge (Available = green, Reserved = amber, Sold = red, Blocked = gray)
  - Filter bar: filter by Status and Unit Type
  - Clicking a unit opens a slide-over panel showing full unit details and a "Reserve Unit" button
- "Reserve Unit" opens a dialog allowing the user to link a CRM Lead or CRM Deal and create a `Unit Reservation` record

### Lead page enhancement

On the existing CRM Lead detail page, add a sidebar section titled **"Property Interest"** surfacing the real estate custom fields:
`re_interested_project`, `re_preferred_unit_type`, `re_budget_min`, `re_budget_max`, `re_preferred_floor`

### Deal page enhancement

On the existing CRM Deal detail page:
- Add a sidebar section titled **"Property"** surfacing: `re_project`, `re_unit`, `re_unit_status`, `re_purchase_price`, `re_reservation_date`, `re_contract_date`, `re_deed_date`, `re_mortgage_status`, `re_commission_rate`, `re_commission_amount`
- Add a **"Payment Schedule"** tab showing the `re_payment_schedule` child table in an editable format with a running total row at the bottom

---

## Naming Conventions & Patterns to Follow

- **New DocType JSON**: follow the structure of `crm/fcrm/doctype/crm_lead/crm_lead.json` (module: `"FCRM"`, naming_rule: `"Random"`, autoname: `"hash"`)
- **New DocType folder names**: use snake_case without a `crm_` prefix (e.g. `real_estate_project/`, `property_unit/`)
- **Python controllers**: extend `frappe.model.Document`; use `frappe.db.set_value()` for cross-doctype updates
- **Vue components**: use `frappe/frappe-ui` components (`ListView`, `Dialog`, `Badge`, `Button`) — use `frontend/src/pages/Leads.vue` as the reference pattern
- **API calls in Vue**: use the `call('crm.fcrm.doctype.xxx.method', args)` pattern matching existing usage in the codebase
- **Every new DocType folder** needs an empty `__init__.py`
- **`hooks.py`**: ensure `fixtures = ["Custom Field"]` is present so the fixture is loaded on `bench migrate`

---

## Deliverables Checklist

- [ ] 5 new DocType folders (`real_estate_project`, `property_unit`, `unit_reservation`, `viewing_appointment`, `payment_schedule`), each with `.json`, `.py`, `__init__.py`
- [ ] `crm/fcrm/fixtures/custom_field.json` extending `CRM Lead` and `CRM Deal`
- [ ] `hooks.py` updated with `fixtures = ["Custom Field"]` if not already present
- [ ] `frontend/src/pages/RealEstate.vue` — project list page
- [ ] `frontend/src/pages/RealEstateProject.vue` — project detail + unit grid page
- [ ] `frontend/src/router.js` updated with 2 new routes
- [ ] Sidebar navigation updated with "Properties" link
- [ ] CRM Lead detail page updated with "Property Interest" sidebar section
- [ ] CRM Deal detail page updated with "Property" sidebar section and "Payment Schedule" tab

**Before writing any code**, read the following files to understand the exact patterns used in this codebase:
1. `crm/fcrm/doctype/crm_lead/crm_lead.json` — DocType JSON structure
2. `crm/fcrm/doctype/crm_lead/crm_lead.py` — Python controller pattern
3. `crm/fcrm/doctype/crm_deal/crm_deal.py` — cross-doctype update patterns
4. `frontend/src/pages/Leads.vue` — list page component pattern
5. `frontend/src/router.js` — how routes are registered
6. `crm/hooks.py` — where fixtures are declared