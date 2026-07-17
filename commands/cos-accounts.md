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

**Hard rules:** read-only against every connector; never store tokens (status + identity only);
never enqueue an auth ask for an account the user has **declined** (`accounts.is_declined` —
Refuse is permanent); ask the user nothing except authorization, and only via the dashboard
popup mechanism (the auth-request queue), never inline.

## Step 1 — Enumerate instances
Merge two sources:
- `connector_accounts` in `dashboard/config.json` (the configured accounts), via
  `accounts.load_accounts(config)`.
- The live tool list: `accounts.detect_instances(<discovered MCP tool names>)` — this catches
  instances the config doesn't know yet (e.g. the user just added `gmail-work` in Claude's
  connector settings). `accounts.multi_account_kinds` flags kinds with ≥2 instances. For each
  unconfigured instance, draft a new `connector_accounts` entry (id from the server name, kind
  from the tool signals, `tool_prefix` from the namespace) and add it to config.json.

## Step 2 — Probe each instance (identity + auth)
For each account, one cheap **identity-revealing read-only call** via its `probe_tool`:
- email: a 1-thread search — the account address appears in the result's recipients;
- messaging: the self-identity/auth-test read;
- calendar: the primary calendar's id;
- anything else: the cheapest 1-item read the instance offers.
Record with `accounts.write_status(dashboard_dir, id, ok, identity=..., error=...)`. An auth/
permission failure is status, not a crash — continue with the rest.

## Step 3 — Auth asks (popup only, Refuse is forever)
For each account whose probe failed with an auth error AND `not accounts.is_declined(...)`:
`accounts.enqueue_auth_request(dashboard_dir, id, reason, auth_url)` — the dashboard renders
the modal (Authorize / Not now / Refuse) and records the outcome. `auth_url` is the best
available entry point: the connector's own auth URL if the error exposes one, else Claude's
connector-settings page. Declined accounts are skipped everywhere and reported as
"declined by user" — never as an error, never re-asked.

## Step 4 — Workspace binding (automatic, ask only if ambiguous)
For accounts with an identity but no `workspace`: infer — company-domain address matching a
known employer workspace → that workspace; `.edu` → school; personal-domain (gmail.com etc.) →
personal; a domain matching a freelance client in the graph → that client's workspace. Save the
binding into `connector_accounts` and the workspace registry's `connectors[]`
(`dashboard/workspaces.py`). Only a genuinely ambiguous identity generates a question — and even
that goes through the dashboard (an open question via `cos-knowledge`), not an inline prompt.

## Step 5 — Update agents
Run `factory.propose_agents(graph, accounts=accounts.load_accounts(config))`: workspaces with
their own communication accounts get per-workspace comms agents (`cos-comms-<workspace>`)
granted ONLY that workspace's instance tools. Propose additions/changes the same way `/setup`
does (collision-safe, user approves before any agent file is written). Research modules
(`/cos-research`) must tag records from an instance with that instance's workspace, so graph
isolation follows automatically.

## Step 6 — Report
Per account: state (connected ✓ / needs auth ✗ / declined 🚫 / unknown), identity, workspace,
and the exact fix for anything broken. One-line summary from `accounts.summarize_accounts`.
Forward a `Memory update:` to `cos-knowledge`. Nothing external was sent or modified.
