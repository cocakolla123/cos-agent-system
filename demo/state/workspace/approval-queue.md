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
- task: kestrel:action:api-v1-deprecation-notice
- context: Task: Write API v1 deprecation notice text for Tomas (due 2026-10-13). Source: his email of Oct 8, 'I need the API v1 deprecation notice text by next Tuesday.'

### q-1013-alex-cron
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-drafter
- created: 2026-10-13T08:44:00-07:00
- short_summary: Slack reply to Alex in #proj-billing-migration: the billing cron schedule (due Oct 16)
- proposed_tool_call: slack.send_message in #proj-billing-migration, thread of Oct 12, with text: "Confirming the billing job schedule ahead of the cutover: [schedule]. Shout if the cutover week changes."
- task: kestrel:action:confirm-billing-cron-schedule
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
- task: kestrel:action:confirm-billing-cron-schedule
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

### q-1013-corvid-final-round-slot
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Corvid Recruiting: ask for the available final-round slots
- proposed_tool_call: gmail-personal.send to Corvid Systems Recruiting, re "Final round", with text: "Hi, thank you for the update. I'd like to book my final-round interview before the Oct 23 deadline. Could you send the available slots, or a scheduling link? I'll confirm one right away. Best, Dana Kowalski"
- task: job-search:action:corvid-final-round-slot
- context: Task: Pick a Corvid Systems final-round interview slot. Sources: em-0684.

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
- context: Task: Do the churn report from Raj's usage export. Sources: sl-17358, sl-17359.

### q-1013-conference-budget-request
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Victor: conference budget request (fill blanks before sending)
- proposed_tool_call: gmail-work.send to Victor Hale, re "Re: Budget asks", with text: "Hi Victor, here is my conference budget request. Conference: [name, dates, location]. Attendees: [names]. Estimated cost: registration [amount], travel [amount], lodging [amount], total [amount]. Why it matters: [business reason]. Happy to adjust if needed. Thanks, Dana"
- task: kestrel:action:conference-budget-request
- context: Task: Send Victor the conference budget request. Sources: em-0708.

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
- context: Task: Sign off on the events schema change for Raj. Sources: sl-17373.

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
- context: Task: Send Ines a short status update every Friday. Sources: sl-17371, em-0717.

### q-1013-inc-240-timeline
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Outline for INC-240 timeline from #incidents thread (overdue)
- proposed_tool_call: Timeline, Oct 7 (add times and zone from Slack timestamps):
  * - [time] Incident detected [how/by whom]
  * - [time] Raj: errors dropping
  * - [time] Ines: still some 502s from the LB
  * - [time] Mei: LB health checks flapping
  * - [time] Sam: stable
  * - [time] Raj: also seen on eu-west [confirm whether before or after stable]
  * Also add: start time [time], impact [scope], root cause [root cause], mitigation [action], resolution [time]. Tell Ines when done, since it was due Oct 8.
- task: kestrel:action:inc-240-timeline
- context: Task: Add timeline to the INC-240 incident doc. Sources: sl-17420.

### q-1013-it-access-analytics-replica
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Kestrel IT: follow-up on analytics replica access for RTA-90
- proposed_tool_call: gmail-work.send to Kestrel IT, re "RE: Access request: analytics replica", with text: "Hi IT, following up on my request from Aug 5 for read access to the analytics replica. I am still blocked on RTA-90. Could you let me know the status and whether you need anything from me to move it along? Thanks, Dana"
- task: kestrel:action:it-access-analytics-replica
- context: Task: Awaiting IT access to analytics replica (RTA-90). Sources: em-0665, em-0666.

### q-1013-lena-api-field-list-settings-screen
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Slack to Lena: send the overdue API field list for the settings screen
- proposed_tool_call: slack.send_message in <#D-dana-lena>, thread of Sep 29, with text: "Hi Lena, sorry this is later than I said. Here is the API field list for the new settings screen: [field list]. Let me know if anything is unclear or missing."
- task: kestrel:action:lena-api-field-list-settings-screen
- context: Task: Send Lena the API field list for the new settings screen. Sources: sl-17335, sl-17336.

### q-1013-lena-bulk-edits-api-answer
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Slack to Lena: answer on API bulk edit support before Oct 16 mocks
- proposed_tool_call: slack.send_message in <#D-dana-lena>, thread of Oct 12, with text: "Hi Lena, on bulk edits: [yes / no / not decided yet]. [Any detail that affects the mocks, e.g. limits or which fields]. This should let you finalize the mocks by Friday."
- task: kestrel:action:lena-bulk-edits-api-answer
- context: Task: Tell Lena whether the API supports bulk edits. Sources: sl-17366.

### q-1013-lena-roster-timezone-names-answer
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Slack to Lena and Mei: roster API timezone names answer for the mock
- proposed_tool_call: slack.send_message in <#mpdm-dana.k--lena--mei>, thread of Oct 8, with text: "Hi Lena, on the roster API: it [does / does not] return each location's timezone names. [Field name or format, if it does; what to use instead, if not]. That should cover what you need for the mock by Oct 14."
- task: kestrel:action:lena-roster-timezone-names-answer
- context: Task: Tell Lena whether the roster API returns location timezone names. Sources: sl-17386.

### q-1013-northwind-data-retention-policy
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Alex Brennan: check whether Northwind still needs the data retention policy and by when
- proposed_tool_call: gmail-work.send to Alex Brennan, re "RE: Data retention policy", with text: "Hi Alex, I promised to send Kestrel's data retention policy by Aug 28 and it has slipped past that date. Sorry about that. Do you still need it for your compliance audit? If so, what date works for you? I will get it to you by then. Thanks, Dana"
- task: kestrel:action:northwind-data-retention-policy
- context: Task: Send Kestrel data retention policy to Alex Brennan (Northwind). Sources: em-0656, em-0657.

### q-1013-northwind-msa-redlines-legal-review
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Kestrel Legal: check status of LEG-55 MSA redlines review
- proposed_tool_call: gmail-work.send to Kestrel Legal, re "RE: Northwind MSA redlines", with text: "Hi Legal, checking in on LEG-55, the review of the Northwind MSA redlines. Do you have an estimate for when it will be done? Happy to walk through the redlines or answer questions if that helps. Thanks, Dana"
- task: kestrel:action:northwind-msa-redlines-legal-review
- context: Task: Awaiting Legal review of Northwind MSA redlines (LEG-55). Sources: em-0725, em-0726.

### q-1013-northwind-pen-test-summary
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Alex Brennan: send pen-test summary (requested by Oct 22)
- proposed_tool_call: gmail-work.send to Alex Brennan, re "RE: Security documents", with text: "Hi Alex, attached is Kestrel's pen-test summary, ahead of your Oct 22 date. [attach pen-test summary]. Let me know if you need anything else for your review. Thanks, Dana"
- task: kestrel:action:northwind-pen-test-summary
- context: Task: Send pen-test summary to Alex Brennan (Northwind). Sources: em-0707.

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
- context: Task: Comment on the notifications RFC for Tomas. Sources: em-0663, sl-17324, sl-17325.

### q-1013-pager-config-review
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Slack reply to Raj: pager config review slipped past Monday, giving a new date
- proposed_tool_call: slack.send_message in #platform, thread of Oct 9, with text: "Hi Raj, sorry, the pager config review slipped past Monday. I'll review it and send you my comments by [date]. If anything specific needs a look first, tell me and I'll start there."
- task: kestrel:action:pager-config-review
- context: Task: Look at the pager config for Raj. Sources: sl-17368.

### q-1013-plat-301-postmortem-inc-212
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Slack reply to Ines: is the INC-212 postmortem (PLAT-301) still needed, and by when
- proposed_tool_call: slack.send_message in #platform, thread of Jul 21, with text: "@Ines Moreau the INC-212 postmortem (PLAT-301) was due Jul 31 and is still open on my side. Do you still need it? If so, what date should I aim for? If not, I will close the ticket."
- task: kestrel:action:plat-301-postmortem-inc-212
- context: Task: Write postmortem for INC-212 queue outage (PLAT-301). Sources: jr-0538, jr-0539, sl-17317.

### q-1013-plat-322-cron-migration-scheduler-v2
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Steps to finish the cron migration to scheduler v2 (PLAT-322, due Oct 16)
- proposed_tool_call: 1. List the cron jobs still on the old scheduler: [count and names].
  * 2. Migrate the remaining jobs to scheduler v2 and confirm each runs on its next schedule.
  * 3. Check the load test result (PLAT-360) before launch: [result].
  * 4. Note any rollback steps in the runbook.
  * 5. Move PLAT-322 to Done in Jira before Oct 16 and tell Ines Moreau, or ask her for a new date if it will slip: [new date].
- task: kestrel:action:plat-322-cron-migration-scheduler-v2
- context: Task: Migrate cron jobs to scheduler v2 (PLAT-322). Sources: jr-0544, sl-17322, em-0717.

### q-1013-plat-355-oncall-runbook-rewrite
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Outline for the on-call runbook rewrite (PLAT-355, overdue, taken over from Sam)
- proposed_tool_call: On-call runbook outline
  * 1. Purpose and scope
  * 2. On-call rotation and handoff: [schedule source]
  * 3. Paging and escalation: who, when, how [contacts]
  * 4. Triage checklist for common alerts: [alert list]
  * 5. Incident procedures and links to postmortems
  * 6. Rollback and recovery steps: [steps]
  * 7. Contacts and tools: [links]
  * 8. Review owner and update process
  * First, check PLAT-355 and Sam Okoye's notes for any existing draft. Then set a new due date with Ines Moreau: [date].
- task: kestrel:action:plat-355-oncall-runbook-rewrite
- context: Task: Rewrite the on-call runbook (PLAT-355, taken over from Sam). Sources: jr-0547, sl-17328.

### q-1013-plat-360-load-test-scheduler-v2
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Slack reply to Ines: status and new date for the scheduler v2 load test (PLAT-360)
- proposed_tool_call: slack.send_message in #platform, thread of Sep 15, with text: "Hi Ines, update on the scheduler v2 load test (PLAT-360), which was due Sep 30: [current status and any results so far]. I expect to finish by [date] and will post the results here before launch."
- task: kestrel:action:plat-360-load-test-scheduler-v2
- context: Task: Load test scheduler v2 (PLAT-360). Sources: jr-0549, sl-17337, cal-0006.

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
- context: Task: Export the on-call schedule to calendars (PLAT-380). Sources: jr-0558, sl-17352.

### q-1013-plat-390-worker-pool-metrics-endpoint
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Slack reply to Alex: metrics endpoint moves to Nov 6 per Ines
- proposed_tool_call: slack.send_message in #platform, thread of Sep 24, with text: "Hi Alex, Ines confirmed the worker pool metrics endpoint (PLAT-390) can wait until Nov 6, so I'll focus on the load test first and deliver it by then. If you need it earlier, please check with Ines. I'll update the Jira due date too."
- task: kestrel:action:plat-390-worker-pool-metrics-endpoint
- context: Task: Build metrics endpoint for the worker pool (PLAT-390). Sources: jr-0560, sl-17353, em-0694.

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
- context: Task: Close PLAT-410 (gzip is live in prod). Sources: jr-0563, sl-17362.

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
- context: Task: Perf benchmark and latency numbers for the roster API (PLAT-420). Sources: jr-0564, cal-0010, sl-17364.

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
- context: Task: Produce a Postgres 18 upgrade plan before the Oct 20 planning meeting. Sources: em-0701.

### q-1013-q4-capacity-numbers
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Slack follow-up in #platform: are the Q4 capacity numbers still needed, and by when
- proposed_tool_call: slack.send_message in #platform, thread of Sep 21, with text: "I said I would put together the Q4 capacity numbers by Thursday and that did not happen. Does anyone still need them? If so, by when? I will plan around that date. If not, I will drop it."
- task: kestrel:action:q4-capacity-numbers
- context: Task: Put together the Q4 capacity numbers. Sources: sl-17332.

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
- context: Task: Think about Q4 growth goals. Sources: doc-0013.

### q-1013-q4-headcount-platform-justification
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Outline for the Platform section of the Q4 headcount justification doc, due Oct 19
- proposed_tool_call: Add under the Platform section of the doc "Q4 headcount justification":
  * 1. Request: [number and role(s)]
  * 2. Current team and workload: [team size, on-call load]
  * 3. Business case: [roadmap work at risk without hires, e.g. Postgres 18 upgrade, queue sharding]
  * 4. Evidence: [metrics, incidents, capacity numbers]
  * 5. Cost of not hiring: [risks]
  * 6. Proposed start timing: [date]
  * Then reply to Ines's comment in the doc and her Oct 8 DM to say it is ready.
- task: kestrel:action:q4-headcount-platform-justification
- context: Task: Write platform staffing case for Q4 headcount. Sources: em-0700, sl-17365, doc-0014.

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
- context: Task: Queue sharding: build the consumers (Alex does producers). Sources: sl-17381, sl-17382.

### q-1013-renew-api-tls-cert
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Steps to renew the api.kestrel.example TLS cert (expires Nov 2, ask is before Oct 30)
- proposed_tool_call: 1. Confirm where the cert is issued and managed: [CA or tool].
  * 2. Generate or request the renewal for api.kestrel.example: [command or console link].
  * 3. Complete validation: [method].
  * 4. Deploy the new cert to [load balancers or hosts] in a low-traffic window: [date].
  * 5. Verify the new expiry date and chain with a browser or openssl check.
  * 6. Reply in the #platform thread from Oct 9 to tell Raj it is done.
  * 7. Confirm the CertWatch alert clears. Finish before Oct 30.
- task: kestrel:action:renew-api-tls-cert
- context: Task: Renew api.kestrel.example TLS cert (expires Nov 2). Sources: sl-17350, em-0681.

### q-1013-retry-policy-rfc
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Ines: is the retry-policy RFC still needed, and by when
- proposed_tool_call: gmail-work.send to Ines Moreau, re "Retry-policy RFC", with text: "Hi Ines, the retry-policy RFC has been carried over in the platform sync notes since the Sep 4 target and I have not delivered it. Is it still needed? If so, what date should I aim for? If priorities have changed, I will close it out. Thanks, Dana"
- task: kestrel:action:retry-policy-rfc
- context: Task: Draft the retry-policy RFC. Sources: doc-0011, doc-0012.

### q-1013-review-iam-policy-diff
- status: pending
- action_type: self_do
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Review checklist for the IAM policy diff, due Oct 15
- proposed_tool_call: 1. Open the IAM policy diff: [link, ask Ines if unclear].
  * 2. Check each change for least privilege: no new wildcards in actions or resources.
  * 3. Flag new or widened permissions that lack a stated reason.
  * 4. Check role and trust policy changes and who can assume them.
  * 5. Confirm removed permissions will not break [dependent services].
  * 6. Write findings: approve, or request changes with specifics.
  * 7. Post the result where the diff lives and tell Ines in #platform before Oct 15.
- task: kestrel:action:review-iam-policy-diff
- context: Task: Review the IAM policy diff. Sources: sl-17367.

### q-1013-review-rota-api-pr-470
- status: pending
- action_type: self_do
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Review steps for rota-api PR #470 (Batch shift import), covering for Alex
- proposed_tool_call: 1. Open kestrel/rota-api#470 (author raj-p) and read the diff. Description: imports shifts in batches of 500.
  * 2. Check batching edge cases: empty input, last partial batch, exactly 500 rows.
  * 3. Check failure handling: partial failure, rollback or retry, duplicate shifts on re-import.
  * 4. Check transaction use and performance on large imports.
  * 5. Check test coverage for the above.
  * 6. Submit the review: approve or request changes with comments.
  * 7. Reply to Ines's Oct 7 thread in #platform once done.
- task: kestrel:action:review-rota-api-pr-470
- context: Task: Review rota-api PR #470 (Batch shift import). Sources: gh-0035, sl-17330.

### q-1013-rota-api-issue-430-csv-import
- status: pending
- action_type: self_do
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Fix plan for rota-api #430: CSV import drops last row (regression in 2.14)
- proposed_tool_call: 1. Reproduce on 2.14 with a small CSV, trying one file with a trailing newline and one without.
  * 2. Compare the import code between the last good release and 2.14 to find the change that skips the final row. Root cause: [root cause].
  * 3. Fix it and add a regression test that imports N rows and asserts N rows saved.
  * 4. Open a PR that references #430 and ask alex-park to confirm the fix.
  * 5. Comment on the issue with the cause and the fixed version: [version].
- task: kestrel:action:rota-api-issue-430-csv-import
- context: Task: Fix reopened CSV import drops last row (rota-api #430). Sources: gh-0040.

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
- context: Task: Rotate and revoke leaked AWS key (kestrel/infra commit 9f2c1ab). Sources: sl-17348, em-0680.

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
- context: Task: Rotate SSH keys per the new security policy. Sources: sl-17374.

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
- context: Task: Fix reopened timezone bug in shift export (RTA-101). Sources: jr-0554.

### q-1013-rta-130-northwind-rca
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Alex Brennan: apologize for the delay on the Sep 2 RCA and confirm what Northwind still needs and by when
- proposed_tool_call: gmail-work.send to Alex Brennan, re "RE: Outage on Sep 2", with text: "Hi Alex, I am sorry the RCA for the Sep 2 outage has taken this long. Do you still need it from us? If so, what date works for you? I will send it by then. Thanks, Dana"
- task: kestrel:action:rta-130-northwind-rca
- context: Task: Send Northwind RCA for the Sep 2 outage (RTA-130). Sources: jr-0551, em-0670, sl-17338.

### q-1013-scheduler-v2-architecture-review-design-
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Ines circulating scheduler v2 design doc before Oct 22 review (add Victor and Alex Park as recipients)
- proposed_tool_call: gmail-work.send to Ines Moreau, re "Scheduler v2 design doc for the Oct 22 architecture review", with text: "Hi Ines, as requested, here is the scheduler v2 design doc ahead of the architecture review on Oct 22: [link to design doc]. Victor and Alex Park are on the invite and should have it too. Key decisions I want feedback on: [decision 1], [decision 2]. Please send any comments before the review so we can use the hour well. Dana"
- task: kestrel:action:scheduler-v2-architecture-review-design-doc
- context: Task: Circulate scheduler v2 design doc before the Oct 22 architecture review. Sources: cal-0008.

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
- context: Task: Update scheduler v2 launch checklist with infra steps. Sources: sl-17455.

### q-1013-security-awareness-training
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to People Team: confirm the overdue security training is still open and agree a completion date
- proposed_tool_call: gmail-work.send to Kestrel People Team, re "RE: Overdue: security awareness training", with text: "Hi, my annual security awareness training was due Sep 15 and is still incomplete. Is it still open for me to finish, and what is the latest date I can complete it by? I will do it by [date]. Thanks, Dana"
- task: kestrel:action:security-awareness-training
- context: Task: Complete annual security awareness training. Sources: em-0673, em-0674, em-0675.

### q-1013-soc2-backup-restore-evidence
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Ines: apologize for the late backup restore evidence and confirm the date the SOC 2 audit needs it
- proposed_tool_call: gmail-work.send to Ines Moreau, re "RE: SOC 2 evidence", with text: "Hi Ines, I am sorry the backup restore test evidence is late. The Sep 25 date has passed. Do you still need it for the SOC 2 audit, and what is the latest date you can use? I will send it by then: [date]. Thanks, Dana"
- task: kestrel:action:soc2-backup-restore-evidence
- context: Task: Send SOC 2 backup restore test evidence to Ines. Sources: em-0695, em-0696, em-0697.

### q-1013-stratus-renewal-quote
- status: pending
- action_type: message_send
- priority: medium
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Priya: follow up on the 50-seat renewal quote requested Aug 18
- proposed_tool_call: gmail-work.send to Priya, re "Renewal quote", with text: "Hi Priya, I asked on Aug 18 for the renewal quote for our 50-seat plan and only got an automatic acknowledgment. Could you send the quote, or tell me when to expect it? If the renewal date is coming up on your side, please let me know that too. Thanks, Dana"
- task: kestrel:action:stratus-renewal-quote
- context: Task: Awaiting Priya's renewal quote for the 50-seat Stratus plan. Sources: em-0668, em-0669.

### q-1013-v1-migration-guide
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Email to Tomas: is the v1 customer migration guide still needed, and by when
- proposed_tool_call: gmail-work.send to Tomas Reyes, re "RE: Before launch", with text: "Hi Tomas, the /v2/shifts API reference is merged, but the v1 migration guide was due Sep 10 and is still open. Do you still need it? If so, what date works? I will write it for then: [date]. Thanks, Dana"
- task: kestrel:action:v1-migration-guide
- context: Task: Write v1 customer migration guide (API v2 launch). Sources: em-0691, sl-17351, gh-0042.

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
- context: Task: Warehouse cutover plan, infra side (with Raj on data side). Sources: sl-17378, sl-17379, sl-17380.

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
- context: Task: Review tinyq PR #89 (Fix double drain). Sources: gh-0038.

### q-1013-dental-reschedule
- status: pending
- action_type: self_do
- priority: low
- drafted_by: cos-poll
- created: 2026-10-13T08:50:00-07:00
- short_summary: Call script to reschedule the Sep 9 BrightSmile Dental appointment they cancelled
- proposed_tool_call: 1. Call BrightSmile Dental front desk at [phone number].
  * 2. Say: "Hi, this is Dana Kowalski. Your office cancelled my Sep 9 appointment and asked me to call to reschedule."
  * 3. Have your availability ready: [days and times that work].
  * 4. Ask for the earliest opening and confirm the date, time and appointment type: [details].
  * 5. Ask them to send a confirmation to dana.kowalski@mailbox.example.
  * 6. Add the new appointment to your calendar.
- task: personal:action:dental-reschedule
- context: Task: Call BrightSmile Dental to reschedule the cancelled Sep 9 appointment. Sources: em-0687.

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
- context: Task: Sign lease renewal with Harbor Lane Properties. Sources: em-0688.
