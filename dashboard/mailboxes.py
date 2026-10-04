#!/usr/bin/env python3
"""Additional-mailbox flow (M14). Stdlib only, dependency-injected.

First-party connectors hold exactly one Google login, so every EXTRA mailbox
is its own local MCP server instance (``gmail-<shortname>``) with a
per-instance credential file. This module drives everything automatable —
register the instance, launch the OAuth sign-in, detect completion — and
reports the single irreducibly-manual step (Google's own consent click) back
to the UI as a ``step`` for the Connect-an-account flow to narrate.

The server supplies ``claude_bin`` and callbacks; nothing here reads global
config, which is what makes the flow unit-testable (see test_mailboxes.py).
"""

from __future__ import annotations

import os
import re
import subprocess

GMAIL_MCP_PKG = "@gongrzhe/server-gmail-autoauth-mcp"
GMAIL_MCP_DIR = os.path.expanduser("~/.gmail-mcp")
GMAIL_KEYS_PATH = os.path.join(GMAIL_MCP_DIR, "gcp-oauth.keys.json")
# Read-only subset only — send/modify/delete tools are never granted, same
# posture as every other connector in this system.
GMAIL_MCP_READ_TOOLS = ("search_emails", "read_email", "list_email_labels")


def mailbox_server_name(name):
    slug = re.sub(r"[^a-z0-9-]+", "-", (name or "").strip().lower()).strip("-")
    return ("gmail-" + slug) if slug else ""


def mailbox_token_path(server):
    return os.path.join(GMAIL_MCP_DIR, "credentials-%s.json" % server)


def _mcp_registered(server, claude_bin):
    try:
        r = subprocess.run([claude_bin, "mcp", "get", server],
                           capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False


def _adopt_default_token(server):
    """The upstream `auth` flow may ignore GMAIL_CREDENTIALS_PATH and write
    the default ~/.gmail-mcp/credentials.json — claim it for this instance.
    Safe: the dashboard runs one auth flow at a time."""
    default = os.path.join(GMAIL_MCP_DIR, "credentials.json")
    target = mailbox_token_path(server)
    if os.path.exists(default) and not os.path.exists(target):
        try:
            os.rename(default, target)
        except OSError:
            pass


def mailbox_status(name, claude_bin="claude"):
    server = mailbox_server_name(name)
    if server:
        _adopt_default_token(server)
    return {
        "server": server,
        "keys_present": os.path.exists(GMAIL_KEYS_PATH),
        "keys_path": GMAIL_KEYS_PATH,
        "registered": bool(server) and _mcp_registered(server, claude_bin),
        "authorized": bool(server) and os.path.exists(mailbox_token_path(server)),
    }


def add_mailbox(name, claude_bin="claude", spawn_auth=None, on_connected=None):
    """Drive the flow as far as it can go right now; the returned dict's
    ``step`` (needs_keys | auth_started | connected | error) tells the UI
    what, if anything, to ask of the user. Re-calling is safe at every step.

    ``spawn_auth(cmd, env)`` launches the browser sign-in without blocking
    (the server passes its log-wired Popen); ``on_connected(server)`` is the
    server's grant-tools + audit hook, run exactly once per completed flow.
    """
    server = mailbox_server_name(name)
    if not server:
        return {"step": "error", "message": "give the account a short name, e.g. 'work'"}
    os.makedirs(GMAIL_MCP_DIR, exist_ok=True)
    st = mailbox_status(name, claude_bin)
    if not st["keys_present"]:
        st["step"] = "needs_keys"
        st["message"] = ("one-time setup: a Google OAuth client key file is needed "
                         "(every deployment must use its own — Google requires it)")
        return st
    if not st["registered"]:
        r = subprocess.run(
            [claude_bin, "mcp", "add", server, "--scope", "user",
             "-e", "GMAIL_OAUTH_PATH=" + GMAIL_KEYS_PATH,
             "-e", "GMAIL_CREDENTIALS_PATH=" + mailbox_token_path(server),
             "--", "npx", "-y", GMAIL_MCP_PKG],
            capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return {"step": "error",
                    "message": "mcp add failed: " + (r.stderr or r.stdout)[-300:]}
        st["registered"] = True
    if not st["authorized"]:
        env = {**os.environ,
               "GMAIL_OAUTH_PATH": GMAIL_KEYS_PATH,
               "GMAIL_CREDENTIALS_PATH": mailbox_token_path(server)}
        if spawn_auth is not None:
            spawn_auth(["npx", "-y", GMAIL_MCP_PKG, "auth"], env)
        st["step"] = "auth_started"
        st["message"] = ("a Google sign-in window is opening — pick the %s account "
                         "and approve read access" % name)
        return st
    if on_connected is not None:
        on_connected(server)
    st["step"] = "connected"
    st["message"] = ("%s connected — read-only tools granted; probing identity "
                     "and binding a workspace now" % server)
    return st
