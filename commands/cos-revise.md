---
description: Re-draft a pending approval-queue entry based on feedback, without executing anything. Invoked by the dashboard's "Revise" button, but safe to run by hand too — purely draft-only, same posture as /cos.
---

# `/cos-revise`

Arguments: $ARGUMENTS — `<id> <feedback text>` (id first, then the feedback, e.g.
`TICKET-123:ticket-comment "soften the tone, don't mention the two-month timeline"`).

You run in the main session as the orchestrator. This holds no mutating tool — identical
posture to `/cos` and every other draft-only command.

## Workflow

1. Read `<workspace>/approval-queue.md`. Find the entry matching the id. If it's not
   `pending`, say so and stop — don't revise something already resolved.
2. Re-invoke whichever specialist is named in that entry's `drafted_by` field (if multiple are
   listed, e.g. "cos-ticket-triage, revised by cos-risk-quality," use the first/original
   drafter) via the Agent tool, giving it: the original `proposed_tool_call` and `context`,
   plus the user's feedback as an explicit instruction to incorporate. Ask for an updated
   draft in the same format it originally produced.
3. If the entry is an approval-category action (all of them are, by definition) and
   `cos-risk-quality` was generated for this deployment, run it on the revised draft before
   accepting it — same as any other flow.
4. Update the entry in place: new `proposed_tool_call`, `short_summary`, and `context` (append
   a note on what changed and why, don't erase the history of the original draft/rationale).
   Status stays `pending`. This edit goes through `cos-knowledge` like any other workspace
   write, not directly by you.
5. Report back the new draft's `short_summary` + `proposed_tool_call` so the caller (dashboard
   or the user directly) can see exactly what changed.

## Notes

- This never executes anything — it only changes what a future `/cos-approve` or the
  dashboard's "Approve & send" would run. No mutating tool grant needed at all.
- If the feedback is asking for something in `<workspace>/APPROVAL_POLICY.md`'s "never
  autonomous" category (e.g. "just send it directly to legal instead"), don't quietly comply
  — flag it back to the user the same way `/cos-approve`'s hard-stop list would.
