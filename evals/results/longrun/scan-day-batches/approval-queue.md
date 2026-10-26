# Approval queue

Every external action waits here until you approve it.

---

### q-10141435-northwind-onboarding-checklist
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-direct
- created: 2026-10-14T14:35:00Z
- short_summary: Outline for the Northwind onboarding checklist, due Fri 2026-10-16
- proposed_tool_call: Northwind onboarding checklist (for their IT team, starting week of 2026-10-19)
  * 1. Before kickoff
  * - Confirm Northwind IT contacts and who owns each item: [names]
  * - Confirm start date for their IT team: [date]
  * 2. Staging tenant
  * - Priya Natarajan sets up the Northwind staging tenant on 2026-10-15
  * - Share tenant access details with Northwind IT: [link/credentials process]
  * - Confirm Northwind IT can log in: [owner, date]
  * 3. SSO setup
  * - Provide the SSO runbook (Dana updating, due Wed 2026-10-21)
  * - Collect identity provider details from Northwind: [IdP, metadata]
  * - Test SSO login in staging: [owner, date]
  * 4. Access and users
  * - Admin accounts and roles: [details]
  * - User provisioning approach: [details]
  * 5. Support and next steps
  * - Point of contact at our side: [name]
  * - Check-in after first week: [date]
  * Note: items marked in brackets were not covered in the meeting and need to be filled in before sending to Tomas Weber.
- task: default:action:northwind-onboarding-checklist
- context: Task: Write the Northwind onboarding checklist. Sources: tr-added-0001.

### q-10141435-northwind-sso-runbook-update
- status: pending
- action_type: self_do
- priority: medium
- drafted_by: cos-direct
- created: 2026-10-14T14:35:00Z
- short_summary: Outline for the updated SSO runbook for Northwind, due Wed 2026-10-21
- proposed_tool_call: Steps to update the SSO runbook for Northwind
  * 1. Open the previous SSO runbook Dana wrote and copy it as the base for Northwind: [link to last runbook]
  * 2. Replace customer-specific details with Northwind's: tenant name, domains, contacts: [Northwind details]
  * 3. Update the prerequisites section: staging tenant (Priya Natarajan sets it up 2026-10-15), identity provider info needed from Northwind IT: [IdP, metadata format]
  * 4. Review each configuration step against the current product and fix anything out of date: [changes since last runbook]
  * 5. Add a test section: how to verify SSO login in staging and what to check on failure: [test accounts]
  * 6. Add a rollback and troubleshooting section: [known issues]
  * 7. Have Tomas Weber review, then share with Northwind IT by 2026-10-21 (next Wednesday): [delivery method]
- task: default:action:northwind-sso-runbook-update
- context: Task: Update the SSO runbook for Northwind. Sources: tr-added-0001.
