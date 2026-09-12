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

## 2026-07-16 (V2 M1 — Python version floor discovered)

**What happened:** While building the V2 knowledge-graph library, running `python3 -m py_compile
dashboard/server.py` under macOS system Python (`/usr/bin/python3`, 3.9.6) failed with
`SyntaxError: f-string expression part cannot include a backslash` at the meeting-notes card
template. `server.py` uses an f-string whose expression embeds a `"\n\n..."` literal — legal only
on **Python 3.12+**. V1 was authored/verified on a newer Python (homebrew 3.14 here), so the
floor was real but undocumented. A deployer whose default `python3` is 3.9–3.11 would hit a
cryptic crash on `serve.sh` startup.

**Fix / workaround:** Documented the **Python 3.12+ requirement** and kept new V2 modules
(`dashboard/graph.py`) compatible with a wider range (verified passing on 3.9 and 3.14) so the
graph tooling isn't gated harder than the dashboard already is. Longer term the offending
f-string can be refactored (hoist the `"\n\nAction items:\n"` literal into a variable) to lower
the floor, but that's a separate cleanup, not required for M1.

**Where this is now encoded:** this entry; `serve.sh` should state the 3.12+ requirement (follow-up).
**Rule: run `py_compile` under the *oldest* Python a deployer might have as their default
`python3`, not just the newest one on the author's machine — a version-gated syntax error is a
silent floor that only surfaces on someone else's box.**

## 2026-07-17 (V2 review — commands existed but were never installed)

**What happened:** V2 added three commands (`cos-research`, `cos-learn`, `cos-accounts`) that
the dashboard and poll invoke as `/global:cos-*` subprocesses — but `/setup` Step 5's copy list
still named only the six V1 commands. On any fresh deployment, every V2 subprocess (chat
correction loop, accounts probe, incremental research) would have failed with "Unknown
command," silently, into log files.

**Fix / workaround:** Step 5.3 now copies all nine commands and names the failure mode.

**Where this is now encoded:** `commands/setup.md` Step 5.3. **Rule: any new `/global:`-invoked
command MUST be added to `/setup`'s copy list in the same change that introduces it — grep
`server.py` and `commands/*.md` for `/global:` and diff against the copy list before shipping.**

## 2026-09-12 (first real run — three findings in ten minutes)

**What happened:** The first real deployment (fresh machine, dashboard "Research my workspace
now") surfaced three defects no shim-gate had caught: (1) `/start-research` ran with the narrow
`poll_tools` grant (`Read,Edit,Agent`) — under `dontAsk`, `Write`/`Bash`/`Glob`/`Grep` and every
MCP read were silently denied, so research diagnosed brilliantly but couldn't persist a single
graph node; (2) the dashboard chat carried test residue — a `chat-session.json` created during a
shim-based live gate pointed at a session id the real CLI never had, so the user's first message
died with "No conversation found"; (3) that failure surfaced raw instead of self-healing.

**Fix / workaround:** New `research_tools` config key (baseline includes Write/Bash/Glob/Grep;
/setup appends discovered READ-ONLY MCP tools) used by `/start-research`; `validate_config`
enforces its baseline. Chat now detects a dead session and silently retries with a fresh
session id. Test artifacts (`chat-log.md`, `chat-session.json`) removed; live gates must point
`DASHBOARD_DIR`-writing flows at a temp dir, not the real dashboard dir.

**Where this is now encoded:** `server.py` (`RESEARCH_TOOLS`, chat self-heal),
`config.example.json`, `validate_config.py`. **Rules: (a) any subprocess grant paired with
`dontAsk` must be validated against what the command actually needs — a missing tool is a
silent no-op, not an error; (b) a stored session id is a cache, not a fact — always self-heal
on resume failure; (c) live gates that exercise the real server must never leave state files
in the repo's dashboard dir.**
