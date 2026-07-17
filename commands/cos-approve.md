---
description: Review and execute items from the approval queue. The only command in this system that holds mutating tool grants, and only invokes them against the exact stored proposed_tool_call.
---

# `/cos-approve`

Argument: $ARGUMENTS (optional — an entry id or filter; if empty, show all `pending` entries)

You run in the main session. This is the **only** `cos-*` command that may hold mutating
tool grants (send/draft, ticket transition/comment, calendar create/update, PR/branch
operations, etc.) — every other command and every specialist is read-only/draft-only by
design.

## Workflow

1. Read `<workspace>/approval-queue.md` (workspace dir is `dashboard/config.json`'s
   `workspace_dir`). List every entry with `status: pending`, formatted for a quick decision:
   id, action_type, drafted_by, a one-line summary of `context`, and the exact
   `proposed_tool_call`.
2. If `$ARGUMENTS` names a specific id, jump straight to that entry.
3. **Ask the user to approve, reject, or edit each entry before doing anything.** Never assume
   approval. Show the literal `proposed_tool_call` so they're approving exactly what will
   run — not a paraphrase of it.
4. On approval: execute `proposed_tool_call` **verbatim** — the exact tool and parameters
   stored on the entry, not a re-interpreted version. **Set status based on what actually
   happened, not on the attempt**: `status: approved` only if the tool call genuinely
   succeeded (a real returned ID/link, not just "no crash"). If it failed for any reason
   (permission denial, org policy block, API error), set `status: failed` instead and record
   the real error as `execution_result`, so a failed attempt doesn't silently look like
   nothing happened.
5. On rejection: set `status: rejected` and record why, if given.
6. If the user wants to edit the action before approving, update `proposed_tool_call` on the
   entry first, show them the new version, and only execute after they confirm that version.
7. Never touch entries with `status: stale` or `superseded` — they're historical record only.

## Hard stops

Refuse to execute anything matching `<workspace>/APPROVAL_POLICY.md`'s "never autonomous" list
(if it exists) even if it somehow reached the queue as `pending` — common examples: deploy to
prod, merge code, delete data, close incidents, change permissions, access outside
authorization, contact external users, legal/financial/employment/security/policy decisions,
impersonation without disclosure. Flag it to the user instead and ask how they want to handle
it outside this system.

## After executing

Forward a short "executed: <id>" note to `cos-knowledge` so the decisions log reflects what
actually happened, not just what was proposed.
