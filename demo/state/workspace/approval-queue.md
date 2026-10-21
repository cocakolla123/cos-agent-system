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
- context: Task: Write API v1 deprecation notice text for Tomas (due 2026-10-13). Source: his email of Oct 8, 'I need the API v1 deprecation notice text by next Tuesday.'

### q-1013-alex-cron
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-drafter
- created: 2026-10-13T08:44:00-07:00
- short_summary: Slack reply to Alex in #proj-billing-migration: the billing cron schedule (due Oct 16)
- proposed_tool_call: slack.send_message in #proj-billing-migration, thread of Oct 12, with text: "Confirming the billing job schedule ahead of the cutover: [schedule]. Shout if the cutover week changes."
- context: Task: Confirm the cron schedule for the billing jobs for Alex (due 2026-10-16). Source: '@dana.k can you confirm the cron schedule for the billing jobs by Oct 16? we cut over the week after.'

### q-1013-laptop-swap
- status: pending
- action_type: it_booking
- priority: high
- drafted_by: cos-drafter
- created: 2026-10-13T08:45:00-07:00
- short_summary: Book the laptop swap on the IT booking page (was due Oct 9)
- proposed_tool_call: Open the IT booking page and pick a laptop swap slot. No connector can book it, so this is yours to do; mark it handled after.
- context: Task: Book laptop swap appointment with IT (due 2026-10-09, overdue). Source: Kestrel IT, it@kestrel.example, Sep 23. Not the look-alike 'password expires' mail from kestrel-helpdesk.example on Sep 22, which was set aside as phishing.

### q-1013-grace-resume
- status: pending
- action_type: message_send
- priority: high
- drafted_by: cos-drafter
- created: 2026-10-13T08:47:00-07:00
- short_summary: Email to Grace Liu (Halcyon Talent) with the updated resume [job-search workspace]
- proposed_tool_call: gmail-personal.send to Grace Liu, re "Updated resume", with text: "Hi Grace, sorry this is late. My updated resume is attached. Happy to talk whenever suits you."
- context: Job-search workspace: drafted from the personal mailbox, never the work account. Task: Send updated resume to Grace Liu (asked for it by Oct 1).

### q-1012-alex-ack
- status: approved
- action_type: message_send
- priority: medium
- drafted_by: cos-drafter
- created: 2026-10-12T16:10:00-07:00
- short_summary: Slack: acknowledge Alex's cron question (will confirm by Oct 16)
- proposed_tool_call: slack.send_message in #proj-billing-migration, thread of Oct 12, with text: "On it, will confirm by Thursday."
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
