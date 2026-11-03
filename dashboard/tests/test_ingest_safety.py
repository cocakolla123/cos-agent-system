"""Nothing fetched is lost: bad replies, dry runs, concurrent edits, paging, caps, file modes."""

import json
import os
import stat
import sys
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import connections   # noqa: E402
import graph         # noqa: E402
import poll_direct   # noqa: E402


def slack(i, text, ch="D-ines", user="ines"):
    return {"connector": "slack", "id": "sl-%d" % i, "date": "2026-10-26T10:00:00Z", "channel": ch,
            "user": user, "user_name": user, "text": text, "thread_ts": None, "reactions": []}


REC = {"kind": "Action", "workspace": "default", "key": "q4-numbers", "name": "Send Ines the Q4 numbers",
       "confidence": 0.9, "edges": [], "attrs": {"due": "2026-10-30", "evidence": ["sl-1"]}}


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.gdir = os.path.join(self.dir, "ws", "graph")
        connections.save_me(self.dir, {"name": "Dana Kowalski", "emails": ["dana@work.example"], "slack": "dana.k"})
        connections.upsert_source(self.dir, {"kind": "slack", "id": "work", "token": "xoxp-1"})
        self.served = []
        self._orig = connections.FETCHERS["slack"]

        def fake(src, cursor):
            batch = self.served.pop(0) if self.served else []
            return batch, {"C1": "%d" % (int(cursor.get("C1", "0")) + len(batch))}
        connections.FETCHERS["slack"] = fake

    def tearDown(self):
        connections.FETCHERS["slack"] = self._orig

    def bookmark(self):
        return (connections.load_state(self.dir).get("work") or {}).get("cursor")


class TestNothingLost(Base):
    def test_unreadable_reply_keeps_everything_waiting(self):
        self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?")]]
        with self.assertRaises(poll_direct.ExtractionError):
            poll_direct.check(self.dir, self.gdir, _model=lambda d, p, job="poll_direct": ("Sorry, I can't.", 0.01))
        waiting = poll_direct._read_pending(self.dir)
        self.assertEqual([r["item"]["id"] for r in waiting], ["sl-1"])
        self.assertFalse(os.path.exists(os.path.join(self.gdir, "nodes.jsonl")))
        # the next check reads it again and this time applies it
        r = poll_direct.check(self.dir, self.gdir, draft=False,
                              _model=lambda d, p, job="poll_direct": (json.dumps([REC]), 0.01))
        self.assertEqual(r["records"], 1)
        self.assertEqual(poll_direct._read_pending(self.dir), [])

    def test_failed_reads_back_off_instead_of_retrying_every_scan(self):
        import datetime as dt
        now = dt.datetime(2026, 10, 27, 15, 0, tzinfo=dt.timezone.utc)
        calls = []

        def bad(d, p, job="poll_direct"):
            calls.append(1)
            return "not json", 0.01
        self.served = [[slack(1, "Dana need the deck today please")]]
        with self.assertRaises(poll_direct.ExtractionError):
            poll_direct.check(self.dir, self.gdir, now=now, scan=True, _model=bad)
        r = poll_direct.check(self.dir, self.gdir, now=now + dt.timedelta(minutes=5), scan=True, _model=bad)
        self.assertTrue(r.get("backoff"))
        self.assertEqual(len(calls), 1)
        r = poll_direct.check(self.dir, self.gdir, now=now + dt.timedelta(minutes=61), scan=True, draft=False,
                              _model=lambda d, p, job="poll_direct": (json.dumps([REC]), 0.01))
        self.assertEqual(r["records"], 1)
        self.assertNotIn("read_failures", poll_direct._scan_state(self.dir))

    def test_an_empty_array_is_a_real_answer(self):
        self.served = [[slack(1, "Dana thanks for yesterday")]]
        r = poll_direct.check(self.dir, self.gdir, _model=lambda d, p, job="poll_direct": ("[]", 0.01))
        self.assertEqual((r["records"], poll_direct._read_pending(self.dir)), (0, []))

    def test_invalid_records_are_dropped_and_counted(self):
        self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?")]]
        bad = [REC, {"kind": "Action", "name": "no key or workspace"}, "text", dict(REC, key="x", edges=[{"to": 1}])]
        r = poll_direct.check(self.dir, self.gdir, draft=False,
                              _model=lambda d, p, job="poll_direct": (json.dumps(bad), 0.01))
        self.assertEqual((r["records"], r["invalid_records"]), (1, 3))

    def test_dry_run_moves_no_bookmark(self):
        self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?")], [slack(1, "again")]]
        r = poll_direct.check(self.dir, self.gdir, dry_run=True,
                              _model=lambda *a, **k: self.fail("no model call on a dry run"))
        self.assertTrue(r["dry_run"])
        self.assertIsNone(self.bookmark())
        self.assertEqual(poll_direct._read_pending(self.dir), [])
        self.assertFalse(os.path.isdir(os.path.join(self.dir, "inbox")))

    def test_bookmark_moves_only_after_the_waiting_list_is_saved(self):
        self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?")]]
        orig = poll_direct._write_pending

        def crash(config_dir, rows):
            raise OSError("disk full")
        poll_direct._write_pending = crash
        try:
            with self.assertRaises(OSError):
                poll_direct.check(self.dir, self.gdir, scan=True, _model=lambda *a, **k: ("[]", 0))
        finally:
            poll_direct._write_pending = orig
        self.assertIsNone(self.bookmark())        # the next check fetches the same items again
        self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?")]]
        poll_direct.check(self.dir, self.gdir, scan=True, _model=lambda *a, **k: ("[]", 0))
        self.assertEqual(self.bookmark(), {"C1": "1"})

    def test_a_dashboard_edit_during_the_read_is_kept(self):
        g = graph.Graph()
        g.upsert_node("Action", "default", "old-task", name="Old task", attrs={"priority": "medium"})
        g.save(self.gdir)
        self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?")]]

        def model(d, prompt, job="poll_direct"):
            # the user marks a task done in the dashboard while the model is reading
            with graph.transaction(self.gdir):
                gg = graph.Graph.load(self.gdir)
                gg.get("default:action:old-task")["attrs"]["status"] = "done"
                gg.save(self.gdir)
            return json.dumps([REC]), 0.01
        poll_direct.check(self.dir, self.gdir, draft=False, _model=model)
        g = graph.Graph.load(self.gdir)
        self.assertEqual(g.get("default:action:old-task")["attrs"].get("status"), "done")
        self.assertIsNotNone(g.get("default:action:q4-numbers"))

    def test_private_file_modes(self):
        import datetime as dt
        # a fixed afternoon: with the real clock, a run before the day's first
        # batch slot only queues and writes no graph (CI failed at 00:42 PT)
        now = dt.datetime(2026, 10, 27, 20, 0, tzinfo=dt.timezone.utc)
        old = os.umask(0o022)
        try:
            self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?")]]
            poll_direct.check(self.dir, self.gdir, now=now, scan=True, draft=False,
                              _model=lambda d, p, job="poll_direct": (json.dumps([REC]), 0.01))
        finally:
            os.umask(old)
        mode = lambda p: stat.S_IMODE(os.stat(p).st_mode)  # noqa: E731
        inbox = os.path.join(self.dir, "inbox")
        self.assertEqual(mode(os.path.join(inbox, os.listdir(inbox)[0])), 0o600)
        self.assertEqual(mode(os.path.join(self.dir, "fetch-state.json")), 0o600)
        for f in ("nodes.jsonl", "edges.jsonl"):
            self.assertEqual(mode(os.path.join(self.gdir, f)), 0o600)


class TestQuarantine(Base):
    def test_rejected_records_are_quarantined_with_their_sources(self):
        self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?")]]
        bad = [REC, {"kind": "Action", "name": "no key", "attrs": {"evidence": ["sl-1"]}}, "text"]
        r = poll_direct.check(self.dir, self.gdir, draft=False,
                              _model=lambda d, p, job="poll_direct": (json.dumps(bad), 0.01))
        self.assertEqual((r["records"], r["quarantined"]), (1, 2))
        q = poll_direct.read_quarantine(self.dir)
        self.assertEqual(len(q), 2)
        self.assertTrue(all(row["problems"] for row in q))
        # every rejected record names the item it came from, so nothing is orphaned
        self.assertTrue(all(row["source_items"] == ["sl-1"] for row in q))
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.dir, poll_direct.QUARANTINE_FILE)).st_mode),
                         0o600)
        # the waiting list cleared only because every record is now somewhere durable
        self.assertEqual(poll_direct._read_pending(self.dir), [])

    def test_all_valid_writes_no_quarantine_file(self):
        self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?")]]
        poll_direct.check(self.dir, self.gdir, draft=False,
                          _model=lambda d, p, job="poll_direct": (json.dumps([REC]), 0.01))
        self.assertFalse(os.path.exists(os.path.join(self.dir, poll_direct.QUARANTINE_FILE)))


class TestCrashRecovery(Base):
    """Crash injection at each step between 'items are waiting' and 'waiting
    list cleared': a restart recovers every item, and the replay never
    duplicates a task."""

    def actions(self):
        g = graph.Graph.load(self.gdir)
        return [n for n in g.query(type_="Action")]

    def run_with_crash(self, target, name):
        orig = getattr(target, name)

        def boom(*a, **k):
            raise OSError("crash injected in %s" % name)
        setattr(target, name, boom)
        try:
            with self.assertRaises(OSError):
                poll_direct.check(self.dir, self.gdir, draft=False,
                                  _model=lambda d, p, job="poll_direct": (json.dumps([REC]), 0.01))
        finally:
            setattr(target, name, orig)

    def recover(self):
        # the restart: a fresh check with no new items replays what is waiting
        return poll_direct.check(self.dir, self.gdir, draft=False,
                                 _model=lambda d, p, job="poll_direct": (json.dumps([REC]), 0.01))

    def test_crash_during_graph_save(self):
        self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?")]]
        self.run_with_crash(graph, "_write_jsonl")
        self.assertEqual(len(poll_direct._read_pending(self.dir)), 1)   # still waiting
        self.recover()
        self.assertEqual(len(self.actions()), 1)
        self.assertEqual(poll_direct._read_pending(self.dir), [])

    def test_crash_after_graph_save_before_clear(self):
        self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?")]]
        orig = poll_direct._write_pending
        calls = []

        def clear_crashes(config_dir, rows):
            calls.append(rows)
            if not rows:              # the clear after the graph save
                raise OSError("crash before the waiting list was cleared")
            return orig(config_dir, rows)
        poll_direct._write_pending = clear_crashes
        try:
            with self.assertRaises(OSError):
                poll_direct.check(self.dir, self.gdir, draft=False,
                                  _model=lambda d, p, job="poll_direct": (json.dumps([REC]), 0.01))
        finally:
            poll_direct._write_pending = orig
        self.assertEqual(len(self.actions()), 1)                       # saved once
        self.assertEqual(len(poll_direct._read_pending(self.dir)), 1)  # and still waiting
        self.recover()                                                 # replayed...
        self.assertEqual(len(self.actions()), 1)                       # ...without a duplicate
        self.assertEqual(poll_direct._read_pending(self.dir), [])

    def test_crash_during_state_save(self):
        self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?")]]
        self.run_with_crash(poll_direct, "_save_scan_state")
        self.recover()
        self.assertEqual(len(self.actions()), 1)

    def test_crash_during_bookmark_commit(self):
        self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?")]]
        self.run_with_crash(connections, "commit_fetch")
        self.assertIsNone(self.bookmark())        # not acknowledged: refetched next time
        self.served = [[slack(1, "Dana can you send the Q4 numbers by Friday?")]]
        self.recover()
        self.assertEqual(len(self.actions()), 1)  # the refetch and the waiting copy are one task
        self.assertEqual(self.bookmark(), {"C1": "1"})


class TestDraftAccount(unittest.TestCase):
    def test_a_task_names_its_mailbox_or_nothing(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "config.json"), "w") as f:
            json.dump({"connector_accounts": [{"id": "gmail-personal", "kind": "email"},
                                              {"id": "gmail-asu", "kind": "email"},
                                              {"id": "google-calendar", "kind": "calendar"}]}, f)
        acct = poll_direct.node_email_account
        self.assertEqual(acct({"source": "gmail-personal"}, d), "gmail-personal")
        self.assertEqual(acct({"source": "gmail-asu, google-calendar"}, d), "gmail-asu")
        self.assertIsNone(acct({"source": "gmail-personal, gmail-asu"}, d))   # ambiguous: refuse
        self.assertIsNone(acct({"source": "gmail"}, d))                       # not a configured id


class Pages(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        body = Pages.routes[u.path](q)
        b = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


class TestPaging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Pages)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_port

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_slack_reads_every_page(self):
        msgs = [{"ts": "%d.000100" % (1000 + k), "user": "U1", "text": "m%d" % k} for k in range(450)]
        msgs.reverse()                       # Slack pages newest first

        def history(q):
            start = int(q.get("cursor") or 0)
            page = msgs[start:start + 200]
            nxt = str(start + 200) if start + 200 < len(msgs) else ""
            return {"ok": True, "messages": page, "has_more": bool(nxt), "response_metadata": {"next_cursor": nxt}}
        Pages.routes = {
            "/api/users.conversations": lambda q: {"ok": True, "channels": [{"id": "C1", "name": "platform"}]},
            "/api/users.info": lambda q: {"ok": True, "user": {"name": "ines", "real_name": "Ines"}},
            "/api/conversations.history": history,
        }
        items, cur = connections.fetch_slack({"token": "x"}, {"C1": "1.0"}, base=self.base + "/api")
        self.assertEqual(len(items), 450)
        self.assertEqual(cur["C1"], "1449.000100")

    def test_slack_backlog_past_the_cap_is_read_next_time(self):
        msgs = [{"ts": "%d.000100" % (1000 + k), "user": "U1", "text": "m%d" % k} for k in range(30)]

        def history(q):
            return {"ok": True, "messages": [m for m in msgs if float(m["ts"]) > float(q["oldest"])][::-1]}
        Pages.routes = {
            "/api/users.conversations": lambda q: {"ok": True, "channels": [{"id": "C1", "name": "platform"}]},
            "/api/users.info": lambda q: {"ok": True, "user": {"name": "ines"}},
            "/api/conversations.history": history,
        }
        old, connections.MAX_PER_SOURCE = connections.MAX_PER_SOURCE, 20
        try:
            a, cur = connections.fetch_slack({"token": "x"}, {"C1": "1.0"}, base=self.base + "/api")
            b, cur = connections.fetch_slack({"token": "x"}, cur, base=self.base + "/api")
        finally:
            connections.MAX_PER_SOURCE = old
        self.assertEqual((len(a), len(b)), (20, 10))
        self.assertEqual([i["text"] for i in a + b], ["m%d" % k for k in range(30)])

    def test_jira_and_github_read_every_page(self):
        issues = [{"key": "P-%d" % k, "fields": {"summary": "s", "updated": "2026-10-2%dT09:00:00.000+0000" % (k % 9)}}
                  for k in range(230)]

        def jira(q):
            start = int(q.get("startAt") or 0)
            return {"issues": issues[start:start + 100], "total": len(issues)}

        def gh(q):
            page = int(q.get("page") or 1)
            all_ = [{"repository_url": "https://x/repos/o/r", "number": k, "updated_at": "2026-10-20T00:00:00Z"}
                    for k in range(150)]
            return {"items": all_[(page - 1) * 100:page * 100]}
        Pages.routes = {"/rest/api/3/search": jira, "/search/issues": gh}
        j, _ = connections.fetch_jira({"base_url": self.base, "email": "e", "token": "t"}, {"updated": "2026-10-01 00:00"})
        g, _ = connections.fetch_github({"token": "t", "login": "dana"}, {"updated_at": "2026-10-01T00:00:00Z"},
                                        base=self.base)
        self.assertEqual((len(j), len(g)), (230, 150))


class TestImapCap(unittest.TestCase):
    def test_oldest_first_and_the_rest_next_time(self):
        class IMAP:
            def __init__(self, uids):
                self.uids = uids

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
                raw = b"From: a@b.example\r\nSubject: s\r\nDate: Mon, 26 Oct 2026 10:00:00 +0000\r\n\r\nhi"
                return "OK", [(b"1 (X-GM-THRID 5)", raw)]

            def logout(self):
                pass
        old, connections.MAX_PER_SOURCE = connections.MAX_PER_SOURCE, 3
        try:
            src = {"id": "w", "host": "h", "user": "d@w.example", "password": "p"}
            a, cur = connections.fetch_imap(src, {"INBOX": {"uid": 10, "validity": "7"}}, _imap=IMAP(list(range(11, 16))))
            b, cur = connections.fetch_imap(src, cur, _imap=IMAP(list(range(11, 16))))
        finally:
            connections.MAX_PER_SOURCE = old
        self.assertEqual([i["id"][-2:] for i in a + b], ["11", "12", "13", "14", "15"])


if __name__ == "__main__":
    unittest.main()
