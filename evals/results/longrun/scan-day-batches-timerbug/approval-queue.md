# Approval queue

Every external action waits here until you approve it.

---

### q-10141435-northwind-onboarding-checklist
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-direct
- created: 2026-10-14T14:35:00Z
- short_summary: Outline for the Northwind onboarding checklist, due Friday 2026-10-16
- proposed_tool_call: Northwind onboarding checklist (for their IT team, starting next week)
  * 1. Before kickoff
  * - Confirm Northwind IT contacts: [names and emails]
  * - Confirm kickoff date: [date]
  * 2. Environment setup
  * - Staging tenant: Priya Natarajan is setting this up on 2026-10-15. Confirm it is ready: [yes/no]
  * - Tenant URL and admin access for Northwind: [details]
  * 3. SSO setup
  * - Identity provider details needed from Northwind: [list]
  * - Follow the Northwind SSO runbook (Dana is updating it, due Wednesday 2026-10-21)
  * 4. Access and accounts
  * - Admin and user accounts to create: [list]
  * - Roles and permissions: [details]
  * 5. Validation
  * - Test sign-in on staging: [owner]
  * - Sign-off from Northwind IT: [name]
  * 6. Open items and owners
  * - [item] / [owner] / [date]
  * Send to Tomas Weber for review by Friday 2026-10-16, then to Northwind.
- task: default:action:northwind-onboarding-checklist
- context: Task: Write the Northwind onboarding checklist. Sources: tr-added-0001.

### q-10141435-northwind-sso-runbook-update
- status: pending
- action_type: self_do
- priority: medium
- drafted_by: cos-direct
- created: 2026-10-14T14:35:00Z
- short_summary: Outline for the updated SSO runbook for Northwind, due Wednesday 2026-10-21
- proposed_tool_call: SSO runbook update for Northwind (base: the last SSO runbook Dana wrote)
  * 1. Scope and audience
  * - Northwind IT team onboarding, starting next week
  * - Environment: staging tenant set up by Priya Natarajan
  * 2. Prerequisites
  * - Staging tenant ready: [confirm]
  * - Northwind identity provider and admin contact: [details]
  * - Required metadata, certificates, and URLs: [list]
  * 3. Configuration steps
  * 1. Review the previous runbook and mark steps that changed: [changes]
  * 2. Create the SSO connection in the Northwind tenant: [steps]
  * 3. Enter the identity provider settings: [steps]
  * 4. Map user attributes and roles: [mapping]
  * 5. Assign test users: [list]
  * 4. Testing
  * - Test sign-in and sign-out on staging: [expected results]
  * - Failure cases and checks: [list]
  * 5. Troubleshooting
  * - Common errors and fixes from the last runbook: [items]
  * 6. Rollback and support contacts
  * - Rollback steps: [steps]
  * - Contacts: [names]
  * Share with Tomas Weber by Wednesday 2026-10-21.
- task: default:action:northwind-sso-runbook-update
- context: Task: Update the SSO runbook for Northwind. Sources: tr-added-0001.
