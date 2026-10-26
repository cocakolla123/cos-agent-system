# Approval queue

Every external action waits here until Dana approves it. Nothing is sent,
posted or changed without that click.

### example-id
- status: pending
- action_type: message_send
- proposed_tool_call: (schema example, not an entry)

---

### q-1013-tomas-deprecation
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-drafter
- created: 2026-10-13T08:40:00-07:00
- short_summary: Email to Tomas: first draft of the API v1 deprecation notice (he asked for it by today)
- proposed_tool_call: gmail-work.send to Tomas, re "Deprecation notice", with text: "Hi Tomas, here is a first draft of the v1 deprecation notice: API v1 will stop accepting requests on [date]. Please move to the v2 endpoints before then; the migration guide covers the changes. Tell me the date and anything to add, and I will finalize it today."
- task: kestrel:action:api-v1-deprecation-notice-text
- context: Task: Write API v1 deprecation notice text for Tomas (due 2026-10-13). Source: his email of Oct 8, 'I need the API v1 deprecation notice text by next Tuesday.'

### q-1013-alex-cron
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-drafter
- created: 2026-10-13T08:44:00-07:00
- short_summary: Slack reply to Alex in #proj-billing-migration: the billing cron schedule (due Oct 16)
- proposed_tool_call: slack.send_message in #proj-billing-migration, thread of Oct 12, with text: "Confirming the billing job schedule ahead of the cutover: [schedule]. Shout if the cutover week changes."
- task: kestrel:action:billing-cron-schedule-confirm
- context: Task: Confirm the cron schedule for the billing jobs for Alex (due 2026-10-16). Source: '@dana.k can you confirm the cron schedule for the billing jobs by Oct 16? we cut over the week after.'

### q-1013-laptop-swap
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-drafter
- created: 2026-10-13T08:45:00-07:00
- short_summary: Book the laptop swap on the IT booking page (was due Oct 9)
- proposed_tool_call: 1. Open the Kestrel IT booking page (linked in IT's Sep 23 mail from it@kestrel.example).
  * 2. Pick a laptop swap slot.
  * 3. Mark this handled. No connector can book it, so this one is yours.
- task: kestrel:action:laptop-refresh-booking
- context: Task: Book laptop swap appointment with IT (due 2026-10-09, overdue). Source: Kestrel IT, it@kestrel.example, Sep 23. Not the look-alike 'password expires' mail from kestrel-helpdesk.example on Sep 22, which was set aside as phishing.

### q-1013-grace-resume
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-drafter
- created: 2026-10-13T08:47:00-07:00
- short_summary: Email to Grace Liu (Halcyon Talent) with the updated resume [job-search workspace]
- proposed_tool_call: gmail-personal.send to Grace Liu, re "Updated resume", with text: "Hi Grace, sorry this is late. My updated resume is attached. Happy to talk whenever suits you."
- task: job-search:action:halcyon-updated-resume
- context: Job-search workspace: drafted from the personal mailbox, never the work account. Task: Send updated resume to Grace Liu (asked for it by Oct 1).

### q-1012-alex-ack
- status: approved
- action_type: message_send
- priority: medium
- drafted_by: cos-drafter
- created: 2026-10-12T16:10:00-07:00
- short_summary: Slack: acknowledge Alex's cron question (will confirm by Oct 16)
- proposed_tool_call: slack.send_message in #proj-billing-migration, thread of Oct 12, with text: "On it, will confirm by Thursday."
- task: kestrel:action:billing-cron-schedule-confirm
- context: Approved by Dana on Oct 12. The task itself stays open until the schedule is confirmed.

### q-1010-offsite-replyall
- status: rejected
- action_type: message_send
- priority: low
- drafted_by: cos-drafter
- created: 2026-10-10T11:00:00-07:00
- short_summary: Reply to the optional #general @channel about the offsite poll
- proposed_tool_call: slack.send_message in #general with text: "Count me in for Thursday."
- context: Rejected by Dana: the @channel was optional; no reply needed.

### q-1013-fernhill-milestone-1-release
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Marcus: ask him to release the $1,200 Milestone 1 payment
- proposed_tool_call: gmail-freelance.send to Marcus Bell, re "Milestone 1 release: Shopify inventory sync", with text: "Hi Marcus, thanks again for the kind words on the sync. I submitted Milestone 1 (Sync MVP, $1,200) on Aug 20, and Upwork still shows it as not approved or released. Could you approve and release it when you get a chance? If anything in the deliverable needs a change first, let me know and I'll sort it out. Thanks, Dana"
- task: freelance:action:fernhill-milestone-1-release
- context: Task: Milestone 1 ($1,200) payment still unreleased by Fernhill Goods. Sources: em-402082, em-877588.

### q-1013-fernhill-milestone-2-low-stock-alerts
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Marcus: answer his Oct 2 question on the Oct 24 low-stock alerts
- proposed_tool_call: gmail-freelance.send to Marcus Bell, re "Milestone 2: low-stock alerts", with text: "Hi Marcus, thanks for checking in. The low-stock alerts are [on track / status] for the Oct 24 due date. [Progress so far and what is left]. I will send the delivery for your review by [date]. Noted that the Slack failed-order notification is off the list, since your intern is handling it. Thanks, Dana"
- task: freelance:action:fernhill-milestone-2-low-stock-alerts
- context: Task: Deliver Milestone 2 low-stock alerts for Fernhill Goods and reply to Marcus. Sources: em-270940, em-825899.

### q-1013-inv-0042-lumen-dental-payment
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Rosa: follow up on overdue INV-0042 ($2,400), reminder of Oct 6 unanswered
- proposed_tool_call: gmail-freelance.send to Rosa Lin, re "INV-0042: booking widget, now overdue", with text: "Hi Rosa, I'm glad the widget is working well for your patients. INV-0042 ($2,400) was due Sep 29, and I sent a reminder to ap@lumendental.example on Oct 6 without a reply. Could you check with accounts and let me know the payment date? I'm happy to resend the invoice or fill in any vendor forms they need. Thanks, Dana"
- task: freelance:action:inv-0042-lumen-dental-payment
- context: Task: Collect INV-0042 ($2,400) from Lumen Dental (reminder sent Oct 6). Sources: em-815263, em-914019, em-819691.

### q-1013-nimbus-ops-upwork-invite-reply
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Reply to Nimbus Ops invite: give start date and rate for React ops dashboard
- proposed_tool_call: gmail-freelance.send to Nimbus Ops, re "React ops dashboard", with text: "Hi, thank you for the invitation, and I'm glad the Fernhill work stood out. I could start on [start date]. My rate for this project is [rate]. To scope it properly, could you share [details needed, e.g. current stack, timeline, number of dashboards]? Happy to set up a call at your convenience. Thanks, Dana"
- task: freelance:action:nimbus-ops-upwork-invite-reply
- context: Task: Reply to Nimbus Ops on Upwork with start date and rate. Sources: em-209864.

### q-1013-orbitlabs-api-audit-report
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Outline for the Orbit Labs API security audit report (API only, due Oct 15)
- proposed_tool_call: Outline for the audit report:
  * 1. Executive summary: scope, overall risk, top [number] findings
  * 2. Scope and method: public API only (Terraform review dropped per Priya, Oct 3); [testing dates and approach]
  * 3. Findings: for each, [title], severity, evidence, impact, fix
  * 4. Prioritized remediation plan
  * 5. Appendix: [endpoints reviewed, tools used]
  * Then email the report to Priya Raman, referencing the $3,000 fee due on delivery per the SOW.
- task: freelance:action:orbitlabs-api-audit-report
- context: Task: Deliver the API security audit report to Orbit Labs ($3,000 on delivery; Terraform review dropped). Sources: em-193877, em-841372, em-186865, em-900736.

### q-1013-corvid-final-round-slot
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Corvid Recruiting: ask for the available final-round slots
- proposed_tool_call: gmail-personal.send to Corvid Systems Recruiting, re "Final round", with text: "Hi, thank you for the update. I'd like to book my final-round interview before the Oct 23 deadline. Could you send the available slots, or a scheduling link? I'll confirm one right away. Best, Dana Kowalski"
- task: job-search:action:corvid-final-round-slot
- context: Task: Pick a Corvid Systems final-round interview slot. Sources: em-155575.

### q-1013-quillmark-offer-decision
- status: pending
- action_type: self_do
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Decision worksheet for the Quillmark Staff Engineer offer (reply due Oct 24)
- proposed_tool_call: Decision worksheet:
  * 1. Pull terms from the offer letter: base [amount], equity [amount], bonus [amount], start date [date], location/remote [terms].
  * 2. Compare against the Tidewater Analytics offer on pay, role scope, growth and team.
  * 3. List open questions for Hana at Quillmark Talent: [questions].
  * 4. Decide: accept, negotiate, or decline.
  * 5. Reply to Hana at talent@quillmark.example from the personal account with the decision, or ask for more time if still comparing [date].
- task: job-search:action:quillmark-offer-decision
- context: Task: Decide on the Quillmark Staff Engineer offer. Sources: em-881423.

### q-1013-tidewater-offer-sign
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Steps to review and sign the Tidewater Analytics offer in Handshake by Oct 16
- proposed_tool_call: 1. Open the Tidewater Analytics offer for Senior Data Platform Engineer in Handshake.
  * 2. Check base [amount], equity [amount], bonus [amount], start date [date], benefits, and any non-compete or IP clauses.
  * 3. Note any questions or negotiation points: [points]. Send them to Jonah Pike before signing.
  * 4. Compare with the Quillmark offer before committing.
  * 5. Sign in Handshake by Oct 16, or ask Jonah for an extension if still deciding.
- task: job-search:action:tidewater-offer-sign
- context: Task: Review and sign the Tidewater Analytics offer (Senior Data Platform Engineer). Sources: em-314423.

### q-1013-analytics-replica-access-request
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to IT: second follow-up on analytics replica access, blocking RTA-90
- proposed_tool_call: gmail-work.send to Kestrel IT, re "RE: Access request: analytics replica", with text: "Hi IT, following up again on my Aug 5 request for read access to the analytics replica, and my Sep 8 nudge. I'm still blocked on RTA-90. Could you tell me the current status and who owns the approval? If you need anything from me, such as a manager approval or a ticket, let me know and I'll send it right away. Thanks, Dana"
- task: kestrel:action:analytics-replica-access-request
- context: Task: Get read access to the analytics replica (RTA-90). Sources: em-414920, em-890897.

### q-1013-api-field-list-for-lena
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Slack to Lena: send the promised API field list for the new settings screen
- proposed_tool_call: slack.send_message in D-dana-lena, thread of Sep 29, with text: "Hi Lena, sorry for the delay on the API field list for the new settings screen. Here it is: [field list with names, types, required or optional]. Let me know if anything is missing or unclear."
- task: kestrel:action:api-field-list-for-lena
- context: Task: Send Lena the API field list for the new settings screen. Sources: sl-099016.

### q-1013-churn-report-for-raj
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Outline for churn report from Raj's usage export (overdue)
- proposed_tool_call: Outline for the churn report. Source: usage export Raj put in the shared drive (Sep 30).
  * 1. Summary: churn rate [x]% for [period], top 3 findings
  * 2. Method: export used, date range, churn definition [definition]
  * 3. Churn by segment/plan [from export]
  * 4. Usage patterns of churned vs retained accounts
  * 5. At-risk accounts [list]
  * 6. Recommendations and next steps [owners]
  * This was promised for Fri Oct 2 and is overdue, so send Raj a heads-up with the new ETA [date] when it goes out.
- task: kestrel:action:churn-report-for-raj
- context: Task: Deliver the churn report to Raj (usage export received). Sources: sl-730238, sl-191520.

### q-1013-conference-budget-request
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Victor: conference budget request (fill blanks before sending)
- proposed_tool_call: gmail-work.send to Victor Hale, re "Re: Budget asks", with text: "Hi Victor, here is my conference budget request. Conference: [name, dates, location]. Attendees: [names]. Estimated cost: registration [amount], travel [amount], lodging [amount], total [amount]. Why it matters: [business reason]. Happy to adjust if needed. Thanks, Dana"
- task: kestrel:action:conference-budget-request
- context: Task: Send Victor the conference budget request. Sources: em-203825.

### q-1013-events-schema-change-signoff
- status: pending
- action_type: self_do
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Review steps and reply text for events schema sign-off (due Oct 21)
- proposed_tool_call: 1. Get the schema change proposal from Raj in #data-eng (link not in thread; ask if missing).
  * 2. Check: breaking changes for consumers [list], backward compatibility, migration/backfill plan, rollout date [date].
  * 3. Reply in the Oct 9 thread:
  * "@Raj Patel reviewed the events schema change. [Approved / Approved with changes: change]. Open concerns: [concerns or none]."
  * 4. Post before Oct 21.
- task: kestrel:action:events-schema-change-signoff
- context: Task: Sign off on the events schema change. Sources: sl-596047.

### q-1013-friday-status-update-ines
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Draft of Friday Oct 16 status email to Ines (send Friday)
- proposed_tool_call: Send Friday Oct 16 via work email to Ines, re "Weekly status". Update from last week's identical text before sending:
  * Status:
  * - Cron migration: [current progress]
  * - Load test: [current progress]
  * - Runbook: [current progress]
  * Blockers: [none / blocker]
  * The last three emails were word for word the same, so confirm each item is still accurate.
- task: kestrel:action:friday-status-update-ines
- context: Task: Send Ines the weekly Friday status update. Sources: sl-714506, em-198452.

### q-1013-iam-policy-diff-review
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Review checklist for the IAM policy diff, due Oct 15
- proposed_tool_call: 1. Open the IAM policy diff [link to PR or diff].
  * 2. List every permission added or widened. Flag wildcard actions or resources.
  * 3. For each change, confirm who needs it and why: [owner / ticket].
  * 4. Check removed permissions will not break [dependent services].
  * 5. Check no admin or cross-account access is added without a reason.
  * 6. Record findings: approve, or request changes with [specific items].
  * 7. Post the outcome in #platform for Ines by Oct 15.
- task: kestrel:action:iam-policy-diff-review
- context: Task: Review the IAM policy diff. Sources: sl-451347.

### q-1013-incident-doc-timeline-oct-7
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Timeline draft for the Oct 7 incident doc, overdue since Oct 8
- proposed_tool_call: Timeline, Oct 7 incident (times from #incidents timestamps)
  * - [time] Errors reported, [first symptom and who saw it]
  * - [time] Also seen on eu-west (Raj)
  * - [time] LB health checks flapping (Mei)
  * - [time] Some 502s still coming from the LB (Ines)
  * - [time] Errors dropping (Raj)
  * - [time] Stable (Sam)
  * Still to fill: [start time], [root cause], [fix applied], [end time], [owner of write-up]. Put the entries in timestamp order, then add to the doc and tell Ines.
- task: kestrel:action:incident-doc-timeline-oct-7
- context: Task: Add the timeline to the Oct 7 incident doc. Sources: sl-952803.

### q-1013-lena-bulk-edits-api
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Slack reply to Lena on whether the API will support bulk edits
- proposed_tool_call: slack.send_message in D-dana-lena, thread of Oct 12, with text: "Hi Lena, on bulk edits: [yes / no / not yet]. [Details: which endpoints or objects, limits, and timing if not yet available.] For the mocks due Friday, I'd plan on [what to assume]. Happy to talk it through if useful."
- task: kestrel:action:lena-bulk-edits-api
- context: Task: Answer Lena: will the API support bulk edits?. Sources: sl-441953.

### q-1013-lena-roster-timezone-names
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Slack reply to Lena on whether the roster API returns timezone names
- proposed_tool_call: slack.send_message in mpdm-dana.k--lena--mei, thread of Oct 8, with text: "Hi Lena, on the roster API: [yes / no] it returns each location's timezone names. [Field name and an example value, or what it returns instead.] That should cover what you need for the mock by Oct 14. Let me know if not."
- task: kestrel:action:lena-roster-timezone-names
- context: Task: Answer Lena: does the roster API return each location's timezone names?. Sources: sl-814778.

### q-1013-northwind-data-retention-policy
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Alex Brennan: check whether Northwind still needs the data retention policy and by when
- proposed_tool_call: gmail-work.send to Alex Brennan, re "RE: Data retention policy", with text: "Hi Alex, I promised to send Kestrel's data retention policy by Aug 28 and it has slipped past that date. Sorry about that. Do you still need it for your compliance audit? If so, what date works for you? I will get it to you by then. Thanks, Dana"
- task: kestrel:action:northwind-data-retention-policy
- context: Task: Send Northwind the data retention policy. Sources: em-304459, em-457894.

### q-1013-northwind-msa-redlines-legal
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Check-in to Kestrel Legal on LEG-55, Northwind MSA redlines
- proposed_tool_call: gmail-work.send to Kestrel Legal, re "RE: Northwind MSA redlines", with text: "Hi Legal, checking in on LEG-55, the Northwind MSA redlines. Could you let me know where it stands and when I can expect your review? If you need anything more from me, tell me and I'll send it. Thanks, Dana"
- task: kestrel:action:northwind-msa-redlines-legal
- context: Task: Legal review of the Northwind MSA redlines (LEG-55). Sources: em-079608, em-079390.

### q-1013-northwind-pentest-summary
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Alex Brennan confirming the pen-test summary by Oct 22
- proposed_tool_call: gmail-work.send to Alex Brennan, re "RE: Security documents", with text: "Hi Alex, thanks for the note. I'll send Kestrel's pen-test summary by Oct 22. [Add any handling terms, such as confidentiality, if needed.] Dana"
- task: kestrel:action:northwind-pentest-summary
- context: Task: Send Northwind the pen-test summary. Sources: em-493919, em-567301.

### q-1013-notifications-rfc-comments
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Outline of comments on the notifications RFC for Tomas (due Oct 16)
- proposed_tool_call: Comment outline, to post on the RFC before Oct 16 (review meeting is Oct 19):
  * 1. Overall take: [support / support with changes / concerns]
  * 2. Scope and goals: [comments]
  * 3. Design and API implications: [comments]
  * 4. Risks and open questions: [comments]
  * 5. Rollout and dependencies: [comments]
  * 6. Must-fix before the Oct 19 review: [list]
  * 7. Nice-to-haves: [list]
  * Then tell Tomas on Slack (D-dana-tomas) that the comments are in.
- task: kestrel:action:notifications-rfc-comments
- context: Task: Add comments on the notifications RFC for Tomas. Sources: em-612857, sl-019082, sl-842606.

### q-1013-pager-config-review
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Slack reply to Raj: pager config review slipped past Monday, giving a new date
- proposed_tool_call: slack.send_message in #platform, thread of Oct 9, with text: "Hi Raj, sorry, the pager config review slipped past Monday. I'll review it and send you my comments by [date]. If anything specific needs a look first, tell me and I'll start there."
- task: kestrel:action:pager-config-review
- context: Task: Look at the pager config for Raj. Sources: sl-752440.

### q-1013-plat-301-postmortem-inc-212
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Slack reply to Ines: is the INC-212 postmortem (PLAT-301) still needed, and by when
- proposed_tool_call: slack.send_message in #platform, thread of Jul 21, with text: "@Ines Moreau the INC-212 postmortem (PLAT-301) was due Jul 31 and is still open on my side. Do you still need it? If so, what date should I aim for? If not, I will close the ticket."
- task: kestrel:action:plat-301-postmortem-inc-212
- context: Task: Write postmortem for INC-212 queue outage (PLAT-301). Sources: jr-118347, jr-631212, sl-572837, sl-301137.

### q-1013-plat-322-cron-migration
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Plan to finish the PLAT-322 cron migration by Oct 16
- proposed_tool_call: PLAT-322 plan, due Oct 16 (In Progress):
  * 1. List cron jobs still on the old scheduler: [count and names].
  * 2. Migrate remaining jobs to scheduler v2: [jobs left].
  * 3. Verify each job's schedule and first run on v2: [results].
  * 4. Disable the old entries after verification.
  * 5. Update the ticket with [done / remaining] and tell Ines.
  * 6. If Oct 16 is at risk, flag it to Ines now with [new date].
  * Note: weekly status has said "no blockers" three weeks running, so add real progress to the next one.
- task: kestrel:action:plat-322-cron-migration
- context: Task: Migrate cron jobs to scheduler v2 (PLAT-322). Sources: jr-675642, jr-640577, sl-519027, em-624175.

### q-1013-plat-355-oncall-runbook
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Ines: PLAT-355 runbook missed Oct 9, proposing a new date
- proposed_tool_call: gmail-work.send to Ines Moreau, re "PLAT-355 on-call runbook", with text: "Hi Ines, the on-call runbook rewrite (PLAT-355) was due Oct 9 and is not finished. My weekly status said no blockers and should have flagged this sooner. Current state: [what is done and what remains]. I can deliver the full rewrite by [date]. Does that work, or do you need it sooner? Dana"
- task: kestrel:action:plat-355-oncall-runbook
- context: Task: Rewrite the on-call runbook (PLAT-355). Sources: jr-511559, sl-310094, em-198452.

### q-1013-plat-360-load-test-scheduler-v2
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Slack reply to Ines: status and new date for the scheduler v2 load test (PLAT-360)
- proposed_tool_call: slack.send_message in #platform, thread of Sep 15, with text: "Hi Ines, update on the scheduler v2 load test (PLAT-360), which was due Sep 30: [current status and any results so far]. I expect to finish by [date] and will post the results here before launch."
- task: kestrel:action:plat-360-load-test-scheduler-v2
- context: Task: Load test scheduler v2 (PLAT-360). Sources: jr-979917, cal-902993, em-624175.

### q-1013-plat-380-oncall-schedule-export
- status: pending
- action_type: self_do
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Plan for exporting the on-call schedule to calendars (PLAT-380, due Oct 30)
- proposed_tool_call: 1. Confirm with Alex Park which calendars to target and the export format: [calendars, format].
  * 2. Find the current on-call schedule source: [source].
  * 3. Build the export and test it with one rotation.
  * 4. Check that shifts and time zones show correctly: [time zone].
  * 5. Share the result with Alex and Ines Moreau.
  * 6. Update PLAT-380 in Jira, including the Oct 30 due date, which Jira still shows as Sep 22.
- task: kestrel:action:plat-380-oncall-schedule-export
- context: Task: Export the on-call schedule to calendars (PLAT-380). Sources: jr-851586, sl-035174.

### q-1013-plat-390-worker-pool-metrics-endpoint
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Slack reply to Alex: metrics endpoint moves to Nov 6 per Ines
- proposed_tool_call: slack.send_message in #platform, thread of Sep 24, with text: "Hi Alex, Ines confirmed the worker pool metrics endpoint (PLAT-390) can wait until Nov 6, so I'll focus on the load test first and deliver it by then. If you need it earlier, please check with Ines. I'll update the Jira due date too."
- task: kestrel:action:plat-390-worker-pool-metrics-endpoint
- context: Task: Metrics endpoint for the worker pool (PLAT-390). Sources: jr-937071, sl-559538, em-430585.

### q-1013-plat-410-close-gzip-ticket
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Steps to close PLAT-410 now that gzip is live in prod
- proposed_tool_call: 1. Open PLAT-410 'Enable gzip on API responses' in Jira.
  * 2. Add a comment: "Gzip on API responses is live in prod as of Sep 30. Closing."
  * 3. Move the status from To Do to Done.
  * 4. Add a link to the deploy or PR if you have it: [link].
- task: kestrel:action:plat-410-close-gzip-ticket
- context: Task: Close PLAT-410 (gzip on API responses is live in prod). Sources: jr-682416, sl-920234.

### q-1013-plat-420-roster-api-perf-benchmark
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Plan to run the roster perf benchmark Oct 14 and send latency numbers to Ines
- proposed_tool_call: 1. Use the 'Roster perf run' block on Oct 14 (13:00 to 15:00 UTC) to run the benchmark: [test setup].
  * 2. Record the latency results: [p50], [p95], [p99], plus request rate [rate].
  * 3. Reply to Ines Moreau in the #platform thread of Oct 5 with the numbers before Thursday's review.
  * 4. Attach the results to PLAT-420 and mark it Done.
- task: kestrel:action:plat-420-roster-api-perf-benchmark
- context: Task: Perf benchmark and latency numbers for the roster API (PLAT-420). Sources: jr-975465, sl-970188, cal-367911.

### q-1013-postgres-18-upgrade-plan
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Outline for the Postgres 18 upgrade plan, due before the Oct 20 planning meeting
- proposed_tool_call: Postgres 18 Upgrade Plan
  * 1. Goal and scope: [which clusters and services]
  * 2. Current state: [current Postgres version, extensions, sizes]
  * 3. Upgrade approach: [pg_upgrade or logical replication], with rationale
  * 4. Compatibility risks: [deprecated features, extension support, driver versions]
  * 5. Test plan: [staging rehearsal, performance comparison]
  * 6. Rollout sequence and downtime window: [dates]
  * 7. Rollback plan
  * 8. Owners, effort and timeline: [names, estimates]
  * 9. Open questions for the Oct 20 meeting
  * Send to Ines before the meeting.
- task: kestrel:action:postgres-18-upgrade-plan
- context: Task: Prepare a Postgres 18 upgrade plan for Ines before the planning meeting. Sources: em-897707.

### q-1013-q4-capacity-numbers
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Slack follow-up in #platform: are the Q4 capacity numbers still needed, and by when
- proposed_tool_call: slack.send_message in #platform, thread of Sep 21, with text: "I said I would put together the Q4 capacity numbers by Thursday and that did not happen. Does anyone still need them? If so, by when? I will plan around that date. If not, I will drop it."
- task: kestrel:action:q4-capacity-numbers
- context: Task: Put together the Q4 capacity numbers. Sources: sl-471926.

### q-1013-q4-growth-goals
- status: pending
- action_type: self_do
- priority: low
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Notes to prepare Q4 growth goals for the next 1:1 with Ines (no deadline)
- proposed_tool_call: Q4 Growth Goals, draft notes
  * 1. Where I want to grow: [skill or scope area]
  * 2. Goal 1: [goal], how I will measure it: [measure]
  * 3. Goal 2: [goal], measure: [measure]
  * 4. Support needed from Ines: [support]
  * 5. Link to Q4 planning and on-call load topics from the Sep 14 1:1
  * Bring to the next 1:1 with Ines. Low priority, no rush.
- task: kestrel:action:q4-growth-goals
- context: Task: Think about Q4 growth goals. Sources: doc-728329.

### q-1013-q4-platform-headcount-case
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Outline for the platform staffing case in the Q4 headcount doc (due Oct 19)
- proposed_tool_call: Add under the Platform section of the 'Q4 headcount justification' doc:
  * 1. Request: [number] roles, [role titles], start by [date]
  * 2. Current team and workload: [headcount], [on-call load], [open projects]
  * 3. Business case: [risks or delivery gaps without the hires, with numbers]
  * 4. Cost: [cost per role], [total]
  * 5. Impact if not approved: [consequences]
  * 6. Success measures: [metrics and dates]
  * Send Ines the link by Oct 19.
- task: kestrel:action:q4-platform-headcount-case
- context: Task: Write the platform staffing / hiring justification for Q4 headcount. Sources: em-927912, sl-919558, doc-715524.

### q-1013-queue-sharding-consumers
- status: pending
- action_type: self_do
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Work plan for building the queue sharding consumers (Alex does producers), due Oct 30
- proposed_tool_call: Queue sharding consumers plan
  * 1. Agree the shard key and message contract with Alex: [details]
  * 2. Design consumer assignment per shard: [approach]
  * 3. Implement consumers with retry and error handling: [details]
  * 4. Tests, including rebalancing and ordering: [cases]
  * 5. Integration test with Alex's producers: [date]
  * 6. Rollout and monitoring: [plan]
  * Target finish by Oct 30. Check in with Alex by [date] to confirm interfaces.
- task: kestrel:action:queue-sharding-consumers
- context: Task: Queue sharding: consumers side (Alex does producers). Sources: sl-074216, sl-732059.

### q-1013-regression-run-2-15
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Slack check-in to Mei on the release 2.15 regression run
- proposed_tool_call: slack.send_message in #qa, thread of Oct 6, with text: "Hi @mei, checking in on the 2.15 regression run. Do you have an ETA, and is there anything you need from me to move it along? Thanks for taking it."
- task: kestrel:action:regression-run-2-15
- context: Task: Regression run for release 2.15 (Dana asked Mei to take it). Sources: sl-598917.

### q-1013-renew-api-cert
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Steps to renew the api.kestrel.example TLS cert before Oct 30
- proposed_tool_call: 1. Confirm the current cert's expiry (Nov 2) and issuer for api.kestrel.example.
  * 2. Generate a new CSR or start renewal with [CA or provider].
  * 3. Complete validation: [method].
  * 4. Install the new cert on [servers or load balancer] by Oct 28, leaving a buffer before Oct 30.
  * 5. Check the chain and new expiry with a live request to api.kestrel.example.
  * 6. Reply to Raj in #platform that it is done, with the new expiry [date].
- task: kestrel:action:renew-api-cert
- context: Task: Renew the TLS certificate for api.kestrel.example. Sources: sl-463776, em-928365.

### q-1013-retry-policy-rfc
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Ines: is the retry-policy RFC still needed, and by when
- proposed_tool_call: gmail-work.send to Ines Moreau, re "Retry-policy RFC", with text: "Hi Ines, the retry-policy RFC has been carried over in the platform sync notes since the Sep 4 target and I have not delivered it. Is it still needed? If so, what date should I aim for? If priorities have changed, I will close it out. Thanks, Dana"
- task: kestrel:action:retry-policy-rfc
- context: Task: Draft the retry-policy RFC. Sources: doc-724835, doc-932366.

### q-1013-rota-api-430-csv-import-last-row
- status: pending
- action_type: self_do
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Fix plan for rota-api#430, CSV import dropping the last row (2.14 regression)
- proposed_tool_call: 1. Reproduce: import a CSV with [N] rows, with and without a trailing newline, and confirm the last row is missing.
  * 2. Find what changed in 2.14 in the import path: [commit or file].
  * 3. Root cause: [root cause].
  * 4. Fix the row handling so the final row is kept.
  * 5. Add regression tests: trailing newline, no trailing newline, single row.
  * 6. Open a PR referencing #430 and note the fix version [version].
- task: kestrel:action:rota-api-430-csv-import-last-row
- context: Task: Fix CSV import dropping the last row, reopened as a regression in 2.14 (rota-api#430). Sources: gh-059815.

### q-1013-rota-api-470-review-batch-shift-import
- status: pending
- action_type: self_do
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Review checklist for rota-api#470 Batch shift import (Raj's PR)
- proposed_tool_call: Check in rota-api#470 (imports shifts in batches of 500):
  * 1. Last partial batch is flushed, not dropped (compare rota-api#430).
  * 2. Boundary cases: 0, 1, 499, 500, 501 rows.
  * 3. A failure mid-batch: rollback or partial commit, and the error reported.
  * 4. Duplicate shifts and re-import behavior.
  * 5. Tests cover the above.
  * 6. Performance on a large file: [result].
  * Post comments on the PR and submit the review. Alex is out until Oct 23.
- task: kestrel:action:rota-api-470-review-batch-shift-import
- context: Task: Review rota-api#470 Batch shift import (taking over from Alex). Sources: gh-703371, sl-236789, sl-016050, em-992873.

### q-1013-rotate-leaked-aws-key
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Steps to rotate and revoke the AWS key leaked in kestrel/infra commit 9f2c1ab
- proposed_tool_call: 1. In AWS IAM, identify the access key from the GitHub alert and which user or role owns it.
  * 2. Create a replacement key and update every service that uses it: [services].
  * 3. Deactivate the leaked key, confirm nothing breaks, then delete it.
  * 4. Check CloudTrail for use of the old key since commit 9f2c1ab: [findings].
  * 5. Remove the secret from the repo and history as agreed with the team: [method].
  * 6. Close the secret scanning alert, then reply to Ines in the DM that it is done. This was due Oct 9, so say it ran late.
- task: kestrel:action:rotate-leaked-aws-key
- context: Task: Rotate the leaked AWS key. Sources: sl-599611.

### q-1013-rotate-ssh-keys
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Checklist to rotate my SSH keys before the Oct 23 deadline
- proposed_tool_call: 1. List where my current public keys are registered: [GitHub, servers, other services].
  * 2. Generate a new key pair with the key type the security policy requires: [type]. Protect it with a passphrase.
  * 3. Add the new public key to each service listed in step 1.
  * 4. Test login with the new key on each one.
  * 5. Remove the old public keys and delete the old private key.
  * 6. Finish before Oct 23 and confirm in the place the policy specifies: [where].
- task: kestrel:action:rotate-ssh-keys
- context: Task: Rotate SSH keys per the new security policy. Sources: sl-674548.

### q-1013-rta-101-timezone-bug-shift-export
- status: pending
- action_type: self_do
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Fix plan for reopened RTA-101: shift export timezone bug for Australia/Lord_Howe
- proposed_tool_call: 1. Reproduce: export shifts for a location in Australia/Lord_Howe and compare exported times with the in-app times.
  * 2. Check how the export converts offsets. Lord_Howe's offset and its daylight saving shift differ from most zones, so look for hardcoded whole-hour assumptions. Root cause: [root cause].
  * 3. Fix the conversion to use the IANA zone rules.
  * 4. Add tests for Lord_Howe, including dates around the daylight saving change: [dates].
  * 5. Update RTA-101 and ask Mei Tanaka to verify.
- task: kestrel:action:rta-101-timezone-bug-shift-export
- context: Task: Fix reopened timezone bug in shift export, Australia/Lord_Howe (RTA-101). Sources: jr-611362.

### q-1013-rta-130-northwind-rca-sep-2-outage
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Alex Brennan: is the Sep 2 outage RCA still needed, and by when
- proposed_tool_call: gmail-work.send to Alex Brennan, re "Outage on Sep 2", with text: "Hi Alex, I'm sorry for the delay on the RCA for the Sep 2 outage that took out scheduling at your clinics. Do you still need it? If so, could you tell me the date you need it by, and whether you want anything specific covered? I will get it to you by then. Dana"
- task: kestrel:action:rta-130-northwind-rca-sep-2-outage
- context: Task: Send Northwind the RCA for the Sep 2 outage (RTA-130). Sources: jr-310297, em-194870.

### q-1013-scheduler-v2-architecture-review
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email circulating the scheduler v2 design doc ahead of the Oct 22 review
- proposed_tool_call: gmail-work.send to Ines Moreau, Victor, Alex Park, re "Scheduler v2 design doc for the Oct 22 architecture review", with text: "Hi all, here is the design doc for the scheduler v2 architecture review on Oct 22: [design doc link]. Main points for discussion: [key decisions]. Please send comments before the review if you can. Dana"
- task: kestrel:action:scheduler-v2-architecture-review
- context: Task: Present the scheduler v2 architecture review on Oct 22; circulate the design doc two days before. Sources: cal-396784.

### q-1013-scheduler-v2-launch-checklist-infra
- status: pending
- action_type: self_do
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Outline of infra steps to add to the scheduler v2 launch checklist
- proposed_tool_call: Add an "Infra" section to the launch checklist:
  * 1. Feature flag: confirm it is set up and off by default (Lena reports it is ready).
  * 2. Rollout stages: 10%, then 50%, then 100%. For each stage, record the go criteria [metrics and thresholds], the owner [name], and the date [date].
  * 3. Monitoring and alerts to watch during rollout: [dashboards, alerts].
  * 4. Rollback steps: [steps, who decides].
  * 5. Capacity and config changes before launch: [items].
  * 6. Infra sign-off: [name].
  * Due Oct 19. Then reply in the #proj-scheduler-v2 thread with the link.
- task: kestrel:action:scheduler-v2-launch-checklist-infra
- context: Task: Update the scheduler v2 launch checklist with the infra steps. Sources: sl-065253.

### q-1013-security-awareness-training
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to People Team: confirm the overdue security training is still open and agree a completion date
- proposed_tool_call: gmail-work.send to Kestrel People Team, re "RE: Overdue: security awareness training", with text: "Hi, my annual security awareness training was due Sep 15 and is still incomplete. Is it still open for me to finish, and what is the latest date I can complete it by? I will do it by [date]. Thanks, Dana"
- task: kestrel:action:security-awareness-training
- context: Task: Complete the mandatory annual security awareness training. Sources: em-914960.

### q-1013-september-timesheet
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Steps to submit the overdue September timesheet
- proposed_tool_call: 1. Open the timesheet system: [link].
  * 2. Select the September period.
  * 3. Enter hours for each working day: [hours per day], including leave or holidays: [dates].
  * 4. Check the total against the month: [total hours].
  * 5. Submit it today. It was due Oct 2.
  * 6. If the system is locked, email the People Team (people@kestrel.example) to reopen September.
- task: kestrel:action:september-timesheet
- context: Task: Submit the September timesheet. Sources: em-993252.

### q-1013-soc2-backup-restore-evidence
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Ines: apologize for the late backup restore evidence and confirm the date the SOC 2 audit needs it
- proposed_tool_call: gmail-work.send to Ines Moreau, re "RE: SOC 2 evidence", with text: "Hi Ines, I am sorry the backup restore test evidence is late. The Sep 25 date has passed. Do you still need it for the SOC 2 audit, and what is the latest date you can use? I will send it by then: [date]. Thanks, Dana"
- task: kestrel:action:soc2-backup-restore-evidence
- context: Task: Send Ines the backup restore test evidence for SOC 2 (access review export already sent). Sources: em-029847, em-766288, em-892765.

### q-1013-stratus-renewal-quote
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Priya: follow up on the 50-seat renewal quote requested Aug 18
- proposed_tool_call: gmail-work.send to Priya, re "Renewal quote", with text: "Hi Priya, I asked on Aug 18 for the renewal quote for our 50-seat plan and only got an automatic acknowledgment. Could you send the quote, or tell me when to expect it? If the renewal date is coming up on your side, please let me know that too. Thanks, Dana"
- task: kestrel:action:stratus-renewal-quote
- context: Task: Get the 50-seat renewal quote from Priya at Stratus Monitoring. Sources: em-801289, em-661530.

### q-1013-v1-migration-guide
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Tomas: is the v1 customer migration guide still needed, and by when
- proposed_tool_call: gmail-work.send to Tomas Reyes, re "RE: Before launch", with text: "Hi Tomas, the /v2/shifts API reference is merged, but the v1 migration guide was due Sep 10 and is still open. Do you still need it? If so, what date works? I will write it for then: [date]. Thanks, Dana"
- task: kestrel:action:v1-migration-guide
- context: Task: Write migration guide for v1 customers. Sources: em-215982, sl-307630.

### q-1013-warehouse-cutover-plan-infra
- status: pending
- action_type: self_do
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Outline for the infra side of the warehouse cutover plan (due Oct 23, with Raj)
- proposed_tool_call: Outline, infra section of the warehouse cutover plan:
  * 1. Scope and boundary with Raj's data section
  * 2. Current vs target infrastructure: [systems]
  * 3. Pre-cutover prep: provisioning, access, networking, [items]
  * 4. Cutover runbook: ordered steps, owners, timings [times]
  * 5. Monitoring and validation during cutover
  * 6. Rollback plan and trigger criteria: [criteria]
  * 7. Risks and dependencies
  * 8. Cutover window and freeze dates: [dates]
  * Next: sync with Raj on shared interfaces and merge by Oct 23.
- task: kestrel:action:warehouse-cutover-plan-infra
- context: Task: Warehouse cutover plan, infra side (with Raj on the data side). Sources: sl-194739, sl-287474, sl-379479.

### q-1013-plantpal-domain-renewal
- status: pending
- action_type: self_do
- priority: low
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Steps to renew plantpal.app at Namecove before it expires Oct 30
- proposed_tool_call: 1. Log in to Namecove with the dana.kowalski@mailbox.example account.
  * 2. Open the plantpal.app domain page.
  * 3. Renew for [term, e.g. 1 or 2 years] and pay with [payment method].
  * 4. Turn auto-renew on so it does not lapse again.
  * 5. Confirm the new expiry date [date] on the domain page and save the receipt email.
- task: oss:action:plantpal-domain-renewal
- context: Task: Renew the plantpal.app domain (auto-renew is off). Sources: em-677051, doc-959048.

### q-1013-tinyq-docs-site-move
- status: pending
- action_type: self_do
- priority: low
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Checklist to move the tinyq-docs site off Hostlane before Nov 1
- proposed_tool_call: 1. Choose the new host: [host].
  * 2. Build the tinyq-docs site (new theme and search are done) and deploy it to [host].
  * 3. Check pages and search work on the new host.
  * 4. Point the docs domain DNS at the new host: [domain / DNS records].
  * 5. Confirm the site is live and [URL] loads before Nov 1.
  * 6. Cancel the Hostlane legacy plan once the move is verified.
- task: oss:action:tinyq-docs-site-move
- context: Task: Move the tinyq docs site off Hostlane before the legacy plan retires. Sources: em-159713, doc-537085.

### q-1013-tinyq-pr-89-review
- status: pending
- action_type: self_do
- priority: low
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Steps to review tinyq PR #89 (Fix double drain) from olu-a
- proposed_tool_call: 1. Open dana-k/tinyq PR #89 and read issue #88 to confirm the double drain behavior.
  * 2. Check the diff: does acking before release remove the double drain? Look for a case where the ack succeeds but the release fails.
  * 3. Confirm a test reproduces #88 and passes with the fix.
  * 4. Run the test suite locally.
  * 5. Leave review comments: [findings].
  * 6. Approve or request changes, then thank olu-a.
- task: oss:action:tinyq-pr-89-review
- context: Task: Review tinyq PR #89 Fix double drain (#88). Sources: gh-124747.

### q-1013-dental-appointment-reschedule
- status: pending
- action_type: self_do
- priority: low
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Call script for BrightSmile Dental to rebook the cancelled Sep 9 appointment
- proposed_tool_call: Call BrightSmile Dental front desk at [phone number].
  * Say: "Hi, this is Dana Kowalski. Your office cancelled my Sep 9 appointment and asked me to call to reschedule."
  * Ask for the earliest openings on [preferred days/times].
  * Confirm the new date [date], time [time], and any forms or prep needed.
  * Add it to the calendar.
- task: personal:action:dental-appointment-reschedule
- context: Task: Call BrightSmile Dental to reschedule the cancelled Sep 9 appointment. Sources: em-590031.

### q-1013-lease-renewal-sign
- status: pending
- action_type: self_do
- priority: low
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Steps to review and sign the Harbor Lane lease renewal by Oct 30
- proposed_tool_call: 1. Open the Oct 5 email from Harbor Lane Properties (leasing@harborlane.example) and find the renewal document.
  * 2. Read the new terms: rent [amount], term length [length], changes from the current lease [changes].
  * 3. Decide whether to renew. If not, the lease converts to month-to-month after Oct 30.
  * 4. If you have questions or want to negotiate, email leasing before Oct 30.
  * 5. Sign and return the renewal by Oct 30, ideally a few days early.
  * 6. Save a signed copy and note the new end date: [date].
- task: personal:action:lease-renewal-sign
- context: Task: Sign the lease renewal. Sources: em-414540.
