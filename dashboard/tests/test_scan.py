"""Always-on scanning: transcripts, folders, Zoom, the waiting list and drafting."""

import datetime as dt
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import connections   # noqa: E402
import graph         # noqa: E402
import poll_direct   # noqa: E402
import sift          # noqa: E402
import transcripts   # noqa: E402

USER = {"name": "Dana Kowalski", "email": "dana@work.example", "other_emails": [], "slack": "dana.k", "github": ""}

ZOOM_VTT = """WEBVTT

1
00:00:01.000 --> 00:00:04.000
Priya Shah: Okay, um, let's start. Dana, can you send the revised budget by Friday?

2
00:00:04.500 --> 00:00:07.000
Dana Kowalski: Yes, I'll send it Friday.

3
00:00:07.100 --> 00:00:09.000
Dana Kowalski: And I'll set up the vendor call.
"""


def slack(i, ch, user, text):
    return {"connector": "slack", "id": "sl-%d" % i, "date": "2026-10-26T10:00:00Z", "channel": ch,
            "user": user, "user_name": user, "text": text, "thread_ts": None, "reactions": []}


class TestTranscripts(unittest.TestCase):
    def test_vtt_is_cleaned_to_turns(self):
        self.assertEqual(transcripts.clean(ZOOM_VTT),
                         "Priya Shah: Okay, let's start. Dana, can you send the revised budget by Friday?\n"
                         "Dana Kowalski: Yes, I'll send it Friday. And I'll set up the vendor call.")
        self.assertEqual(transcripts.speakers(ZOOM_VTT), ["Priya Shah", "Dana Kowalski"])

    def test_other_formats(self):
        teams = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v Raj Patel>Ship it Monday.</v>\n"
        self.assertEqual(transcripts.clean(teams), "Raj Patel: Ship it Monday.")
        local = "[Priya Shah] 14:05:12\nHi all\n[Dana Kowalski] 14:05:20\nHi\n"
        self.assertEqual(transcripts.clean(local), "Priya Shah: Hi all\nDana Kowalski: Hi")
        old = "14:05:12 From Priya Shah : hello there\n"
        self.assertEqual(transcripts.clean(old), "Priya Shah: hello there")
        otter = "Priya Shah  0:01\nwelcome everyone\nDana Kowalski  0:09\nthanks\n"
        self.assertEqual(transcripts.clean(otter), "Priya Shah: welcome everyone\nDana Kowalski: thanks")

    def test_what_counts_as_a_transcript(self):
        self.assertTrue(transcripts.looks_like_transcript("a/meeting.vtt", ""))
        self.assertTrue(transcripts.looks_like_transcript("a/meeting_saved_closed_caption.txt",
                                                          "[A B] 10:00:01\nx\n" * 4))
        self.assertFalse(transcripts.looks_like_transcript("a/todo.txt", "buy milk\nNote: call mom\n"))

    def test_docx_text(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "Transcript.docx")
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("word/document.xml", "<w:document><w:p><w:t>Raj Patel: Ship it.</w:t></w:p></w:document>")
        self.assertEqual(transcripts.read_text(p).strip(), "Raj Patel: Ship it.")


class TestFolder(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.meet = os.path.join(self.root, "2026-10-26 14.00.12 Budget review 81234567890")
        os.makedirs(self.meet)
        with open(os.path.join(self.meet, "meeting.transcript.vtt"), "w") as f:
            f.write(ZOOM_VTT)
        with open(os.path.join(self.root, "groceries.txt"), "w") as f:
            f.write("eggs, rice")
        os.makedirs(os.path.join(self.root, ".git"))
        with open(os.path.join(self.root, ".git", "x.txt"), "w") as f:
            f.write("ignored")

    def test_new_files_once_and_transcripts_by_kind(self):
        src = {"id": "zoom-folder", "kind": "folder", "path": self.root}
        items, cur = connections.fetch_folder(src, {})
        by = {i["connector"]: i for i in items}
        self.assertEqual(sorted(by), ["file", "transcript"])
        self.assertEqual(by["transcript"]["title"], "Budget review")
        self.assertIn("Dana Kowalski: Yes, I'll send it Friday.", by["transcript"]["text"])
        items2, cur2 = connections.fetch_folder(src, cur)
        self.assertEqual(items2, [])
        with open(os.path.join(self.root, "groceries.txt"), "a") as f:
            f.write(", milk and more")
        items3, _ = connections.fetch_folder(src, cur2)
        self.assertEqual([i["name"] for i in items3], ["groceries.txt"])

    def test_first_check_skips_old_files(self):
        p = os.path.join(self.root, "old.txt")
        with open(p, "w") as f:
            f.write("old note")
        t = time.time() - 40 * 86400
        os.utime(p, (t, t))
        names = [i.get("name") for i in connections.fetch_folder({"id": "f", "path": self.root}, {})[0]]
        self.assertNotIn("old.txt", names)

    def test_sift_keeps_transcripts_and_drops_plain_files(self):
        items, _ = connections.fetch_folder({"id": "f", "path": self.root}, {})
        s = sift.Sifter(USER)
        kept, dropped = s.sift(items)
        self.assertEqual([i["connector"] for i in kept], ["transcript"])
        self.assertEqual(dropped, {"file": 1})
        self.assertTrue(s.is_urgent(kept[0], "meeting"))
        items, _ = connections.fetch_folder({"id": "f", "path": self.root, "keep": "all"}, {})
        self.assertEqual(len(sift.Sifter(USER).sift(items)[0]), 2)


class Zoom(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body):
        b = (body if isinstance(body, str) else json.dumps(body)).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        Zoom.seen.append(("POST", self.path, self.headers.get("Authorization")))
        self._send({"access_token": "tok"})

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        Zoom.seen.append(("GET", self.path, self.headers.get("Authorization")))
        if u.path == "/v2/users/me/recordings":
            base = "http://127.0.0.1:%d" % self.server.server_port
            self._send({"meetings": [
                {"uuid": "abc==", "topic": "Budget review", "start_time": "2026-10-26T21:00:00Z",
                 "host_email": "priya@work.example", "duration": 30,
                 "recording_files": [{"file_type": "MP4", "download_url": base + "/v"},
                                     {"file_type": "TRANSCRIPT", "status": "completed", "download_url": base + "/t"}]},
                {"uuid": "nofile", "topic": "No transcript", "recording_files": []}]})
        else:
            self._send(ZOOM_VTT)


class TestZoom(unittest.TestCase):
    def test_transcripts_of_new_cloud_recordings(self):
        Zoom.seen = []
        srv = HTTPServer(("127.0.0.1", 0), Zoom)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:%d" % srv.server_port
        try:
            src = {"id": "zoom", "kind": "zoom", "account_id": "acc", "client_id": "cid", "client_secret": "sec"}
            items, cur = connections.fetch_zoom(src, {}, base=base + "/v2", oauth=base + "/oauth/token")
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["title"], "Budget review")
            self.assertEqual(items[0]["connector"], "transcript")
            self.assertIn("Priya Shah: Okay, let's start.", items[0]["text"])
            self.assertEqual(cur["done"], ["abc=="])
            self.assertTrue(Zoom.seen[0][2].startswith("Basic "))
            self.assertTrue(all(s[2] == "Bearer tok" for s in Zoom.seen[1:]))
            again, _ = connections.fetch_zoom(src, cur, base=base + "/v2", oauth=base + "/oauth/token")
            self.assertEqual(again, [])
        finally:
            srv.shutdown()


class TestScan(unittest.TestCase):
    NOW = dt.datetime(2026, 10, 26, 21, 30, tzinfo=dt.timezone.utc)   # 2:30pm in Los Angeles

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ws = os.path.join(self.dir, "ws")
        self.gdir = os.path.join(self.ws, "graph")
        connections.save_me(self.dir, {"name": "Dana Kowalski", "emails": ["dana@work.example"], "slack": "dana.k"})
        with open(os.path.join(self.dir, "poll-config.json"), "w") as f:
            json.dump({"timezone": "America/Los_Angeles",
                       "direct": {"interval_min": 5, "flush_min": 240, "flush_start": "08:00", "flush_end": "16:30"}}, f)
        with open(os.path.join(self.dir, poll_direct.SCAN_STATE), "w") as f:
            json.dump({"last_flush": "2026-10-26T20:00:00Z"}, f)      # an hour and a half ago
        self.calls = []

    def fetcher(self, items):
        return lambda d: {"items": items, "per_source": {"s": {"ok": True, "count": len(items)}}}

    def model(self, d, prompt, job="poll_direct"):
        self.calls.append((job, prompt))
        if job == "draft_direct":
            return json.dumps([{"task": "default:action:revised-budget", "action_type": "message_send",
                                "short_summary": "Email to Priya: the revised budget",
                                "proposed_tool_call": 'work-mail.send to Priya, re "Budget", with text: "Hi Priya, [budget]"'}]), 0.01
        return json.dumps([{"kind": "Action", "workspace": "default", "key": "revised-budget",
                            "name": "Send Priya the revised budget", "confidence": 0.9, "edges": [],
                            "attrs": {"due": "2026-10-30", "evidence": ["tr-1"]}}]), 0.03

    def test_non_urgent_waits_and_costs_nothing(self):
        r = poll_direct.check(self.dir, self.gdir, now=self.NOW, scan=True, _model=self.model,
                              _fetch=self.fetcher([slack(1, "#platform", "ines", "@dana.k can you look at the deck next week?")]))
        self.assertTrue(r["queued"])
        self.assertEqual((self.calls, r["cost_usd"], r["waiting"]), ([], 0.0, 1))
        # the next scan with nothing new: still waiting, still no call
        r = poll_direct.check(self.dir, self.gdir, now=self.NOW, scan=True, _model=self.model, _fetch=self.fetcher([]))
        self.assertEqual((self.calls, r["waiting"]), ([], 1))

    def test_transcript_is_read_now_with_what_was_waiting_and_drafted(self):
        poll_direct.check(self.dir, self.gdir, now=self.NOW, scan=True, _model=self.model,
                          _fetch=self.fetcher([slack(1, "#platform", "ines", "@dana.k can you look at the deck next week?")]))
        tr = {"connector": "transcript", "id": "tr-1", "date": "2026-10-26T21:20:00Z", "title": "Budget review",
              "speakers": ["Priya Shah", "Dana Kowalski"], "origin": "file",
              "text": transcripts.clean(ZOOM_VTT)}
        r = poll_direct.check(self.dir, self.gdir, now=self.NOW, scan=True, _model=self.model, _fetch=self.fetcher([tr]))
        self.assertEqual([c[0] for c in self.calls], ["poll_direct", "draft_direct"])
        self.assertIn("look at the deck", self.calls[0][1])          # the waiting item rides along
        self.assertIn("meeting Budget review", self.calls[0][1])
        self.assertIn("Dana Kowalski: Yes, I'll send it Friday.", self.calls[0][1])
        self.assertIn("Send Priya the revised budget", self.calls[1][1])
        self.assertEqual((r["urgent"], r["records"], r["drafts"]), (1, 1, 1))
        self.assertAlmostEqual(r["cost_usd"], 0.04)
        self.assertFalse(os.path.exists(os.path.join(self.dir, poll_direct.PENDING_FILE)))
        with open(os.path.join(self.ws, "approval-queue.md")) as f:
            q = f.read()
        self.assertIn("- status: pending", q)
        self.assertIn("- task: default:action:revised-budget", q)
        self.assertIn("work-mail.send to Priya", q)
        self.assertEqual(poll_direct.pending_queue_tasks(os.path.join(self.ws, "approval-queue.md")),
                         {"default:action:revised-budget"})
        # the same task found again is not drafted twice
        self.calls = []
        poll_direct.check(self.dir, self.gdir, now=self.NOW, _model=self.model,
                          _fetch=self.fetcher([slack(2, "D-priya", "priya", "thanks Dana")]))
        self.assertEqual([c[0] for c in self.calls], ["poll_direct"])

    def test_urgent_message_and_batch_hours(self):
        r = poll_direct.check(self.dir, self.gdir, now=self.NOW, scan=True, _model=self.model,
                              _fetch=self.fetcher([slack(3, "D-raj", "raj", "need the slides today please")]))
        self.assertEqual(r.get("urgent"), 1)
        late = dt.datetime(2026, 10, 27, 5, 0, tzinfo=dt.timezone.utc)   # 10pm: outside batch hours
        self.assertFalse(poll_direct.batch_due(self.dir, late))
        self.assertTrue(poll_direct.batch_due(self.dir, self.NOW + dt.timedelta(hours=4)) is False)  # 6:30pm
        morning = dt.datetime(2026, 10, 27, 16, 0, tzinfo=dt.timezone.utc)  # 9am next day
        self.assertTrue(poll_direct.batch_due(self.dir, morning))

    def test_a_failed_call_keeps_the_waiting_list(self):
        def boom(d, p, job="poll_direct"):
            raise RuntimeError("offline")
        with self.assertRaises(RuntimeError):
            poll_direct.check(self.dir, self.gdir, now=self.NOW, _model=boom,
                              _fetch=self.fetcher([slack(4, "D-raj", "raj", "hi Dana")]))
        r = poll_direct.check(self.dir, self.gdir, now=self.NOW, scan=True, _model=self.model, _fetch=self.fetcher([]))
        self.assertEqual(r["waiting"], 1)


if __name__ == "__main__":
    unittest.main()
