---
description: Probe every connector account instance (multi-account aware) — identity, auth status, workspace binding — and keep the dashboard's Accounts panel + auth popups current. Read-only.
argument-hint: "[--probe]"
---

# /cos-accounts — Multi-Account Connector Management

One MCP connection = one OAuth = **one account**. Multiple accounts (two Gmails, two Slacks) on
one machine are multiple **named connector instances**, each with its own OAuth and its own tool
namespace. This command keeps the system's picture of those instances current: who each one is
logged in as, whether it still works, and which workspace it belongs to. The deterministic core
is `dashboard/accounts.py`; the dashboard renders the results and pops the auth modal.

**How you write:** this run has no Python interpreter. Its only Bash command is
`python3 <tool> <command>` (the `--tool=<path>` the dashboard passes), and it writes files only
inside the workspace (`--workspace=<path>`); put any JSON a command needs under
`<workspace>/tmp/`. The commands: `accounts-list`, `accounts-detect <tools.json>`,
`accounts-add <entry.json>`, `accounts-bind <id> <workspace>`, `accounts-status <id> ok|failed
[--identity X] [--error X]`, `accounts-declined <id>`, `accounts-auth <id> [--reason X] [--url
https://...]`, `accounts-summary`, `workspace-connect <workspace dir> <workspace> <connector>`,
`agents-propose <workspace>/graph`.

**Hard rules:** read-only against every connector; never store tokens (status + identity only);
never enqueue an auth ask for an account the user has **declined** (`accounts-declined <id>` —
Refuse is permanent); ask the user nothing except authorization, and only via the dashboard
popup mechanism (the auth-request queue), never inline.

## Step 1 — Enumerate instances
Merge two sources:
- `connector_accounts` in `dashboard/config.json` (the configured accounts), via
  `python3 <tool> accounts-list`.
- The live tool list: `python3 <tool> accounts-detect <workspace>/tmp/tools.json` (the discovered MCP tool names) — this catches
  instances the config doesn't know yet (e.g. the user just added `gmail-work` in Claude's
  connector settings). its `multi_account_kinds` flags kinds with ≥2 instances. For each
  unconfigured instance, draft a new `connector_accounts` entry (id from the server name, kind
  from the tool signals, `tool_prefix` from the namespace) and add it with `accounts-add`.

## Step 2 — Probe each instance (identity + auth)
For each account, one cheap **identity-revealing read-only call** via its `probe_tool`:
- email: a 1-thread search — the account address appears in the result's recipients;
- messaging: the self-identity/auth-test read;
- calendar: the primary calendar's id;
- anything else: the cheapest 1-item read the instance offers.
Record with `python3 <tool> accounts-status <id> ok|failed --identity ... --error ...`. An auth/
permission failure is status, not a crash — continue with the rest.

## Step 3 — Auth asks (popup only, Refuse is forever)
For each account whose probe failed with an auth error AND not declined (`accounts-declined <id>`):
`python3 <tool> accounts-auth <id> --reason ... --url ...` — the dashboard renders
the modal (Authorize / Not now / Refuse) and records the outcome. `auth_url` is the best
available entry point: the connector's own auth URL if the error exposes one, else Claude's
connector-settings page. Declined accounts are skipped everywhere and reported as
"declined by user" — never as an error, never re-asked.

## Step 4 — Workspace binding (automatic, ask only if ambiguous)
For accounts with an identity but no `workspace`: infer — company-domain address matching a
known employer workspace → that workspace; `.edu` → school; personal-domain (gmail.com etc.) →
personal; a domain matching a freelance client in the graph → that client's workspace. Save the
binding with `accounts-bind <id> <workspace>` and add the connector to the workspace registry
with `workspace-connect <workspace dir> <workspace> <connector>`. Only a genuinely ambiguous identity generates a question — and even
that goes through the dashboard (an open question via `cos-knowledge`), not an inline prompt.

## Step 5 — Update agents
Run `python3 <tool> agents-propose <workspace>/graph`: workspaces with
their own communication accounts get per-workspace comms agents (`cos-comms-<workspace>`)
granted ONLY that workspace's instance tools. Propose additions/changes the same way `/setup`
does (collision-safe, user approves before any agent file is written). Research modules
(`/cos-research`) must tag records from an instance with that instance's workspace, so graph
isolation follows automatically.

## Step 6 — Report
Per account: state (connected ✓ / needs auth ✗ / declined 🚫 / unknown), identity, workspace,
and the exact fix for anything broken. One-line summary from `python3 <tool> accounts-summary`.
Forward a `Memory update:` to `cos-knowledge`. Nothing external was sent or modified.

## Local mailbox instances (M14)

First-party connectors hold exactly one Google login, so every ADDITIONAL mailbox is a local
MCP server instance named `gmail-<shortname>` (registered user-scope via `claude mcp add`,
package `@gongrzhe/server-gmail-autoauth-mcp`, per-instance `GMAIL_CREDENTIALS_PATH` token).
The dashboard's "➕ Connect an account" flow creates these; treat their tools
(`mcp__gmail-<shortname>__search_emails|read_email|list_email_labels`) as a full gmail-kind
account instance in Steps 1–5: probe identity with a cheap `search_emails` (e.g. newest
message's To: header), bind by the probed address's domain like any other account, and grant
per-workspace comms agents only that instance's tools. Only the read-only tool subset is ever
granted anywhere — the instance has no send/modify/delete grants to begin with.
