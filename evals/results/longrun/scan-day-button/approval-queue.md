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
- proposed_tool_call: Northwind onboarding checklist (for their IT team, who start next week)
  * 1. Before day one
  * - Staging tenant: Priya is setting it up 2026-10-15. Confirm it is ready: [tenant name/URL]
  * - Named contacts: Northwind IT lead [name]; Kestrel owner [name]
  * - Access list: who at Northwind needs accounts [names/roles]
  * 2. SSO setup
  * - Link to the updated SSO runbook (due Wed 2026-10-21): [link]
  * - Info Northwind must provide: [identity provider, metadata, domains]
  * 3. Staging tenant checks
  * - Login works for each Northwind user: [ ]
  * - Basic functions verified: [list]
  * 4. Timeline
  * - Northwind IT start: week of 2026-10-19 [exact date]
  * - Production move: [date]
  * 5. Support
  * - Where to ask questions: [channel/email]
  * - Escalation path: [name]
  * Next: fill each blank with Priya and Tomas, then send to Tomas by Friday.
- task: kestrel:action:northwind-onboarding-checklist
- context: Task: Write the Northwind onboarding checklist. Sources: tr-added-0001.

### q-10141435-sso-runbook-update
- status: pending
- action_type: self_do
- priority: medium
- drafted_by: cos-direct
- created: 2026-10-14T14:35:00Z
- short_summary: Steps to update the SSO runbook for Northwind, due Wed 2026-10-21
- proposed_tool_call: Update the SSO runbook for Northwind (Dana wrote the last version)
  * 1. Open the previous SSO runbook: [link/location].
  * 2. Copy it to a new version titled for Northwind: [doc name].
  * 3. Replace customer-specific details with Northwind's: [identity provider, domains, tenant name/URL, contacts].
  * 4. Re-check each step against the current staging tenant once Priya has set it up (2026-10-15). Note any step that changed: [list].
  * 5. Add a Northwind test section: sign-in test user, expected result, common failures and fixes: [details].
  * 6. Add rollback or escalation steps and who to contact: [name].
  * 7. Link the finished runbook from the Northwind onboarding checklist.
  * 8. Send to Tomas Weber for review by Wed 2026-10-21.
- task: kestrel:action:sso-runbook-update
- context: Task: Update the SSO runbook for Northwind. Sources: tr-added-0001.

### q-10141435-reply-sam-deploy-status
- status: pending
- action_type: message_send
- priority: low
- drafted_by: cos-direct
- created: 2026-10-14T14:35:00Z
- short_summary: Slack reply to Sam: deploy status [needs confirming]
- proposed_tool_call: email.send_message in group DM with Alex P. and Sam (mpdm-dana.k--alex.p--sam), with text: "Hi Sam, [yes, the deploy went out at [time] / not yet, expected [date/time]]. [Add any caveats or follow-up needed.]"
- task: kestrel:action:reply-sam-deploy-status
- context: Task: Reply to Sam: did the deploy go out?. Sources: sl-297135.

### q-10141705-northwind-maintenance-window-nov-15-conf
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-direct
- created: 2026-10-14T17:05:00Z
- short_summary: Email to Alex Brennan: confirm the Nov 15 maintenance window before the Oct 30 deadline
- proposed_tool_call: email.send to Alex Brennan <alex.brennan@northwind.example>, re "Re: Maintenance window", with text: "Hi Alex, confirming the maintenance window on November 15, from [start time] to [end time] [time zone]. Expected impact for your clinics: [impact, e.g. services affected and for how long]. This gives you time to warn them ahead of Oct 30. I will let you know right away if anything changes. Thanks, Dana"
- task: kestrel:action:northwind-maintenance-window-nov-15-confirm
- context: Task: Confirm the Nov 15 maintenance window to Alex Brennan at Northwind Clinics. Sources: em-962935.
