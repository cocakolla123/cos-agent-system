"""Direct checks: the sift filter, the connectors (fake servers) and poll_direct."""

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
import sift          # noqa: E402

USER = {"name": "Dana Kowalski", "email": "dana@work.example", "other_emails": ["dana@home.example"],
        "slack": "dana.k", "github": "dana-k"}


def mail(i, frm, subj, body, to="dana@work.example", sent=False, thread=None):
    return {"connector": "gmail", "id": "em-%d" % i, "date": "2026-10-13T10:00:00Z", "account": "dana@work.example",
            "labelIds": ["SENT"] if sent else ["INBOX"], "from": frm, "to": [to], "cc": [],
            "subject": subj, "body": body, "threadId": thread or "th-%d" % i}


def slack(i, ch, user, text, thread=None):
    return {"connector": "slack", "id": "sl-%d" % i, "date": "2026-10-13T10:00:00Z", "channel": ch,
            "user": user, "user_name": user, "text": text, "thread_ts": thread, "reactions": []}


class TestSift(unittest.TestCase):
    def setUp(self):
        self.chans = [{"name": "#platform", "is_member": True}, {"name": "#random", "is_member": True}]

    def test_keeps_what_needs_the_user_and_drops_noise(self):
        known = [slack(1, "#platform", "dana.k", "I'll take the cutover")]
        tasks = [{"name": "Finish PLAT-322 cron migration", "sources": []},
                 {"name": "Renew the plantpal.app domain", "sources": []}]
        s = sift.Sifter(USER, self.chans, tasks, known)
        keep = [
            slack(2, "#platform", "ines", "@dana.k can you review this?"),
            slack(3, "D-dana-ines", "ines", "lunch?"),
            slack(4, "#platform", "alex", "+1", thread="sl-1"),
            slack(5, "#platform", "raj", "PLAT-322 can slip to Nov 13"),
            slack(6, "#random", "hr", "@here everyone must finish benefits enrollment by Nov 6"),
            mail(7, "Rosa Lin <rosa@client.example>", "Invoice", "Hi Dana, paid today."),
            mail(8, "Upwork <notifications@upwork.example>", "New message from Marcus Bell", "Marcus: thanks!"),
            mail(9, "dana@work.example", "Re: plan", "Will send Friday", sent=True),
            mail(10, "Namecove <renewals@namecove.example>", "Receipt", "plantpal.app is renewed until 2027"),
        ]
        drop = [
            slack(11, "#platform", "ci-bot", "main #4411 passed"),
            slack(12, "#random", "zoe", "look at this good boy"),
            slack(13, "#platform", "kai", "@omar can you rebase?"),
            mail(14, "Deals <deals@shop.example>", "50% off", "Unsubscribe here"),
            mail(15, "Harborline Bank <alerts@harborline.example>", "Statement ready", "No action is needed."),
            slack(16, "#random", "hr", "@here optional: pizza Thursday"),
        ]
        kept, dropped = s.sift(keep + drop)
        self.assertEqual(sorted(i["id"] for i in kept), sorted(i["id"] for i in keep))
        self.assertEqual(sum(dropped.values()), len(drop))
        self.assertIn("kept 9 of 15", sift.summary_line(kept, dropped))

    def test_trackers(self):
        s = sift.Sifter(USER)
        mine = {"connector": "jira", "id": "jr-1", "key": "RTA-1", "fields": {"summary": "x", "assignee": "Dana Kowalski"}}
        theirs = {"connector": "jira", "id": "jr-2", "key": "RTA-2", "fields": {"summary": "x", "assignee": "Sam"}}
        pr = {"connector": "github", "id": "gh-1", "repo": "org/api", "title": "Fix", "requested_reviewers": ["dana-k"]}
        own_repo = {"connector": "github", "id": "gh-2", "repo": "dana-k/plantpal", "title": "Bump"}
        other = {"connector": "github", "id": "gh-3", "repo": "org/web", "title": "Bump", "user": "bot"}
        self.assertEqual([s.reason(x) for x in (mine, theirs, pr, own_repo, other)],
                         ["assigned", None, "assigned", "assigned", None])

    def test_first_name_alone_is_not_a_mention(self):
        s = sift.Sifter(USER)
        self.assertIsNone(s.reason(slack(1, "#random", "kai", "Dana Lee fixed the build")))
        self.assertEqual(s.reason(slack(2, "#random", "kai", "hi Dana, quick one")), "mention")


# ------------------------------------------------------------- fake services

class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        Fake.seen.append((u.path, q, dict(self.headers)))
        body = Fake.routes.get(u.path)
        if callable(body):
            body = body(q)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        b = (body if isinstance(body, str) else json.dumps(body)).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


class FakeIMAP:
    """Just enough of imaplib.IMAP4 for fetch_imap."""
    def __init__(self, uids):
        self.uids, self.calls = uids, []

    def login(self, u, p):
        self.calls.append(("login", u))

    def select(self, folder, readonly=False):
        self.calls.append(("select", folder, readonly))
        return "OK", [b"3"]

    def response(self, name):
        return name, [b"777"]

    def uid(self, cmd, *args):
        self.calls.append((cmd,) + args)
        if cmd == "SEARCH":
            if args[1] == "UID":
                lo = int(args[2].split(":")[0])
                return "OK", [" ".join(str(u) for u in self.uids if u >= lo).encode()]
            return "OK", [" ".join(str(u) for u in self.uids).encode()]
        uid = int(args[0])
        raw = ("From: Rosa Lin <rosa@client.example>\r\nTo: dana@work.example\r\nSubject: =?utf-8?q?Invoice_INV-0042?=\r\n"
               "Date: Mon, 12 Oct 2026 09:00:00 +0000\r\nMessage-ID: <m%d@x>\r\n\r\nPaid today, %d." % (uid, uid)).encode()
        return "OK", [(b"%d (UID %d X-GM-THRID 99 BODY[] {100}" % (uid, uid), raw), b")"]

    def logout(self):
        self.calls.append(("logout",))


class TestConnections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Fake.seen = []
        cls.srv = HTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_port

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        Fake.seen = []

    def test_settings_are_private_and_status_hides_secrets(self):
        connections.save_me(self.dir, {"name": "Dana Kowalski", "emails": ["dana@work.example"], "slack": "dana.k"})
        connections.upsert_source(self.dir, {"kind": "slack", "id": "work slack", "token": "xoxp-secret"})
        connections.upsert_source(self.dir, {"kind": "slack", "id": "work slack", "token": ""})  # keeps the token
        p = os.path.join(self.dir, "connections.json")
        self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600)
        self.assertEqual(connections.load(self.dir)["sources"][0]["token"], "xoxp-secret")
        self.assertNotIn("xoxp-secret", json.dumps(connections.status(self.dir)))
        self.assertEqual(connections.status(self.dir)["sources"][0]["id"], "work-slack")
        with self.assertRaises(connections.ConnectionError_):
            connections.upsert_source(self.dir, {"kind": "jira", "email": "a@b.example"})

    def test_imap_reads_only_new_uids(self):
        src = {"id": "work", "kind": "imap", "host": "h", "user": "dana@work.example", "password": "p"}
        items, cur = connections.fetch_imap(src, {}, _imap=FakeIMAP([5, 6]))
        self.assertEqual([i["id"] for i in items], ["em-work-INBOX-5", "em-work-INBOX-6"])
        self.assertEqual(items[0]["subject"], "Invoice INV-0042")
        self.assertEqual(items[0]["threadId"], "th-99")
        self.assertEqual(cur["INBOX"], {"uid": 6, "validity": "777"})
        fake = FakeIMAP([5, 6, 7])
        items, cur = connections.fetch_imap(src, cur, _imap=fake)
        self.assertEqual([i["id"] for i in items], ["em-work-INBOX-7"])
        self.assertIn(("select", '"INBOX"', True), fake.calls)         # read-only
        items, _ = connections.fetch_imap(src, {"INBOX": {"uid": 6, "validity": "111"}}, _imap=FakeIMAP([5, 6, 7]))
        self.assertEqual(len(items), 3)                                  # UIDVALIDITY changed: start over

    def test_slack_history_since_bookmark_with_thread_replies(self):
        Fake.routes = {
            "/api/users.conversations": {"ok": True, "channels": [{"id": "C1", "name": "platform"},
                                                                  {"id": "D1", "is_im": True, "user": "U2"}]},
            "/api/users.info": lambda q: {"ok": True, "user": {"name": {"U1": "dana.k", "U2": "ines"}[q["user"]],
                                                               "real_name": "X"}},
            "/api/conversations.history": lambda q: {"ok": True, "messages": (
                [{"ts": "200.000100", "user": "U2", "text": "@dana.k can you?", "reply_count": 1, "latest_reply": "201.0"}]
                if q["channel"] == "C1" else [{"ts": "150.0", "user": "U2", "text": "hi"}])},
            "/api/conversations.replies": {"ok": True, "messages": [
                {"ts": "200.000100", "user": "U2", "text": "@dana.k can you?"},
                {"ts": "201.0", "user": "U1", "text": "yes", "thread_ts": "200.000100"}]},
        }
        items, cur = connections.fetch_slack({"token": "xoxp-1"}, {"C1": "100.0"}, base=self.base + "/api")
        self.assertEqual(sorted(i["channel"] for i in items), ["#platform", "#platform", "D-ines"])
        reply = next(i for i in items if i["text"] == "yes")
        self.assertEqual(reply["thread_ts"], "sl-C1-200.000100")
        self.assertEqual(cur["C1"], "201.0")
        hist = [q for p, q, _ in Fake.seen if p.endswith("conversations.history") and q["channel"] == "C1"]
        self.assertEqual(hist[0]["oldest"], "100.0")
        self.assertEqual(Fake.seen[0][2].get("Authorization"), "Bearer xoxp-1")

    def test_jira_github_ical(self):
        Fake.routes = {
            "/rest/api/3/search": {"issues": [{"key": "PLAT-322", "fields": {
                "summary": "Cron migration", "status": {"name": "In Progress"}, "assignee": {"displayName": "Dana Kowalski"},
                "reporter": {"displayName": "Ines"}, "duedate": "2026-10-16", "priority": {"name": "High"},
                "updated": "2026-10-13T09:30:00.000+0000", "comment": {"comments": [{"author": {"displayName": "Raj"},
                                                                                       "body": "can slip"}]}}}]},
            "/search/issues": {"items": [{"repository_url": "https://api.github.com/repos/org/api", "number": 430,
                                          "title": "CSV import drops last row", "state": "open", "user": {"login": "alex"},
                                          "updated_at": "2026-10-13T08:00:00Z", "assignees": [{"login": "dana-k"}]}]},
            "/cal.ics": ("BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:abc\r\nSUMMARY:Design review\\, v2\r\n"
                         "DTSTART:20261022T170000Z\r\nDTEND:20261022T180000Z\r\nORGANIZER:mailto:ines@work.example\r\n"
                         "ATTENDEE;CN=Dana:mailto:dana@work.example\r\nLAST-MODIFIED:20261012T100000Z\r\n"
                         "DESCRIPTION:Dana presents the\r\n  design doc\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"),
        }
        j, jc = connections.fetch_jira({"base_url": self.base, "email": "d@x.example", "token": "t"}, {"updated": "2026-10-12 00:00"})
        self.assertEqual(j[0]["key"], "PLAT-322")
        self.assertEqual(j[0]["fields"]["assignee"], "Dana Kowalski")
        self.assertEqual(jc["updated"], "2026-10-13 09:30")
        jql = next(q for p, q, _ in Fake.seen if p.endswith("/search"))["jql"]
        self.assertIn('updated >= "2026-10-12 00:00"', jql)
        g, gc = connections.fetch_github({"token": "t", "login": "dana-k"}, {}, base=self.base)
        self.assertEqual((g[0]["repo"], g[0]["number"], g[0]["assignees"]), ("org/api", 430, ["dana-k"]))
        self.assertEqual(gc["updated_at"], "2026-10-13T08:00:00Z")
        c, cc = connections.fetch_ical({"id": "cal", "url": self.base + "/cal.ics"}, {})
        self.assertEqual(c[0]["summary"], "Design review, v2")
        self.assertEqual(c[0]["attendees"], ["dana@work.example"])
        self.assertIn("design doc", c[0]["description"])
        c2, _ = connections.fetch_ical({"id": "cal", "url": self.base + "/cal.ics"}, cc)
        self.assertEqual(c2, [])                                          # nothing modified since

    def test_fetch_all_keeps_bookmark_on_failure(self):
        connections.upsert_source(self.dir, {"kind": "github", "id": "gh", "token": "t"})
        connections.upsert_source(self.dir, {"kind": "slack", "id": "sl", "token": "t"})

        def ok(src, cur):
            return [slack(1, "#x", "a", "b")], {"n": (cur.get("n") or 0) + 1}

        def bad(src, cur):
            raise RuntimeError("401 bad token")
        r = connections.fetch_all(self.dir, _fetchers={"github": bad, "slack": ok})
        self.assertEqual(r["per_source"]["gh"]["ok"], False)
        st = connections.load_state(self.dir)
        self.assertEqual(st["sl"]["cursor"], {"n": 1})
        self.assertNotIn("cursor", st["gh"])
        self.assertEqual(len(connections.recent_items(self.dir)), 1)


class TestPollDirect(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.gdir = os.path.join(self.dir, "graph")
        connections.save_me(self.dir, {"name": "Dana Kowalski", "emails": ["dana@work.example"], "slack": "dana.k"})

    def test_quiet_check_makes_no_model_call(self):
        def fetch(d):
            return {"items": [slack(1, "#random", "zoe", "cat pics")], "per_source": {"slack": {"ok": True, "count": 1}}}

        def model(d, p, job="poll_direct"):
            raise AssertionError("no model call when nothing is kept")
        r = poll_direct.check(self.dir, self.gdir, _fetch=fetch, _model=model)
        self.assertEqual((r["kept"], r["quiet"]), (0, ["slack"]))

    def test_kept_items_go_to_the_model_and_records_into_the_graph(self):
        seen = {}

        def fetch(d):
            return {"items": [slack(1, "#platform", "ines", "@dana.k can you send the Q4 numbers by Friday?"),
                              slack(2, "#platform", "ci-bot", "build passed")],
                    "per_source": {"slack": {"ok": True, "count": 2}}}

        def model(d, prompt, job="poll_direct"):
            seen["prompt"] = prompt
            return json.dumps([{"kind": "Action", "workspace": "default", "key": "q4-numbers",
                                "name": "Send Ines the Q4 numbers", "confidence": 0.9, "edges": [],
                                "source": "sl-1", "attrs": {"due": "2026-10-16", "evidence": ["sl-1"]}}]), 0.01
        r = poll_direct.check(self.dir, self.gdir, _fetch=fetch, _model=model)
        self.assertEqual((r["kept"], r["records"]), (1, 1))
        self.assertIn("can you send the Q4 numbers", seen["prompt"])
        self.assertNotIn("build passed", seen["prompt"])
        self.assertIn("no files and no tools", seen["prompt"])
        self.assertIn("sl-1 · 2026-10-13 10:00 · slack #platform · @ines", seen["prompt"])
        g = graph.Graph.load(self.gdir)
        self.assertTrue(any(n.get("name") == "Send Ines the Q4 numbers" for n in g.nodes.values()))

    def test_triage_keeps_its_picks_and_items_citing_open_tasks(self):
        msgs = [slack(k, "#platform", "ines", "@dana.k fyi %d" % k) for k in range(40)]
        msgs.append(slack(99, "#platform", "raj", "PLAT-322 can slip to Nov 13"))
        g = graph.Graph()
        g.upsert_node("Action", "default", "plat-322", name="Finish PLAT-322 migration", attrs={"evidence": []})
        g.save(self.gdir)
        calls = []

        def fetch(d):
            return {"items": msgs, "per_source": {"slack": {"ok": True, "count": len(msgs)}}}

        def model(d, prompt, job="poll_direct"):
            calls.append((job, prompt))
            return ('["sl-3"]', 0.001) if job == "triage" else ("[]", 0.01)
        r = poll_direct.check(self.dir, self.gdir, _fetch=fetch, _model=model)
        self.assertEqual([c[0] for c in calls], ["triage", "poll_direct"])
        self.assertEqual(r["after_triage"], 2)                       # sl-3 + the PLAT-322 item
        self.assertIn("sl-99", calls[1][1])
        self.assertNotIn("sl-4 ", calls[1][1])
        self.assertAlmostEqual(r["cost_usd"], 0.011)


if __name__ == "__main__":
    unittest.main()


@unittest.skipIf(sys.version_info < (3, 12), "server.py needs Python 3.12")
class TestServerPanel(unittest.TestCase):
    def setUp(self):
        import server
        self.server = server
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = server.DASHBOARD_DIR
        server.DASHBOARD_DIR = self.tmp.name

    def tearDown(self):
        self.server.DASHBOARD_DIR = self.saved
        self.tmp.cleanup()

    def test_panel_lists_connections_without_secrets(self):
        connections.upsert_source(self.tmp.name, {"kind": "github", "id": "gh", "token": "ghp_secret_value", "login": "dana-k"})
        html_ = self.server.render_connections_section()
        self.assertIn("Direct connections", html_)
        self.assertIn("dana-k", html_)
        self.assertNotIn("ghp_secret_value", html_)

    def test_direct_check_can_run_on_an_api_key(self):
        import models
        models.save(self.tmp.name, {"light": {"provider": "claude-code", "model": ""},
                                    "standard": {"provider": "openai", "model": "m"},
                                    "deep": {"provider": "claude-code", "model": ""}})
        self.assertEqual(models.route(self.tmp.name, "poll_direct")["provider"], "openai")
        self.assertEqual(models.route(self.tmp.name, "poll")["provider"], "claude-code")
