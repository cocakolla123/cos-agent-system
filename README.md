# CoS Template

A self-contained, reusable Chief-of-Staff multi-agent system. Open this folder in Claude Code
and run `/setup` — it discovers your available MCP connectors, asks the one thing it can't
infer (your actual core job), generates matching agents, and sets up a local dashboard +
polling.

Start here: **[PLAN.md](./PLAN.md)** — full design, ground rules, config schema, and current
build status.

This folder has no relationship to any other CoS deployment on this machine (including
anything under `~/.claude/cos/`) — see PLAN.md's "Ground rule: total self-containment."

## Quick start

1. Run `/setup` (see `commands/setup.md`).
2. `./dashboard/serve.sh` to start the local dashboard at `http://127.0.0.1:8765`.
3. Use `/cos "<request>"` for anything ad hoc, or let polling surface things on its own.

## Layout

See PLAN.md's "Directory layout" section.
