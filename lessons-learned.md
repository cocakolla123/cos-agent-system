# Lessons learned

Append-only. Each entry: date, what happened, what changed as a result. Written to by
`/cos-poll`'s recurring-failure detection (see `commands/cos-poll.md`) and by hand whenever a
fix to a live deployment reflects a general lesson worth folding into this template. This file
is distinct from `PLAN.md`'s own "Lessons learned" section, which tracks lessons about
*building* this template — this file tracks lessons about *running* a deployment of it.

Format for each entry:
```
## <date>
**What happened:** ...
**Fix / workaround:** ...
**Where this is now encoded:** <file(s) updated so future deployments don't hit this cold>
```

---

## 2026-07-13 (worked example, ported from a real deployment's discovery)

**What happened:** A real send-message tool call was blocked by the messaging platform's own
org-level policy ("Your organization requires approval for this tool") — not a bug in this
system, an external permission gate.

**Fix / workaround:** Switched that connector's `action_tools` mapping (in
`dashboard/config.json`) from the real-send tool to a draft-creating variant, so "Approve"
stages a real draft for the user to send themselves instead of attempting (and failing) a real
send. `commands/cos-approve-confirmed.md`'s status handling already distinguishes `approved`
(fully completed) from `drafted` (staged, needs a human's last click) from `failed` (attempt
that didn't work), so this degrades cleanly instead of silently pretending to succeed.

**Where this is now encoded:** `agents/README.md`'s note that specialists never hold a real
send tool by default; `commands/cos-approve-confirmed.md`'s three-way status model;
`dashboard/config.example.json`'s `action_tools` comment. `/setup` should proactively ask
whether the messaging connector's send scope is already approved, or default to a draft-mode
mapping and let the recurring-failure mechanism promote it if a real send later starts working
without one.
