# FSI Lifecycle — Business Logic Equations

Documents the core business rules encoded in `app/services/workflow.py`.

---

## EQ-001: Provisioned Email Address

**Source:** `_build_generated_email()`

```
provisioned_email = lower(strip(first_name)) + "." + lower(strip(last_name)) + "@freightservices.net"
```

Spaces within names are removed. This email is used for M365 account creation and FSI identity provisioning.

---

## EQ-002: Action Plan Determination

**Source:** `build_action_plan()`

```
if event_type == "onboarding":
    actions += ["Create M365 account (Stellar Support)"]
    if role_profile in {"office", "manager"}:
        actions += ["Provision laptop + dock (Stellar Sales)"]

if event_type == "offboarding":
    actions += ["Revoke AD and M365 sessions (Stellar Support)"]
```

---

## EQ-003: CC Routing

**Source:** `_build_cc_targets()`

```
cc_targets = union(
    communication_options.internal_notification_list (comma-separated),
    HR_CC_EMAILS env var (comma-separated),
    manager_email (if set),
)
# De-duplicated, order preserved.
primary_to_email = cc_targets[0] if cc_targets else manager_email
```

The primary recipient for approval emails is the first address in the CC list (typically HR), falling back to manager_email.

---

## EQ-004: Approval Routing

**Source:** `initiate_lifecycle_event()`

```
approver_email = manager_email OR first(HR_CC_EMAILS)
```

If neither is set, the intake cannot be initiated and returns an error. The approval email uses template alias `manager-approval-required` via Postmark.

---

## EQ-005: Hardware Procurement Trigger

**Source:** `_execute_onboarding()`

```
if role_profile in {"office", "manager"}:
    send hardware-procurement email → stellar_sales_email
```

Drivers and warehouse employees do not trigger Stellar Sales hardware tickets. Their equipment is handled via EQ-006.

---

## EQ-006: Driver Asset Provisioning

**Source:** `_execute_onboarding()`, driver branch

```
assets_needed = []
if driver_needs_laptop:       assets_needed += ["Laptop"]
if driver_needs_printer:      assets_needed += ["Mobile Printer"]
if driver_needs_fuel_card:    assets_needed += ["Fuel Card"]
if driver_needs_vehicle:      assets_needed += ["Box Truck Assignment"]

if assets_needed:
    send internal-fleet-provisioning email → FSI_OPS_EMAIL
```

---

## EQ-007: Offboarding Deactivation

**Source:** `_execute_offboarding()`

```
# Immediate vs scheduled determines template alias:
template = "offboarding-immediate" if is_immediate else "offboarding-standard"

# FSI identity deactivation (lifecycle writes to shared users table):
if user exists and is_active:
    user.is_active = False

# Stellar Support notification sent with termination_date:
termination_display = "Immediate" if is_immediate
                    else termination_date.isoformat() if termination_date
                    else "Not Provided"

# Driver offboarding additionally triggers ops asset recovery:
if role_profile == "driver":
    send internal-fleet-provisioning (RECOVERY) → telecon_sales_email
```

---

## EQ-008: Inventory Status Transitions

**Source:** `app/services/inventory_service.py`

```
assign_asset(asset, user_id):
    asset.status = ASSIGNED
    asset.assigned_to_user_id = user_id

unassign_asset(asset):
    asset.status = AVAILABLE
    asset.assigned_to_user_id = None

retire_asset(asset):
    asset.status = RETIRED
    asset.assigned_to_user_id = None   # clears assignment on retirement
```

Valid status values: `Available`, `Assigned`, `In_Repair`, `Retired`, `Lost`.
