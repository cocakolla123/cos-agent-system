#!/usr/bin/env python3
"""Export the demo dashboard as static pages that need no server.

    python3 demo/build_demo.py && python3 demo/export_static.py

Starts the dashboard in demo mode on a free local port, saves one page per
workspace filter to demo/site/, and replaces the page's network calls with
the same saved responses the demo server gives (demo/state/responses.json).
The result can be hosted anywhere as plain files: no server, no model, no
connector, nothing that can send.
"""
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATE = os.path.join(HERE, "state")
SITE = os.path.join(HERE, "site")
PY = os.environ.get("DEMO_PYTHON", "python3.12")   # server.py needs 3.12+

SHIM = """<script>
/* Demo build: no server behind this page. Every request answers from saved
   responses; nothing is sent anywhere. */
window.__DEMO_RESPONSES = %s;
window.__DEMO_DEFAULT = %s;
function demoReply(path, body) {
  const r = window.__DEMO_RESPONSES[path];
  if (typeof r === "string") return r;
  if (r && typeof r === "object") {
    const probe = ["message", "id", "text"].map(k => String((body || {})[k] || "")).join(" ").toLowerCase();
    for (const k of Object.keys(r)) if (k !== "default" && probe.includes(k.toLowerCase())) return r[k];
    return r["default"] || window.__DEMO_DEFAULT;
  }
  return window.__DEMO_DEFAULT;
}
function demoReload() {}
window.fetch = async function (url, opts) {
  const path = String(url).split("?")[0];
  const json = o => new Response(JSON.stringify(o), {headers: {"Content-Type": "application/json"}});
  if (opts && String(opts.method || "").toUpperCase() === "POST") {
    let body = {};
    try { body = JSON.parse(opts.body || "{}"); } catch (e) {}
    return json({message: demoReply(path, body), demo: true});
  }
  if (path === "/entry-chat-log") return json({messages: []});
  if (path === "/auth-requests") return json({requests: []});
  if (path === "/graph-version") return json({v: "demo"});
  return json({message: window.__DEMO_DEFAULT, demo: true});
};
</script>"""


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def fetch(port, query=""):
    with urllib.request.urlopen("http://127.0.0.1:%d/%s" % (port, query), timeout=30) as r:
        return r.read().decode()


def page_name(ws):
    return "index.html" if ws is None else "ws-%s.html" % ws


def staticize(html_text, shim):
    html_text = html_text.replace("location.reload(", "demoReload(")
    html_text = re.sub(r'href="\?workspace=([a-z0-9-]+)"',
                       lambda m: 'href="%s"' % page_name(None if m.group(1) == "all" else m.group(1)),
                       html_text)
    return html_text.replace("<head>", "<head>\n" + shim, 1)


def main():
    cfg = os.path.join(STATE, "config.json")
    if not os.path.exists(cfg):
        sys.exit("run demo/build_demo.py first")
    resp = json.load(open(os.path.join(STATE, "responses.json")))
    sys.path.insert(0, os.path.join(ROOT, "dashboard"))
    default = ("Demo mode: nothing was sent or changed. In the real app this runs only on "
               "your machine, against your own connected accounts.")
    shim = SHIM % (json.dumps(resp), json.dumps(default))
    workspaces = [w["id"] for w in json.load(open(os.path.join(
        STATE, "workspace", "workspaces.json")))["workspaces"]]
    port = free_port()
    proc = subprocess.Popen([PY, os.path.join(ROOT, "dashboard", "server.py"),
                             "--config", cfg, "--port", str(port)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for _ in range(50):
            try:
                fetch(port)
                break
            except OSError:
                time.sleep(0.2)
        os.makedirs(SITE, exist_ok=True)
        pages = {None: "?workspace=all"}
        pages.update({w: "?workspace=" + w for w in workspaces})
        for ws, query in pages.items():
            with open(os.path.join(SITE, page_name(ws)), "w") as f:
                f.write(staticize(fetch(port, query), shim))
    finally:
        proc.terminate()
        proc.wait(timeout=10)
    print("wrote", SITE, sorted(os.listdir(SITE)))


if __name__ == "__main__":
    main()
