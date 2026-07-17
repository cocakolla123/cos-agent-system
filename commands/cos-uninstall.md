---
description: Cleanly remove this CoS deployment — global commands/agents, scheduler job, and (only if explicitly confirmed) the workspace data
---

# /cos-uninstall — Clean Removal

Remove everything `/setup` installed, without touching any other deployment's files.

1. **Inventory first, show before deleting.** List exactly what will be removed:
   - `~/.claude/commands/global/cos-*.md` and `~/.claude/agents/global/cos-*.md` — but ONLY
     files this deployment wrote. If another CoS deployment exists on this machine (different
     content than this template's), stop and ask which files belong to which.
   - The scheduler job registered for `poll-tick.sh` (launchd plist / crontab entry).
2. **Remove commands/agents + scheduler job** after the user confirms the inventory.
3. **Workspace data** (`dashboard/workspace/` — graph, approval queue, audit log, lessons,
   context) is the user's work product: NEVER removed by default. Only delete it if the user
   explicitly asks, and offer a tarball backup first.
4. Report what was removed and what was intentionally kept.
