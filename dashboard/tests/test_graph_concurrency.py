"""Concurrent graph writers: every independent edit survives, no file is torn.

Several processes write one graph at once: the dashboard server (threads),
scheduled checks, the drafting pass and research crawls. Each must load,
change and save under ``graph.transaction`` so nobody saves over an edit made
after they loaded. This drives the real code paths from threads and from
subprocesses against one synthetic graph and then checks that every edit is
there:

  dashboard   server.update_graph_node (Python 3.12+ only, like server.py)
  poll        poll_direct.check with a stub model, including its draft step
  draft       poll_direct.draft_new_tasks "wait" verdicts on a graph loaded
              before a slow model call
  research    cos_tool's ``ingest`` command

A subprocess killed mid-save must leave whole files and release the lock.
All data here is synthetic.

Run as a script (``python test_graph_concurrency.py worker ...``) it is the
subprocess side of the test.
"""

import datetime as _dt
import json
import os
import random
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import connections   # noqa: E402
import cos_tool      # noqa: E402
import graph         # noqa: E402
import poll_direct   # noqa: E402

WS = "default"
USER = {"name": "Dana Kowalski", "emails": ["dana@work.example"], "slack": "dana.k"}
NOW = _dt.datetime(2026, 10, 27, 21, 30, tzinfo=_dt.timezone.utc)
HAS_SERVER = sys.version_info >= (3, 12)       # server.py needs 3.12
KINDS = ["research", "poll", "draft"] + (["dashboard"] if HAS_SERVER else [])
ITERS = 6
THREADS_PER_KIND = 2
PROCS_PER_KIND = 1
MAX_WID = 16    # worker ids are 0..MAX_WID-1; seeded nodes cover them all
KIND_NO = {"research": 0, "poll": 1, "draft": 2, "dashboard": 3}
SHARED = ["shared-%d" % k for k in range(3)]


def _owned(kind, wid):
    """The seeded node a draft/dashboard worker edits (and others hit too)."""
    return "%s-%d" % (kind, wid)


def targets():
    """Seeded nodes every worker also adds attrs to, so paths collide."""
    out = list(SHARED)
    for w in range(MAX_WID):
        out += [_owned("draft", w), _owned("dashboard", w)]
    return out


def seed(root):
    gdir = os.path.join(root, "graph")
    g = graph.Graph()
    for key in targets():
        g.upsert_node("Action", WS, key, name="Synthetic task %s" % key,
                      attrs={"due": "2026-12-01"}, now=NOW)
    g.save(gdir)
    return gdir


def nid(key):
    return graph.node_id(WS, "Action", key)


def _target(kind, wid, i):
    t = targets()
    return t[(KIND_NO[kind] * 7 + wid * 5 + i * 3) % len(t)]


def _attr(kind, wid, i):
    return "%s_%d_%d" % (kind, wid, i)


def _rec(key, attrs, name=None):
    r = {"kind": "Action", "workspace": WS, "key": key, "confidence": 0.9,
         "edges": [], "source": "synthetic", "attrs": attrs}
    if name:
        r["name"] = name
    return r


def _cfg_dir(root, kind, wid):
    d = os.path.join(root, "cfg-%s-%d-%d" % (kind, wid, os.getpid()))
    os.makedirs(d, exist_ok=True)
    connections.save_me(d, USER)
    return d


def _jitter():
    time.sleep(random.random() * 0.004)


# ---------------------------------------------------------------- the paths

def do_research(root, wid, i):
    gdir = os.path.join(root, "graph")
    path = os.path.join(root, "recs-%d-%d-%d.json" % (os.getpid(), wid, i))
    recs = [_rec("research-%d-%d" % (wid, i), {"made_by": "research"}, name="R %d %d" % (wid, i)),
            _rec(_target("research", wid, i), {_attr("research", wid, i): i})]
    with open(path, "w") as f:
        json.dump(recs, f)
    out = cos_tool.cmd_ingest(gdir, path)
    assert out["invalid"] == 0, out


def do_poll(root, wid, i, cfg):
    gdir = os.path.join(root, "graph")
    key = "poll-%d-%d-%d" % (os.getpid(), wid, i)
    item = {"connector": "slack", "id": "sl-%s" % key, "date": "2026-10-27T10:00:00Z",
            "channel": "#platform", "user": "ines", "user_name": "ines",
            "text": "@dana.k can you send the numbers for %s by Friday?" % key,
            "thread_ts": None, "reactions": []}

    def fetch(d):
        return {"items": [item], "per_source": {"slack": {"ok": True, "count": 1}}}

    def model(d, prompt, job="poll_direct"):
        _jitter()             # a slow model: others write meanwhile
        if job == "draft_direct":
            ids = re.findall(r"(?m)^### task (\S+)", prompt)
            return json.dumps([{"task": t, "action_type": "wait",
                                "short_summary": "hold %s" % t} for t in ids]), 0.0
        return json.dumps([_rec(key, {"due": "2026-12-01", "evidence": [item["id"]]},
                                name="Send numbers %s" % key),
                           _rec(_target("poll", wid, i), {_attr("poll", wid, i): i})]), 0.0

    r = poll_direct.check(cfg, gdir, now=NOW, _fetch=fetch, _model=model)
    assert r["records"] == 2 and "draft_error" not in r, r
    return key


def do_draft(root, wid, i, cfg):
    """The draft-missing shape: graph loaded, then a slow model, then save."""
    gdir = os.path.join(root, "graph")
    g = graph.Graph.load(gdir)
    node = g.nodes[nid(_owned("draft", wid))]

    def call(d, prompt, job="draft_direct"):
        _jitter()
        return json.dumps([{"task": node["id"], "action_type": "wait",
                            "short_summary": "hold %d %d" % (wid, i)}]), 0.0

    queue = os.path.join(root, "approval-queue.md")
    poll_direct.draft_new_tasks(cfg, g, [node], {}, USER, NOW, call, queue, graph_dir=gdir)


def do_dashboard(root, wid, i):
    import server
    ok, msg = server.update_graph_node(nid(_owned("dashboard", wid)), note="note %d %d" % (wid, i))
    assert ok, msg


def run_worker(kind, root, wid, iters):
    """Run one worker's edits in order; returns the poll keys it created."""
    cfg = _cfg_dir(root, kind, wid) if kind in ("poll", "draft") else None
    made = []
    for i in range(iters):
        if kind == "research":
            do_research(root, wid, i)
        elif kind == "poll":
            made.append(do_poll(root, wid, i, cfg))
        elif kind == "draft":
            do_draft(root, wid, i, cfg)
        elif kind == "dashboard":
            do_dashboard(root, wid, i)
        _jitter()
    return made


def _setup_server(root):
    import server
    server.COS_DIR = root


# ---------------------------------------------------------------- checks

def missing_edits(root, plan, poll_keys):
    """Every edit ``plan`` ({kind: [wid, ...]}) made, minus what the graph has."""
    g = graph.Graph.load(os.path.join(root, "graph"))
    miss = []

    def attrs(key):
        n = g.nodes.get(nid(key))
        return None if n is None else (n.get("attrs") or {})

    for kind, wids in plan.items():
        for wid in wids:
            for i in range(ITERS):
                a = attrs(_target(kind, wid, i))
                if a is None or a.get(_attr(kind, wid, i)) is None:
                    if kind in ("research", "poll"):
                        miss.append("%s attr %s" % (kind, _attr(kind, wid, i)))
                if kind == "research" and attrs("research-%d-%d" % (wid, i)) is None:
                    miss.append("research node %d-%d" % (wid, i))
            if kind == "draft":
                want = "hold %d %d" % (wid, ITERS - 1)
                got = (attrs(_owned("draft", wid)) or {}).get("next_step")
                if got != want:
                    miss.append("draft %d next_step %r != %r" % (wid, got, want))
            if kind == "dashboard":
                want = "note %d %d" % (wid, ITERS - 1)
                got = (attrs(_owned("dashboard", wid)) or {}).get("note")
                if got != want:
                    miss.append("dashboard %d note %r != %r" % (wid, got, want))
    for key in poll_keys:
        a = attrs(key)
        if a is None:
            miss.append("poll node %s" % key)
        elif a.get("next_step") != "hold %s" % nid(key):
            miss.append("poll %s next_step %r" % (key, a.get("next_step")))
    return miss


class TestConcurrentWriters(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.gdir = seed(self.root)
        if HAS_SERVER:
            import server
            self.saved_cos = server.COS_DIR
            _setup_server(self.root)

    def tearDown(self):
        if HAS_SERVER:
            import server
            server.COS_DIR = self.saved_cos

    def test_threads_and_subprocesses_lose_no_edit(self):
        plan = {k: [] for k in KINDS}
        poll_keys = []
        errors = []
        lock = threading.Lock()
        wid = 0
        procs = []
        for kind in KINDS:
            for _ in range(PROCS_PER_KIND):
                procs.append((kind, wid, subprocess.Popen(
                    [sys.executable, os.path.abspath(__file__), "worker", kind, self.root,
                     str(wid), str(ITERS)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)))
                plan[kind].append(wid)
                wid += 1

        def thread(kind, w):
            try:
                keys = run_worker(kind, self.root, w, ITERS)
                with lock:
                    poll_keys.extend(keys)
            except Exception as e:  # noqa: BLE001
                with lock:
                    errors.append("%s %d: %r" % (kind, w, e))

        threads = []
        for kind in KINDS:
            for _ in range(THREADS_PER_KIND):
                threads.append(threading.Thread(target=thread, args=(kind, wid)))
                plan[kind].append(wid)
                wid += 1
        self.assertLess(wid, MAX_WID)
        for t in threads:
            t.start()
        for t in threads:
            t.join(120)
        for kind, w, p in procs:
            out, err = p.communicate(timeout=120)
            if p.returncode != 0:
                errors.append("subprocess %s %d exit %d: %s" % (kind, w, p.returncode, err[-2000:]))
            else:
                poll_keys.extend(json.loads(out.strip().splitlines()[-1]))
        self.assertEqual(errors, [])
        self.assertEqual(missing_edits(self.root, plan, poll_keys), [])

    def test_wait_verdict_keeps_an_edit_made_during_the_model_call(self):
        """draft_new_tasks used to save the graph it loaded before the model
        call, overwriting anything saved meanwhile."""
        cfg = _cfg_dir(self.root, "draft", 0)
        g = graph.Graph.load(self.gdir)
        task = g.nodes[nid(_owned("draft", 0))]
        other = nid("shared-0")

        def call(d, prompt, job="draft_direct"):
            with graph.transaction(self.gdir):      # someone edits meanwhile
                live = graph.Graph.load(self.gdir)
                live.nodes[other]["attrs"]["note"] = "edited during the call"
                live.save(self.gdir)
            return json.dumps([{"task": task["id"], "action_type": "wait",
                                "short_summary": "hold for the reply"}]), 0.0

        poll_direct.draft_new_tasks(cfg, g, [task], {}, USER, NOW, call,
                                    os.path.join(self.root, "approval-queue.md"),
                                    graph_dir=self.gdir)
        after = graph.Graph.load(self.gdir)
        self.assertEqual(after.nodes[other]["attrs"].get("note"), "edited during the call")
        self.assertEqual(after.nodes[task["id"]]["attrs"].get("next_step"), "hold for the reply")
        self.assertEqual(task["attrs"].get("next_step"), "hold for the reply")

    def test_check_saves_its_wait_verdicts(self):
        """The check's draft step used to drop "wait" holds: no graph_dir."""
        cfg = _cfg_dir(self.root, "poll", 0)
        key = do_poll(self.root, 0, 0, cfg)
        n = graph.Graph.load(self.gdir).nodes[nid(key)]
        self.assertEqual(n["attrs"].get("next_step"), "hold %s" % nid(key))


@unittest.skipIf(os.name != "posix", "SIGKILL is POSIX")
class TestKillMidSave(unittest.TestCase):
    NODES = 3000

    def test_killed_saver_never_leaves_a_torn_file_or_a_held_lock(self):
        root = tempfile.mkdtemp()
        gdir = os.path.join(root, "graph")
        nodes_path = os.path.join(gdir, "nodes.jsonl")
        rng = random.Random(8)
        for round_ in range(8):
            p = subprocess.Popen([sys.executable, os.path.abspath(__file__), "killsave",
                                  gdir, str(self.NODES)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            deadline = time.time() + 30
            while not os.path.exists(nodes_path) and time.time() < deadline:
                time.sleep(0.005)
            time.sleep(rng.random() * 0.15)
            os.kill(p.pid, signal.SIGKILL)
            _, err = p.communicate(timeout=10)
            self.assertEqual(p.returncode, -signal.SIGKILL, err[-500:])
            # whole: every line parses and comes from one save
            with open(nodes_path, encoding="utf-8") as f:
                rows = [json.loads(line) for line in f]
            self.assertEqual(len(rows), self.NODES, "round %d" % round_)
            self.assertEqual(len({r["attrs"]["gen"] for r in rows}), 1, "round %d" % round_)
            # released: the dead holder's lock does not block the next writer
            got = threading.Event()

            def take():
                with graph.transaction(gdir):
                    got.set()
            t = threading.Thread(target=take, daemon=True)
            t.start()
            self.assertTrue(got.wait(10), "lock still held after kill, round %d" % round_)
            t.join(10)


class TestLockBackend(unittest.TestCase):
    def test_posix_uses_fcntl(self):
        if os.name == "posix":
            self.assertEqual(graph.lock_backend(), "fcntl")

    def test_windows_falls_back_to_msvcrt(self):
        calls = []
        fake = types.SimpleNamespace(LK_NBLCK=2, LK_UNLCK=0,
                                     locking=lambda fd, mode, n: calls.append((mode, n)))
        with mock.patch.dict(sys.modules, {"fcntl": None, "msvcrt": fake}):
            self.assertEqual(graph.lock_backend(), "msvcrt")
            with graph.transaction(tempfile.mkdtemp()):
                self.assertEqual(calls, [(2, 1)])
        self.assertEqual(calls, [(2, 1), (0, 1)])

    def test_msvcrt_waits_while_another_holds_it(self):
        state = {"busy": 2}
        calls = []

        def locking(fd, mode, n):
            calls.append(mode)
            if mode == 2 and state["busy"]:
                state["busy"] -= 1
                raise OSError(36, "Resource deadlock avoided")
        fake = types.SimpleNamespace(LK_NBLCK=2, LK_UNLCK=0, locking=locking)
        with mock.patch.dict(sys.modules, {"fcntl": None, "msvcrt": fake}):
            with graph.transaction(tempfile.mkdtemp()):
                pass
        self.assertEqual(calls, [2, 2, 2, 0])

    def test_no_lock_primitive_is_a_clear_error_unless_allowed(self):
        with mock.patch.dict(sys.modules, {"fcntl": None, "msvcrt": None}):
            with mock.patch.dict(os.environ, {"COS_ALLOW_UNLOCKED": ""}):
                with self.assertRaises(graph.LockUnavailable) as cm:
                    with graph.transaction(tempfile.mkdtemp()):
                        pass
                self.assertIn("COS_ALLOW_UNLOCKED", str(cm.exception))
            with mock.patch.dict(os.environ, {"COS_ALLOW_UNLOCKED": "1"}):
                self.assertEqual(graph.lock_backend(), "none")
                with graph.transaction(tempfile.mkdtemp()):
                    pass


def _killsave(gdir, n):
    """Save a big graph over and over until killed."""
    gen = 0
    while True:
        gen += 1
        with graph.transaction(gdir):
            g = graph.Graph()
            for k in range(n):
                g.nodes["%s:Action:k%05d" % (WS, k)] = {
                    "id": "%s:Action:k%05d" % (WS, k), "type": "Action", "workspace": WS,
                    "name": "synthetic %d" % k, "attrs": {"gen": gen, "pad": "x" * 200}}
            g.save(gdir)


if __name__ == "__main__":
    if sys.argv[1:2] == ["worker"]:
        kind, root, wid, iters = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
        if kind == "dashboard":
            _setup_server(root)
        print(json.dumps(run_worker(kind, root, wid, iters)))
    elif sys.argv[1:2] == ["killsave"]:
        _killsave(sys.argv[2], int(sys.argv[3]))
    else:
        unittest.main()
