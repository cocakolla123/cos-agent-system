---
description: Execute one specific approval-queue entry with no interactive confirmation. Only ever invoked non-interactively by the local dashboard, after the user has already confirmed via its popup — never intended to be typed by hand instead of /cos-approve.
---

# `/cos-approve-confirmed`

Argument: $ARGUMENTS — exactly one entry id, e.g. `TICKET-123:ticket-comment`. Required, not
optional (unlike `/cos-approve`, this command never lists/prompts — the id was already chosen
in the dashboard UI and the human already clicked confirm there).

You run in the main session. This is a **sibling of `/cos-approve`**, holding the same
category of mutating tool grants, scoped narrowly per invocation by whatever `--allowedTools`
the dashboard passed. The difference from `/cos-approve`: **do not ask for confirmation** —
the dashboard's own confirm-popup already was the human-approval step for this specific id. Do
not treat the mere fact of being invoked as license to do anything beyond the one stored
action below.

## Workflow

1. Read `<workspace>/approval-queue.md`. Find the entry matching `$ARGUMENTS` exactly. If
   none exists, or the matching entry's `status` is not `pending`, stop and output exactly
   that fact (e.g. "no pending entry found for `<id>`") — do not guess which entry was meant.
2. **Hard stop check first, same as `/cos-approve`**: refuse if this entry matches
   `<workspace>/APPROVAL_POLICY.md`'s "never autonomous" list (deploy to prod, merge code,
   delete data, close incidents, change permissions, access outside authorization, contact
   external users, legal/financial/employment/security/policy decisions, impersonation
   without disclosure) — output the refusal and do not execute, even though it reached
   `pending`.
3. Execute `proposed_tool_call` **verbatim** using whichever tool is actually in your
   `--allowedTools` grant for this invocation — never re-interpret or "improve" the drafted
   text. The dashboard scopes this per `action_type` via `dashboard/config.json`'s
   `action_tools` map — e.g. if a messaging send tool has ever hit an org-level policy block
   for this deployment, `action_tools` may point at a draft-creating variant instead of a
   real send. That's not something you decide — just use whichever tool you were actually
   given.
4. **Set status based on what actually happened, not on the attempt.**
   - `status: approved` — the action was genuinely, fully completed (e.g. a real returned ID).
   - `status: drafted` — the tool call succeeded but only *staged* something for the user to
     finish themselves (e.g. a draft-creation tool returned a real link). Record that link in
     `execution_result` so the dashboard can show exactly where to go finish it.
   - `status: failed` — the tool call failed for any reason (permission denial, org policy
     block, API error). Record the real error message as `execution_result` so it stays
     visible on the dashboard rather than disappearing from the pending list.
   Never set `approved` on a rejection, error, or mere draft-creation — those are different
   outcomes with different statuses. `failed` is not the same as `stale`/`superseded`, which
   mean something else resolved it, not that this attempt failed.
5. Forward a short "executed: `<id>`" note to `cos-knowledge` so the decisions log reflects
   what actually happened.
6. Output a short final line the dashboard can show the user: executed / failed / no-op, and
   why.

## Hard stops

Identical to `/cos-approve`'s hard-stop list — refusing here is exactly as important as in the
interactive command, since a scoped `--allowedTools` invocation is still capable of running
whatever tool it was granted.
