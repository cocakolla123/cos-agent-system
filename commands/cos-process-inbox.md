---
description: Process ad-hoc requests submitted via the local dashboard's task box. Reads new lines from tasks/inbox.md, runs each through /cos, and moves them to inbox-done.md.
---

# `/cos-process-inbox`

You run in the main session as the orchestrator (same role as `/cos` itself — this command
just supplies `/cos`'s input from a file instead of from the user typing directly).

## Workflow

1. Read `<workspace>/tasks/inbox.md`. Find every line with status `pending`
   (`- [pending] <timestamp> — <request text>`). If there are none, say so and stop — don't
   invent work.
2. For each pending line, in order submitted (oldest first):
   a. Run the full `/cos` orchestration flow (Step 0 classify → Step 1 context →
      Step 2 dispatch → Step 3 risk gate → Step 4 merge → Step 5 queue) using that line's
      request text as the request, exactly as if the user had typed it directly.
   b. After that flow completes and anything it produced has been queued/logged, edit
      `inbox.md` to change that line's status from `pending` to `processed`, then append the
      same line to `inbox-done.md`.
3. Summarize for the user: how many items were processed, one line each on what was found /
   what's now in the approval queue, and confirm nothing was sent or modified externally
   beyond what `/cos` itself already queues.

## Notes

- Process items one at a time, not all in parallel — each one runs the full `/cos` flow, which
  itself parallelizes internally where appropriate. Running multiple `/cos` flows
  concurrently risks races on `approval-queue.md`/shared-context writes.
- This command holds no mutating tool itself — identical posture to `/cos`. Everything it
  produces lands in the approval queue for `/cos-approve` (or the dashboard's confirmed-approve
  flow), never executed here.
- If a request in the inbox is ambiguous, follow `/cos`'s own Step 0 "no confident match"
  behavior (surface the ambiguity, ask which flow was meant) rather than guessing — even
  though there's no live human on the other end of a dashboard-submitted request, so record
  the ambiguity as an open question via `cos-knowledge` instead of blocking.
