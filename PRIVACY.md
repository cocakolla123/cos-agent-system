# Privacy: what stays on your machine, and what leaves it

The CoS dashboard runs on your computer. This page lists every place your data
is stored and every outbound network call the code makes. A test
(`dashboard/tests/test_privacy_controls.py`) fails if a module gains a network
or model call that this page does not list, so the page and the code can't
silently disagree.

## What leaves your machine

| Module | Calls | What is sent | When |
|---|---|---|---|
| `dashboard/server.py`, `dashboard/poll_direct.py`, `dashboard/codefix.py`, `poll-tick.sh` | the `claude` CLI, which sends prompts to **Anthropic** | the job's instructions plus the account content the job reads: mail, messages, tickets, calendar events and your task list. Connected accounts (Gmail, Slack, …) are read through Claude's connectors inside that call | every poll tick, research crawl, draft, chat reply and approved action |
| `dashboard/models.py` | only the model providers **you** configure in Settings → Models (Anthropic API, OpenAI, Gemini, OpenRouter, or local Ollama) | text-only jobs: chat (your open tasks and pending drafts), revising a draft, and, in direct mode, the fetched items being read | only when a tier is set to that provider; nothing is sent to a provider you didn't pick |
| `dashboard/connections.py` | direct connections you add: your IMAP server, `slack.com/api`, your Atlassian site, `api.github.com`, your calendar's iCal link, `api.zoom.us` | your credential for that service, to **read** new items. Every connection is read-only | every direct check |
| `dashboard/mailboxes.py` | the `claude mcp` CLI (local configuration only) | the name of a mailbox connector to check or register | when you add a mailbox |
| `dashboard/codefix.py` | `git` and `gh` against your own repository | a fix branch and a pull request, only after you approve that card. It never merges | after an approval |
| `dashboard/publish.py` | `git push` to the template repository you configure | the generic template only, after `privacy.py` scans the whole tree for your names, real addresses, API keys and large dollar amounts and refuses on any hit | only when you run publish |

Nothing else opens a network connection. The dashboard itself listens on
`127.0.0.1` only.

## What stays on your machine

All of it lives under `dashboard/`, and only your user account can read it.
Files are `0600` and folders `0700`; the server checks and repairs this at
every start and every tick. Run `python3 dashboard/privacy.py inventory dashboard`
to see what's on disk right now, with sizes.

| File | Holds | Kept |
|---|---|---|
| `config.json` | your identity, connected accounts, tool grants | until you delete it |
| `connections.json` | direct-connection credentials | until you remove the connection |
| `secrets.json` | API keys for optional model providers | until you remove the key |
| `inbox/*.jsonl` | full text of items fetched by direct connections | **30 days**, then deleted |
| `pending.jsonl` | fetched items waiting for a model read | until read |
| `quarantine.jsonl` | malformed model records, with source ids | until you delete it |
| `runs.jsonl` | per-run trace: ids, counts, fates, costs, **no message text**; errors are redacted | about 5 MB, then the oldest half is dropped |
| `usage.jsonl` | cost and token counts per model call | until you delete it |
| `*.log`, `*.err` | job output, which quotes account content | the newest **5 MB** of each |
| `chat-log.md`, `chat-session.json` | dashboard chat | until you delete them |
| `workspace/graph/` | the knowledge graph: people, tasks, projects | until you delete it |
| `workspace/approval-queue.md` | drafted actions | until approved or rejected |
| `workspace/privacy-tokens.txt` | your own names and employers, used to block publishing them | until you delete it |

None of these files can be committed: each one is in `.gitignore`, and a test
checks that.

## Seeing, exporting and deleting

- **See:** `python3 dashboard/privacy.py inventory dashboard`
- **Check permissions:** `python3 dashboard/privacy.py audit dashboard`, then `fix` to repair
- **Apply retention now:** `python3 dashboard/privacy.py retention dashboard`
- **Export:** everything is plain JSON, JSONL or Markdown in the files above; copy them.
- **Delete:** `/cos-uninstall` removes the commands, agents and scheduler. It deletes your
  workspace data (graph, queue, inbox) only if you explicitly confirm that step.
  Deleting a single file above is also safe; the dashboard rebuilds what it needs.

Revoke a direct connection's credential at its source too (Google App
passwords, your Slack app, GitHub tokens), since removing it here deletes only
the local copy.
