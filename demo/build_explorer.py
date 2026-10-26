#!/usr/bin/env python3
"""Turn the full Kestrel world into a browsable file tree for the web.

    python3 demo/build_explorer.py OUT_DIR [--run lrf-v3]

Writes OUT_DIR/index.json (the folder tree, counts, the run's tasks, the answer
key) and OUT_DIR/shards/NN.json (the items, bundled by folder, ~1.5 MB each).
The page loads index.json first and a shard only when a folder is opened.

Folders mirror what Dana's computer would show: Mail per account and month,
Slack channels and DMs, Jira projects, GitHub repos, Calendar months, Drive.
Each item can carry two marks:
  spotted  the recorded run cited it as a source of a task (at C1 or C2)
  answer   the answer key lists it as a source of a task (with the task's
           result in the run)
Everything is fictional; addresses are under .example.
"""

import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LR = os.path.join(ROOT, "evals", "longrun")
sys.path.insert(0, LR)
sys.path.insert(0, os.path.join(ROOT, "evals"))

import build                  # noqa: E402
import score                  # noqa: E402
import graph as graphlib      # noqa: E402
import score_longrun          # noqa: E402

SHARD_BYTES = 1_500_000
ACCOUNTS = {"dana.k@kestrel.example": "Work (dana.k@kestrel.example)",
            "dana.kowalski@mailbox.example": "Personal (dana.kowalski@mailbox.example)",
            "dana.builds@mailbox.example": "Freelance (dana.builds@mailbox.example)",
            "danak.dev@mailbox.example": "Old account (danak.dev@mailbox.example)"}


def month(d):
    return datetime.date.fromisoformat(d[:10]).strftime("%Y-%m %B")


def folder(i):
    c = i["connector"]
    if c == "gmail":
        acct = ACCOUNTS.get(i.get("account"), i.get("account"))
        box = "Sent" if "SENT" in (i.get("labelIds") or []) else "Inbox"
        return ["Mail", acct, box, month(i["date"])]
    if c == "slack":
        ch = i["channel"]
        if ch.startswith("D-") or ch.startswith("mpdm-"):
            return ["Slack", "Direct messages", ch]
        return ["Slack", "Channels", ch]
    if c == "jira":
        return ["Jira", i["key"].split("-")[0]]
    if c == "github":
        return ["GitHub", i["repo"]]
    if c == "calendar":
        return ["Calendar", month(i["date"])]
    if c == "drive":
        mine = any(o in ACCOUNTS for o in i.get("owners") or [])
        return ["Drive", "My Drive" if mine else "Shared with me", month(i["date"])]
    return [c]


def compact(i):
    """What the page shows: a title line, who, the text, and the raw item."""
    c = i["connector"]
    if c == "gmail":
        title, who, text = i.get("subject"), i.get("from"), i.get("body")
    elif c == "slack":
        title, who, text = (i.get("text") or "")[:90], i.get("user_name") or i.get("user"), i.get("text")
    elif c == "jira":
        f = i.get("fields") or {}
        title = "%s  %s" % (i.get("key"), f.get("summary"))
        who = f.get("assignee") or "Unassigned"
        text = "Status: %s. Priority: %s.%s" % (f.get("status"), f.get("priority"),
                                               (" Due " + f["duedate"] + ".") if f.get("duedate") else "")
        if i.get("comments"):
            text += "\n" + "\n".join("%s: %s" % (x.get("author"), x.get("body")) for x in i["comments"])
    elif c == "github":
        title = "#%s %s" % (i.get("number"), i.get("title"))
        who = i.get("user")
        text = (i.get("body") or "") + ("\nState: %s%s" % (i.get("state"), ", merged" if i.get("merged") else ""))
    elif c == "calendar":
        title, who = i.get("summary"), i.get("organizer")
        text = "%s to %s. %s" % (i.get("start"), i.get("end"), i.get("description") or "")
    else:
        title, who, text = i.get("name"), ", ".join(i.get("owners") or []), i.get("content")
    keep = {"gmail": ("account", "to", "cc", "labelIds"), "slack": ("channel", "thread_ts"),
            "jira": ("key",), "github": ("repo", "type", "state", "requested_reviewers", "assignees"),
            "calendar": ("attendees",), "drive": ("owners", "sharedBy")}.get(c, ())
    meta = {k: i[k] for k in keep if i.get(k)}
    if c == "calendar" and meta.get("attendees"):
        meta["attendees"] = [x if isinstance(x, str) else x.get("email") for x in meta["attendees"]][:12]
    out = {"id": i["id"], "c": c, "d": i["date"], "t": title or "", "w": who or "", "x": text or ""}
    if meta:
        out["m"] = meta
    return out


def run_marks(run):
    """Tasks from the recorded run at C1 and C2, and which items each cites."""
    base = os.path.join(ROOT, "evals", "results", "longrun", run)
    if not os.path.isdir(base):
        return [], {}, None
    meta = json.load(open(os.path.join(base, "meta.json")))
    out, by_item = [], {}
    for cp, step, today in (("c1", "c1", "2026-10-13"), ("c2", "f4", "2026-11-10")):
        gdir = os.path.join(base, "graph", step)
        if not os.path.isdir(gdir):
            continue
        g = graphlib.Graph.load(gdir)
        now = graphlib._parse_iso(today)
        for n in score.open_actions(g):
            if not graphlib.is_open_action(n, now=now):
                continue
            a = n.get("attrs") or {}
            ev = a.get("evidence") or []
            ev = ev if isinstance(ev, list) else [ev]
            ids = sorted(set(x for x in ev if isinstance(x, str)) |
                         set(score_longrun._ids(n)))
            t = {"cp": cp, "name": n.get("name"), "ws": n.get("workspace"),
                 "due": str(a.get("due") or "")[:10] or None, "priority": a.get("priority"),
                 "waiting_on": a.get("blocked_on"), "ids": ids}
            out.append(t)
            for x in ids:
                by_item.setdefault(x, []).append(len(out) - 1)
    return out, by_item, meta.get("model")


def main(out, run="lrf-v3"):
    items, gold, meta = build.build("full")
    os.makedirs(os.path.join(out, "shards"), exist_ok=True)
    tasks, spotted, model = run_marks(run) if run else ([], {}, None)
    scores = {}
    for cp in ("c1", "c2"):
        p = os.path.join(ROOT, "evals", "results", "longrun", run or "-", "score_%s.json" % cp)
        if os.path.exists(p):
            scores[cp] = {r["id"]: r for r in json.load(open(p))["arcs"]}
    answers, answer_of = [], {}
    for a in gold:
        res = {cp: {"pass": s[a["id"]].get("pass"), "caught": s[a["id"]].get("caught"),
                    "name": s[a["id"]].get("name"), "present": s[a["id"]].get("present")}
               for cp, s in scores.items() if a["id"] in s}
        answers.append({"id": a["id"], "split": a["split"], "kind": a["phenomenon"],
                        "c1": a.get("c1"), "c2": a.get("c2"), "ids": a["sources"], "result": res})
        for x in a["sources"]:
            answer_of[x] = len(answers) - 1

    # group items into leaf folders
    leaves = {}
    for i in items:
        leaves.setdefault(tuple(folder(i)), []).append(i)
    tree = {"name": "Dana's computer", "children": {}, "n": 0}
    for path, rows in leaves.items():
        node = tree
        node["n"] += len(rows)
        for part in path:
            node = node["children"].setdefault(part, {"name": part, "children": {}, "n": 0})
            node["n"] += len(rows)
        node["leaf"] = "/".join(path)
    for path, rows in leaves.items():
        sp = sum(1 for i in rows if i["id"] in spotted)
        an = sum(1 for i in rows if i["id"] in answer_of)
        node = tree
        for part in (None,) + path:
            node = node if part is None else node["children"][part]
            node["s"] = node.get("s", 0) + sp
            node["a"] = node.get("a", 0) + an

    # bundle leaves into shards
    shard, size, sid, leaf_shard = {}, 0, 0, {}

    def flush():
        nonlocal shard, size, sid
        if shard:
            with open(os.path.join(out, "shards", "%02d.json" % sid), "w") as f:
                json.dump(shard, f, ensure_ascii=False, separators=(",", ":"))
            sid += 1
            shard, size = {}, 0

    for path in sorted(leaves):
        rows = sorted(leaves[path], key=lambda x: x["date"])
        key = "/".join(path)
        data = []
        for i in rows:
            ci = compact(i)
            if i["id"] in spotted:
                ci["s"] = spotted[i["id"]]
            if i["id"] in answer_of:
                ci["a"] = answer_of[i["id"]]
            data.append(ci)
        blob = len(json.dumps(data, ensure_ascii=False))
        if size and size + blob > SHARD_BYTES:
            flush()
        shard[key] = data
        leaf_shard[key] = sid
        size += blob
    flush()

    def strip(node):
        kids = [strip(c) for c in sorted(node["children"].values(), key=lambda c: c["name"])]
        out = {"name": node["name"], "n": node["n"], "s": node.get("s", 0), "a": node.get("a", 0)}
        if kids:
            out["children"] = kids
        if node.get("leaf"):
            out["leaf"] = node["leaf"]
            out["shard"] = leaf_shard[node["leaf"]]
        return out

    index = {"world": "full", "today": meta["today"], "c2": meta["c2"], "run": run, "model": model,
             "total": len(items), "before_first_read": sum(1 for i in items if i["date"] < meta["today"]),
             "tree": strip(tree), "tasks": tasks, "answers": answers, "shards": sid,
             "where": {x: "/".join(folder(i)) for i in items for x in [i["id"]]
                       if i["id"] in spotted or i["id"] in answer_of}}
    with open(os.path.join(out, "index.json"), "w") as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))
    total = sum(os.path.getsize(os.path.join(out, "shards", x)) for x in os.listdir(os.path.join(out, "shards")))
    print("explorer: %d items, %d folders, %d shards (%.1f MB), %d tasks from %s, %d answer tasks" % (
        len(items), len(leaves), sid, total / 1e6, len(tasks), run, len(answers)))


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[a.index("--run") + 1] if "--run" in a else "lrf-v3")
