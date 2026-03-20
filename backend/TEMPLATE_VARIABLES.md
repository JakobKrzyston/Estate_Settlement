# Template Variable Reference

Master reference for all Jinja2 variables used across the 15 letter templates in `templates/`.

---

## Auto-Filled Variables

These 12 variables are injected into **every template automatically** by `_cert_to_vars()` in `doc_parser/generate.py`. No action is needed in the `supplemental` dict for these.

| Variable | Source | Description |
|---|---|---|
| `deceased_full_name` | death certificate | Full legal name of the deceased |
| `account_holder_name` | death certificate | Alias for `deceased_full_name`; used by bank, utility, and telecom templates |
| `date_of_death` | death certificate | Formatted as "Month D, YYYY" |
| `date_of_birth` | death certificate | Formatted as "Month D, YYYY" |
| `ssn_last4` | death certificate | Last 4 digits of SSN only |
| `deceased_ssn` | death certificate | Masked SSN: "XXX-XX-{last4}" |
| `county` | death certificate | County of death |
| `state` | death certificate | State of death |
| `surviving_spouse` | death certificate | Surviving spouse name, or empty string |
| `sender_name` | filer | Name of the person submitting the letter |
| `sender_relationship` | filer | Relationship to deceased — drives per-template conditionals (`"surviving_spouse"`, `"executor"`, `"administrator"`) |
| `sender_address` | filer | Filer's mailing address |

---

## Per-Template Supplemental Variables

Variables that must be supplied in the `supplemental` dict passed to `generate_letters()`.

### ssa.html — Social Security Administration
*Address hardcoded. No supplemental variables required.*

All content is derived from auto-filled variables.

---

### medicare.html — Centers for Medicare & Medicaid Services
*Address hardcoded.*

| Variable | Required | Description |
|---|---|---|
| `medicare_beneficiary_id` | Yes | Medicare Beneficiary Identifier (MBI) printed on the Medicare card |

---

### bank.html — Bank / Financial Institution
*Address supplied via variable.*

| Variable | Required | Description |
|---|---|---|
| `bank_name` | Yes | Full legal name of the bank, e.g. `"Chase Bank"` |
| `mailing_address_for_death_cert` | Yes | Mailing address for the estate/death certificate department |
| `account_numbers` | Yes | Account number(s) — string or list, e.g. `"****1234"` or `["****1234", "****5678"]` |
| `sender_capacity` | Yes | Legal role of the sender, e.g. `"Executor of the Estate"`, `"Surviving Spouse"` |
| `estate_attorney_name` | No | Attorney name and contact info; included as a closing note if present |

---

### utility.html — Utility Company
*Address supplied via variable.*

| Variable | Required | Description |
|---|---|---|
| `utility_company_name` | Yes | Name of the utility, e.g. `"Duke Energy"`, `"TECO Energy"` |
| `account_number` | Yes | Account number on the utility bill |
| `service_address` | Yes | Address where service is provided |
| `forwarding_address` | Yes | Address for final bill and correspondence |

---

### telecom.html — Telecom / Wireless Carrier
*Address supplied via variable.*

| Variable | Required | Description |
|---|---|---|
| `telecom_company_name` | Yes | Name of the carrier, e.g. `"AT&T"`, `"Verizon"`, `"T-Mobile"` |
| `account_number` | Yes | Account number |
| `phone_numbers_on_account` | Yes | Phone number(s) on the account, e.g. `"(813) 555-0100"` |
| `service_address` | Yes | Address associated with the account |
| `porting_or_cancel_preference` | Yes | Instruction for line disposition, e.g. `"Port number (813) 555-0100 to [carrier] before cancellation."` or `"Cancel all lines immediately."` |
| `forwarding_address` | Yes | Address for final bill and correspondence |

---

### brokerage.html — Brokerage / Investment Account
*Address supplied via variables.*

| Variable | Required | Description |
|---|---|---|
| `institution_name` | Yes | e.g. `"Fidelity Investments"`, `"Charles Schwab & Co., Inc."` |
| `institution_dept` | Yes | e.g. `"Transition Services Department"` |
| `institution_address1` | Yes | Street or P.O. box line |
| `institution_address2` | Yes | City, state, zip |
| `account_numbers` | Yes | List of account number strings, e.g. `["Z12-345678", "X98-765432"]` |
| `account_types` | Yes | List of account type strings matching `account_numbers`, e.g. `["Individual Brokerage", "Traditional IRA"]` |
| `letters_testamentary_date` | No | Date Letters Testamentary were issued, e.g. `"January 15, 2025"` |
| `probate_court` | No | Full court name, e.g. `"Superior Court of Hillsborough County, Florida"` |
| `estate_ein` | No | Estate EIN if obtained, e.g. `"XX-XXXXXXX"` |

---

### usaa.html — USAA (Bank & Insurance)
*Address hardcoded.*

| Variable | Required | Description |
|---|---|---|
| `usaa_member_number` | Yes | USAA member number of the deceased |
| `deceased_service_branch` | Yes | e.g. `"United States Army"`, `"United States Marine Corps"` |
| `deceased_service_dates` | Yes | e.g. `"1982–2004"` |
| `usaa_bank_account_numbers` | No | List of banking account numbers |
| `usaa_policy_numbers` | No | List of insurance policy numbers |
| `letters_testamentary_date` | No | Date Letters Testamentary were issued |
| `probate_court` | No | Full court name |
| `estate_ein` | No | Estate EIN if obtained |

---

### credit_union.html — Credit Union
*Address supplied via variables.*

| Variable | Required | Description |
|---|---|---|
| `institution_name` | Yes | e.g. `"Suncoast Credit Union"`, `"Navy Federal Credit Union"` |
| `institution_dept` | Yes | e.g. `"Member Services / Estate Department"` |
| `institution_address1` | Yes | Street or P.O. box line |
| `institution_address2` | Yes | City, state, zip |
| `account_numbers` | Yes | List of account number strings |
| `account_types` | Yes | List of account type strings matching `account_numbers` |
| `member_number` | No | Credit union member number (often separate from account numbers) |
| `letters_testamentary_date` | No | Date Letters Testamentary were issued |
| `probate_court` | No | Full court name |
| `estate_ein` | No | Estate EIN if obtained |

---

### subscriptions.html — Subscription Services
*Address supplied via variables. Intentionally less formal; photocopy of death certificate is sufficient.*

| Variable | Required | Description |
|---|---|---|
| `institution_name` | Yes | e.g. `"Spotify AB"`, `"Netflix, Inc."`, `"Apple Inc."` |
| `institution_dept` | Yes | e.g. `"Customer Support / Bereavement Team"` |
| `institution_address1` | Yes | Street or P.O. box (most responses handled online) |
| `institution_address2` | Yes | City, state, zip |
| `account_email` | No | Email address associated with the account |
| `subscription_name` | No | e.g. `"Spotify Premium"`, `"Netflix Standard with Ads"` |
| `prepaid_balance_inquiry` | No | Boolean; include refund request paragraph if `true` |
| `apple_legacy_contact` | No | Boolean; include Apple Legacy Contact language if `true` |

---

### mortgage.html — Mortgage Servicer
*Address supplied via variables.*

| Variable | Required | Description |
|---|---|---|
| `institution_name` | Yes | e.g. `"Mr. Cooper (Nationstar Mortgage LLC)"` |
| `institution_dept` | Yes | e.g. `"Loss Mitigation / Successor in Interest Department"` |
| `institution_address1` | Yes | Street or P.O. box line |
| `institution_address2` | Yes | City, state, zip |
| `loan_number` | Yes | Mortgage loan number |
| `property_address` | Yes | Full address of the mortgaged property |
| `property_relationship` | No | e.g. `"joint owner with right of survivorship"` or `"sole heir and beneficiary under the will"` |
| `letters_testamentary_date` | No | Date Letters Testamentary were issued |
| `probate_court` | No | Full court name |
| `currently_delinquent` | No | Boolean; include payment status note if `true` |
| `requesting_assumption` | No | Boolean; include mortgage assumption request if `true` |

---

### irs.html — IRS (Final Return Cover Letter)
*This is a cover letter accompanying Form 1040 and/or Form 56, NOT a standalone death notification. Mail to the IRS Service Center for the deceased's state of residence.*

| Variable | Required | Description |
|---|---|---|
| `deceased_ssn` | Yes | Full SSN (auto-filled as `XXX-XX-{last4}`; supply full SSN in supplemental to override) |
| `tax_year` | Yes | Tax year of the final return, e.g. `"2024"` |
| `irs_service_center` | Yes | Full address line, e.g. `"Internal Revenue Service, Austin, TX 73301-0215"` |
| `form_56_attached` | No | Boolean; reference Form 56 if `true` |
| `form_1310_attached` | No | Boolean; reference Form 1310 if `true` |
| `form_4810_attached` | No | Boolean; include prompt assessment request if `true` |
| `estate_ein` | No | Estate EIN if obtained |
| `refund_due` | No | Boolean; include refund note if `true` |
| `balance_due` | No | Boolean; include payment note if `true` |
| `prior_years_unfiled` | No | Boolean; note prior-year returns enclosed if `true` |

---

### amazon.html — Amazon
*Operated via email to bereavement-support-cs@amazon.com. This template is formatted as the email body.*

| Variable | Required | Description |
|---|---|---|
| `account_email` | Yes | Email address associated with the Amazon account |
| `has_gift_card_balance` | No | Boolean; include gift card balance inquiry if `true` |
| `has_prime_membership` | No | Boolean; reference Prime cancellation/refund if `true` |
| `has_pending_orders` | No | Boolean; request order cancellation if `true` |
| `has_seller_account` | No | Boolean; add Amazon Seller note if `true` |

---

### linkedin.html — LinkedIn
*No mailing address. Requests are submitted via LinkedIn's Help Center online form. This template serves as a companion record.*

| Variable | Required | Description |
|---|---|---|
| `profile_url` | Yes | Full URL of the LinkedIn profile |
| `account_email` | Yes | Email address registered to the LinkedIn account |
| `action_requested` | Yes | `"memorialize"` or `"close"` |
| `linkedin_premium` | No | Boolean; include Premium subscription note if `true` |
| `premium_payment_source` | No | e.g. `"American Express ending 1234"` (for billing stoppage) |

---

### life_insurance.html — Life Insurance Company
*Address supplied via variables.*

| Variable | Required | Description |
|---|---|---|
| `institution_name` | Yes | e.g. `"MetLife"`, `"New York Life Insurance Company"` |
| `institution_dept` | Yes | e.g. `"Life Insurance Claims Department"` |
| `institution_address1` | Yes | Street or P.O. box line |
| `institution_address2` | Yes | City, state, zip |
| `policy_number` | Yes | Primary policy number |
| `policy_type` | Yes | e.g. `"term life"`, `"whole life"`, `"universal life"`, `"group life"` |
| `additional_policies` | No | List of dicts for multiple policies: `[{"number": "...", "type": "..."}]` |
| `letters_testamentary_date` | No | Date Letters Testamentary were issued |
| `probate_court` | No | Full court name |
| `estate_ein` | No | Estate EIN if obtained |
| `policy_issue_date` | No | Date policy was issued; flags contestability period if recent |
| `death_was_accidental` | No | Boolean; include AD&D inquiry if `true` |
| `death_outside_us` | No | Boolean; note death occurred abroad if `true` |
| `group_policy` | No | Boolean; use employer group policy language if `true` |
| `employer_name` | No | Required if `group_policy` is `true` |

---

### pension.html — Pension / Retirement Plan Administrator
*Address supplied via variables.*

| Variable | Required | Description |
|---|---|---|
| `institution_name` | Yes | e.g. `"California Public Employees' Retirement System (CalPERS)"` |
| `institution_dept` | Yes | e.g. `"Pension Benefits / Survivor Benefits Department"` |
| `institution_address1` | Yes | Street or P.O. box line |
| `institution_address2` | Yes | City, state, zip |
| `plan_name` | Yes | e.g. `"ABC Corp 401(k) Plan"`, `"State Teachers Retirement Plan"` |
| `participant_id` | Yes | Employee ID, member number, or plan participant ID |
| `employer_name` | Yes | Employing organization that sponsored the plan |
| `plan_type` | No | e.g. `"401(k)"`, `"pension"`, `"defined benefit"`, `"403(b)"` |
| `letters_testamentary_date` | No | Date Letters Testamentary were issued |
| `probate_court` | No | Full court name |
| `estate_ein` | No | Estate EIN if obtained |
| `deceased_was_retired` | No | Boolean; use retired-participant language if `true` |
| `benefits_were_active` | No | Boolean; note ongoing payments at time of death if `true` |
| `optional_forms_period` | No | Boolean; include ERISA QJ&SA language if `true` (vested but not yet retired) |

---

## Variable Usage Matrix

Variables used across multiple templates. Useful for building a shared `supplemental` dict.

| Variable | Templates |
|---|---|
| `account_email` | amazon, linkedin, subscriptions |
| `account_number` | utility, telecom |
| `account_numbers` | bank, brokerage, credit_union |
| `estate_ein` | brokerage, usaa, credit_union, irs, life_insurance, pension |
| `forwarding_address` | utility, telecom |
| `institution_address1` | brokerage, credit_union, subscriptions, mortgage, life_insurance, pension |
| `institution_address2` | brokerage, credit_union, subscriptions, mortgage, life_insurance, pension |
| `institution_dept` | brokerage, credit_union, subscriptions, mortgage, life_insurance, pension |
| `institution_name` | brokerage, credit_union, subscriptions, mortgage, life_insurance, pension |
| `letters_testamentary_date` | brokerage, usaa, credit_union, mortgage, irs, life_insurance, pension |
| `probate_court` | brokerage, usaa, credit_union, mortgage, irs, life_insurance, pension |
| `service_address` | utility, telecom |
