"""Connector sync under stress: big backlogs, rate limits, partial pages,
disconnects, identical timestamps, edits. The bar for every case: run the
sync until it reports itself complete, and every source event has arrived
exactly once — nothing skipped, nothing duplicated, and an unfinished sync
says so instead of looking like success."""

import functools
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import connections  # noqa: E402


class Server(BaseHTTPRequestHandler):
    routes = {}

    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        status, body, headers = 200, None, {}
        out = Server.routes[u.path](q)
        if isinstance(out, tuple):
            status, body, headers = out
        else:
            body = out
        b = json.dumps(body or {}).encode()
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Server)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_port

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.sleeps = []
        self._sleep = getattr(connections, "_sleep", None)
        connections._sleep = self.sleeps.append

    def tearDown(self):
        connections._sleep = self._sleep

    def drain(self, kind, fetcher, max_runs=50):
        """Sync until a run reports complete; returns (items, per-run results)."""
        got, runs = [], []
        for _ in range(max_runs):
            res = connections.fetch_all(self.dir, _fetchers={kind: fetcher})
            per = res["per_source"]["src"]
            runs.append(per)
            got += res["items"]
            if per.get("ok") and per.get("complete"):
                return got, runs
        self.fail("sync never reported itself complete in %d runs: %r" % (max_runs, runs[-1]))

    def assertExactlyOnce(self, got, expected_ids):
        ids = [i["id"] for i in got]
        self.assertEqual(len(ids), len(set(ids)), "duplicate events delivered")
        self.assertEqual(set(ids), set(expected_ids), "events skipped or invented")


# ---------------------------------------------------------------- Slack

def slack_world(n, start=None):
    start = start or (time.time() - 10 * 86400)
    msgs = [{"ts": "%.6f" % (start + k), "user": "U1", "text": "m%d" % k} for k in range(n)]
    state = {"fail": {}}

    def history(q):
        oldest = float(q.get("oldest") or 0)
        live = [m for m in reversed(msgs) if float(m["ts"]) > oldest]   # Slack pages newest first
        pos = int(q.get("cursor") or 0)
        rule = state["fail"].get(pos // 200)
        if rule:
            kind, left = rule
            state["fail"][pos // 200] = (kind, left - 1) if left > 1 else None
            if kind == "429":
                return 429, {"ok": False, "error": "ratelimited"}, {"Retry-After": "1"}
            return {"ok": False, "error": "internal_error"}
        page = live[pos:pos + 200]
        nxt = str(pos + 200) if pos + 200 < len(live) else ""
        return {"ok": True, "messages": page, "has_more": bool(nxt), "response_metadata": {"next_cursor": nxt}}
    routes = {
        "/api/users.conversations": lambda q: {"ok": True, "channels": [{"id": "C1", "name": "eng"}]},
        "/api/users.info": lambda q: {"ok": True, "user": {"name": "ines", "real_name": "Ines"}},
        "/api/conversations.history": history,
    }
    return msgs, state, routes


class TestSlackStress(Base):
    def setUp(self):
        super().setUp()
        connections.upsert_source(self.dir, {"kind": "slack", "id": "src", "token": "xoxp-test"})

    def fetcher(self):
        return functools.partial(connections.fetch_slack, base=self.base + "/api")

    def ids(self, msgs):
        return ["sl-C1-%s" % m["ts"] for m in msgs]

    def test_ten_thousand_message_backlog_drains_exactly_once(self):
        msgs, _, Server.routes = slack_world(10000)
        got, runs = self.drain("slack", self.fetcher())
        self.assertExactlyOnce(got, self.ids(msgs))
        self.assertEqual([i["text"] for i in got], ["m%d" % k for k in range(10000)])   # oldest first
        self.assertEqual(len(runs), 5)                          # 2,000 a check
        self.assertTrue(all("more waiting" in r["incomplete"] for r in runs[:-1]))

    def test_rate_limit_is_waited_out(self):
        msgs, state, Server.routes = slack_world(450)
        state["fail"][1] = ("429", 2)                          # page 2 is limited twice
        got, runs = self.drain("slack", self.fetcher())
        self.assertExactlyOnce(got, self.ids(msgs))
        self.assertEqual(len(runs), 1)
        self.assertEqual(self.sleeps, [1.0, 1.0])              # Retry-After honoured

    def test_rate_limit_that_never_lifts_fails_without_moving_the_bookmark(self):
        msgs, state, Server.routes = slack_world(450)
        state["fail"][1] = ("429", connections.RATE_RETRIES + 1)
        first = connections.fetch_all(self.dir, _fetchers={"slack": self.fetcher()})
        self.assertFalse(first["per_source"]["src"]["ok"])
        self.assertEqual(first["items"], [])
        got, _ = self.drain("slack", self.fetcher())           # the limit lifts
        self.assertExactlyOnce(got, self.ids(msgs))

    def test_partial_page_keeps_the_channel_bookmark_and_says_so(self):
        msgs, state, Server.routes = slack_world(450)
        state["fail"][1] = ("error", 1)                        # page 2 fails once
        first = connections.fetch_all(self.dir, _fetchers={"slack": self.fetcher()})
        per = first["per_source"]["src"]
        self.assertFalse(per["complete"])
        self.assertIn("eng", per["incomplete"])
        self.assertEqual(first["items"], [])                    # page 1 alone is not delivered
        got, _ = self.drain("slack", self.fetcher())
        self.assertExactlyOnce(got, self.ids(msgs))

    def test_page_cap_fails_loudly_instead_of_dropping_the_oldest(self):
        msgs, _, Server.routes = slack_world(1000)
        old, connections.SLACK_MAX_PAGES = connections.SLACK_MAX_PAGES, 2
        try:
            res = connections.fetch_all(self.dir, _fetchers={"slack": self.fetcher()})
        finally:
            connections.SLACK_MAX_PAGES = old
        per = res["per_source"]["src"]
        self.assertFalse(per["complete"])
        self.assertIn("more than 2 pages", per["incomplete"])
        self.assertEqual(res["items"], [])
        got, _ = self.drain("slack", self.fetcher())
        self.assertExactlyOnce(got, self.ids(msgs))

    def test_status_surfaces_an_incomplete_sync(self):
        _, _, Server.routes = slack_world(2500)
        connections.fetch_all(self.dir, _fetchers={"slack": self.fetcher()})
        row = connections.status(self.dir)["sources"][0]
        self.assertIn("500 more waiting", row["incomplete"])


class TestSlackThreads(Base):
    def test_a_new_reply_in_an_older_thread_is_fetched(self):
        connections.upsert_source(self.dir, {"kind": "slack", "id": "src", "token": "xoxp-test"})
        t0 = time.time() - 5 * 86400
        parent = {"ts": "%.6f" % t0, "user": "U1", "text": "kickoff", "reply_count": 1,
                  "latest_reply": "%.6f" % (t0 + 10), "thread_ts": "%.6f" % t0}
        replies = [dict(parent), {"ts": "%.6f" % (t0 + 10), "user": "U1", "text": "first reply",
                                  "thread_ts": parent["ts"]}]

        def history(q):
            return {"ok": True, "messages": [m for m in [parent] if float(m["ts"]) > float(q["oldest"])]}

        def conv_replies(q):
            return {"ok": True, "messages": [m for m in replies if float(m["ts"]) > float(q.get("oldest") or 0)
                                             or m["ts"] == parent["ts"]]}
        Server.routes = {
            "/api/users.conversations": lambda q: {"ok": True, "channels": [{"id": "C1", "name": "eng"}]},
            "/api/users.info": lambda q: {"ok": True, "user": {"name": "ines"}},
            "/api/conversations.history": history,
            "/api/conversations.replies": conv_replies,
        }
        f = functools.partial(connections.fetch_slack, base=self.base + "/api")
        first = connections.fetch_all(self.dir, _fetchers={"slack": f})
        self.assertEqual(sorted(i["text"] for i in first["items"]), ["first reply", "kickoff"])
        # days later: the parent is far behind the bookmark, and someone replies
        late = {"ts": "%.6f" % (time.time() - 60), "user": "U1", "text": "@dana can you review by today?",
                "thread_ts": parent["ts"]}
        replies.append(late)
        parent["latest_reply"] = late["ts"]
        second = connections.fetch_all(self.dir, _fetchers={"slack": f})
        self.assertEqual([i["text"] for i in second["items"]], ["@dana can you review by today?"])
        third = connections.fetch_all(self.dir, _fetchers={"slack": f})
        self.assertEqual(third["items"], [])


# ---------------------------------------------------------------- Jira

def jira_world(issues):
    def search(q):
        since = q["jql"].split('"')[1]                         # updated >= "YYYY-MM-DD HH:MM"
        live = sorted((i for i in issues.values()
                       if i["fields"]["updated"][:16].replace("T", " ") >= since),
                      key=lambda i: (i["fields"]["updated"], i["key"]))
        start = int(q.get("startAt") or 0)
        return {"issues": live[start:start + 100], "total": len(live),
                "isLast": start + 100 >= len(live)}
    return {"/rest/api/3/search": search}


def issue(key, updated):
    return {"key": key, "fields": {"summary": key, "updated": updated}}


class TestJiraStress(Base):
    def setUp(self):
        super().setUp()
        connections.upsert_source(self.dir, {"kind": "jira", "id": "src", "base_url": self.base,
                                             "email": "e@x.example", "token": "t"})
        st = connections.load_state(self.dir)
        st["src"] = {"cursor": {"updated": "2026-10-01 00:00"}}
        connections.save_state(self.dir, st)

    def test_more_identical_timestamps_than_the_cap_still_drain(self):
        same = "2026-10-27T09:00:00.000+0000"
        issues = {"P-%d" % k: issue("P-%d" % k, same) for k in range(450)}
        Server.routes = jira_world(issues)
        old, connections.MAX_PER_SOURCE = connections.MAX_PER_SOURCE, 100
        try:
            got, runs = self.drain("jira", connections.fetch_jira)
        finally:
            connections.MAX_PER_SOURCE = old
        self.assertExactlyOnce(got, ["jr-P-%d-20261027090000" % k for k in range(450)])
        self.assertEqual(len(runs), 5)

    def test_an_edit_is_one_new_event(self):
        issues = {"P-%d" % k: issue("P-%d" % k, "2026-10-20T09:%02d:00.000+0000" % k) for k in range(30)}
        Server.routes = jira_world(issues)
        first, _ = self.drain("jira", connections.fetch_jira)
        issues["P-3"] = issue("P-3", "2026-10-27T15:00:00.000+0000")    # edited at the source
        again, _ = self.drain("jira", connections.fetch_jira)
        quiet, _ = self.drain("jira", connections.fetch_jira)
        self.assertEqual(len(first), 30)
        self.assertEqual([i["key"] for i in again], ["P-3"])
        self.assertEqual(quiet, [])


# ---------------------------------------------------------------- GitHub

class TestGithubStress(Base):
    def test_identical_update_seconds_past_the_cap_drain(self):
        connections.upsert_source(self.dir, {"kind": "github", "id": "src", "token": "t", "login": "dana"})
        st = connections.load_state(self.dir)
        st["src"] = {"cursor": {"updated_at": "2026-10-01T00:00:00Z"}}
        connections.save_state(self.dir, st)
        same = "2026-10-27T09:00:00Z"
        pool = [{"repository_url": "https://x/repos/o/r", "number": k, "updated_at": same} for k in range(250)]

        def search(q):
            page = int(q.get("page") or 1)
            return {"items": pool[(page - 1) * 100:page * 100], "total_count": len(pool)}
        Server.routes = {"/search/issues": search}
        old, connections.MAX_PER_SOURCE = connections.MAX_PER_SOURCE, 60
        try:
            got, _ = self.drain("github", functools.partial(connections.fetch_github, base=self.base))
        finally:
            connections.MAX_PER_SOURCE = old
        self.assertExactlyOnce(got, ["gh-o-r-%d-20261027090000" % k for k in range(250)])


# ---------------------------------------------------------------- IMAP

class FakeIMAP:
    """A mailbox whose FETCH can drop the connection or return nothing."""

    def __init__(self, uids, broken=None, unreadable=()):
        self.uids, self.broken, self.unreadable = uids, broken, set(unreadable)

    def login(self, *a):
        pass

    def select(self, *a, **k):
        return "OK", [b"1"]

    def response(self, k):
        return k, [b"7"]

    def uid(self, cmd, *args):
        if cmd == "SEARCH":
            lo = int(args[2].split(":")[0]) if args[1] == "UID" else 0
            return "OK", [" ".join(str(u) for u in self.uids if u >= lo).encode()]
        uid = int(args[0])
        if uid == self.broken:
            raise OSError("connection reset by peer")
        if uid in self.unreadable:
            return "OK", [None]
        raw = b"From: a@b.example\r\nSubject: s\r\nDate: Mon, 26 Oct 2026 10:00:00 +0000\r\n\r\nhi"
        return "OK", [(b"1 (X-GM-THRID 5)", raw)]

    def logout(self):
        pass


class TestImapStress(Base):
    def setUp(self):
        super().setUp()
        connections.upsert_source(self.dir, {"kind": "imap", "id": "src", "host": "h",
                                             "user": "d@w.example", "password": "p"})
        st = connections.load_state(self.dir)
        st["src"] = {"cursor": {"INBOX": {"uid": 10, "validity": "7"}}}
        connections.save_state(self.dir, st)
        self.box = FakeIMAP(list(range(11, 31)))

    def fetcher(self):
        return lambda src, cur: connections.fetch_imap(src, cur, _imap=self.box)

    def expected(self, uids=range(11, 31)):
        return ["em-src-INBOX-%d" % u for u in uids]

    def test_disconnect_mid_fetch_loses_nothing(self):
        self.box.broken = 15
        first = connections.fetch_all(self.dir, _fetchers={"imap": self.fetcher()})
        self.assertFalse(first["per_source"]["src"]["ok"])
        self.box.broken = None
        got, _ = self.drain("imap", self.fetcher())
        self.assertExactlyOnce(first["items"] + got, self.expected())

    def test_unreadable_message_holds_the_bookmark_until_it_reads(self):
        self.box.unreadable = {14}
        first = connections.fetch_all(self.dir, _fetchers={"imap": self.fetcher()})
        per = first["per_source"]["src"]
        self.assertEqual([i["id"] for i in first["items"]], self.expected((11, 12, 13)))
        self.assertIn("message 14 could not be read", per["incomplete"])
        self.box.unreadable = set()
        rest, _ = self.drain("imap", self.fetcher())
        self.assertExactlyOnce(first["items"] + rest, self.expected())

    def test_backlog_past_the_cap_drains(self):
        self.box.uids = list(range(11, 1011))
        old, connections.MAX_PER_SOURCE = connections.MAX_PER_SOURCE, 300
        try:
            got, runs = self.drain("imap", self.fetcher())
        finally:
            connections.MAX_PER_SOURCE = old
        self.assertExactlyOnce(got, self.expected(range(11, 1011)))
        self.assertEqual(len(runs), 4)

    def test_deleted_message_does_not_stall_the_sync(self):
        self.box.uids = [u for u in range(11, 31) if u != 17]     # expunged at the source
        got, _ = self.drain("imap", self.fetcher())
        self.assertExactlyOnce(got, [i for i in self.expected() if not i.endswith("-17")])


if __name__ == "__main__":
    unittest.main()
