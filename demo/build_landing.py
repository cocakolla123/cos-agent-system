#!/usr/bin/env python3
"""Assemble the landing page and everything it links to into one folder.

    python3 demo/build_landing.py OUT_DIR [--run lrf-v3]

OUT_DIR/
  index.html            demo/landing/index.html
  explorer.html, explorer.js
  data/                 Dana's computer (demo/build_explorer.py)
  demo/*.html           the dashboard demo (demo/site/), with a link back to
                        the landing page in its side menu. The link hides
                        itself when the dashboard is shown inside the
                        landing page's own frame.
  files.json            published path -> file, for the Artifact publish
Run demo/build_demo.py and demo/export_static.py first so demo/site/ is current.
"""

import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_explorer  # noqa: E402

BACK = ('<a class="back-home" href="../index.html">&larr; Back to the landing page</a>'
        '<style>.back-home{display:block;margin:0 20px 14px;font-size:13px;color:inherit;'
        'opacity:.75;text-decoration:none}.back-home:hover{opacity:1;text-decoration:underline}'
        '.in-landing .back-home{display:none}</style>'
        '<script>try{if(window.parent!==window&&window.parent.document.getElementById("live"))'
        'document.documentElement.classList.add("in-landing")}catch(e){}</script>')
BRAND = '<div class="brand"><span class="brand-mark" aria-hidden="true"></span><div>Chief of Staff</div></div>'


def main(out, run="lrf-v3"):
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "demo"))
    for f in ("index.html", "explorer.html", "explorer.js"):
        shutil.copy(os.path.join(HERE, "landing", f), os.path.join(out, f))
    site = os.path.join(HERE, "site")
    for f in sorted(os.listdir(site)):
        if not f.endswith(".html"):
            continue
        html = open(os.path.join(site, f)).read()
        if html.count(BRAND) != 1:
            raise SystemExit("%s: side-menu brand not found once; update BRAND" % f)
        open(os.path.join(out, "demo", f), "w").write(html.replace(BRAND, BRAND + BACK))
    build_explorer.main(os.path.join(out, "data"), run)
    files = {}
    for root, _, names in os.walk(out):
        for n in names:
            p = os.path.join(root, n)
            rel = os.path.relpath(p, out)
            if rel not in ("index.html", "files.json"):
                files[rel] = p
    json.dump(dict(sorted(files.items())), open(os.path.join(out, "files.json"), "w"), indent=1)
    print("landing: %d files besides index.html" % len(files))


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[a.index("--run") + 1] if "--run" in a else "lrf-v3")
