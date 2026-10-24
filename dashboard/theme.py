"""The dashboard's look: "signal".

Swiss poster and transit-signage design: a strict grid, a bold grotesque, black
and white, square corners, hard 1px rules and no shadows. One colour does the
work, a deep cobalt for what you can act on and what is selected; signal red is
kept for what is late. Sections are numbered like a timetable (01 Today, 02
Meetings). Night is true black with the same cobalt, lifted.

No web fonts are loaded (the local app makes no outside requests); the
grotesque stack picks Helvetica Neue on a Mac and the best sans elsewhere.
"""

_DAY = """
  --bg: #ffffff; --panel: #f3f3f1; --panel-2: #e9e9e6; --line: #dcdcd8; --line-strong: #0d0d0d;
  --ink: #0d0d0d; --ink-2: #4a4a48; --ink-3: #74746f;
  --cobalt: #1b3bff; --cobalt-hover: #0026e6; --cobalt-soft: rgba(27,59,255,.08); --on-cobalt: #ffffff;
  --red: #e4002b; --red-soft: rgba(228,0,43,.08);
  --amber: #a55d00; --amber-soft: rgba(255,170,0,.14);
  --green: #00804a; --green-soft: rgba(0,128,74,.10);
  --violet: #6b2bd6; --violet-soft: rgba(107,43,214,.09);
  --row-hover: #f7f7f5; --row-sel: #eef1ff;
  color-scheme: light;
"""

_NIGHT = """
  --bg: #000000; --panel: #0e0e0f; --panel-2: #18181a; --line: #262628; --line-strong: #f2f2f0;
  --ink: #f2f2f0; --ink-2: #b4b4af; --ink-3: #8a8a85;
  --cobalt: #5c78ff; --cobalt-hover: #7a90ff; --cobalt-soft: rgba(92,120,255,.14); --on-cobalt: #000000;
  --red: #ff3b55; --red-soft: rgba(255,59,85,.13);
  --amber: #ffb43d; --amber-soft: rgba(255,180,61,.13);
  --green: #39d98a; --green-soft: rgba(57,217,138,.12);
  --violet: #b18cff; --violet-soft: rgba(177,140,255,.13);
  --row-hover: #0c0c0d; --row-sel: #0d1233;
  color-scheme: dark;
"""

CSS = (":root {" + _DAY + """
  --sans: "Helvetica Neue", Helvetica, "Inter", "Segoe UI", "Arial Nova", Arial, system-ui, sans-serif;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {""" + _NIGHT + """} }
:root[data-theme="dark"] {""" + _NIGHT + "}" + r"""
* { box-sizing: border-box; border-radius: 0; }
html { background: var(--bg); }
body { margin: 0; font-family: var(--sans); font-size: 14.5px; line-height: 1.45; color: var(--ink); background: var(--bg);
  -webkit-font-smoothing: antialiased; letter-spacing: -.003em; counter-reset: navsec; }
a { color: var(--cobalt); text-decoration: none; }
a:hover { text-decoration: underline; text-underline-offset: 2px; }
::selection { background: var(--cobalt); color: var(--on-cobalt); }

/* ---------- shell ---------- */
.nav { position: fixed; inset: 0 auto 0 0; width: 220px; padding: 22px 0 16px; z-index: 60;
  display: flex; flex-direction: column; background: var(--bg); border-right: 1px solid var(--line-strong); }
.brand { display: flex; align-items: center; gap: 10px; padding: 0 20px 22px; margin-bottom: 8px; border-bottom: 1px solid var(--line); }
.brand-mark { width: 14px; height: 14px; background: var(--cobalt); flex: none; }
.brand-mark svg { display: none; }
.brand > div { font-size: 15px; font-weight: 700; letter-spacing: -.02em; }
.nav-group { margin: 18px 20px 6px; font-size: 10.5px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--ink-3); }
.nav a.nav-link { position: relative; display: grid; grid-template-columns: 26px 1fr auto; align-items: baseline;
  padding: 7px 20px; color: var(--ink); font-size: 14px; font-weight: 500; }
.nav a.nav-link::before { counter-increment: navsec; content: counter(navsec, decimal-leading-zero);
  font-size: 11px; font-weight: 500; color: var(--ink-3); font-variant-numeric: tabular-nums; }
.nav a.nav-link:hover { background: var(--panel); text-decoration: none; }
.nav a.nav-link.active { background: var(--ink); color: var(--bg); }
.nav a.nav-link.active::before { color: var(--bg); opacity: .7; }
.nav-count { font-size: 12px; color: var(--ink-3); font-variant-numeric: tabular-nums; }
.nav a.active .nav-count { color: var(--bg); }
.nav-foot { margin-top: auto; padding: 12px 20px 0; border-top: 1px solid var(--line); display: flex; flex-direction: column; align-items: flex-start; gap: 8px; }
.nav-hint { font-size: 11.5px; color: var(--ink-3); line-height: 2; }
.main { margin-left: 220px; min-height: 100vh; }
.topbar { position: sticky; top: 0; z-index: 50; display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
  padding: 14px 36px; background: var(--bg); border-bottom: 1px solid var(--line-strong); }
@media (min-width: 1100px) { .topbar { flex-wrap: nowrap; } }
.topbar-head { display: flex; align-items: baseline; gap: 14px; min-width: 0; flex: 1 1 200px; }
.topbar-title { font-size: 26px; line-height: 1; font-weight: 700; letter-spacing: -.035em; white-space: nowrap; }
.status { display: block; color: var(--ink-3); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.status-dot { display: inline-block; width: 7px; height: 7px; background: var(--green); margin-right: 6px; vertical-align: 0; }
.topbar-actions { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.theme-switch { display: inline-flex; border: 1px solid var(--line-strong); }
.theme-switch button { font: inherit; font-size: 12px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase;
  padding: 6px 10px; border: 0; background: var(--bg); color: var(--ink-2); cursor: pointer; }
.theme-switch button + button { border-left: 1px solid var(--line-strong); }
.theme-switch button:hover { color: var(--ink); background: var(--panel); }
.theme-switch button[aria-checked="true"] { background: var(--ink); color: var(--bg); }
.theme-switch button:focus-visible { outline: 2px solid var(--cobalt); outline-offset: 2px; }
.search-btn { display: inline-flex; align-items: center; gap: 12px; min-width: 200px; justify-content: space-between;
  height: 34px; padding: 0 8px 0 12px; background: var(--panel); color: var(--ink-3); border: 1px solid transparent; font-size: 13px; }
.search-btn:hover { border-color: var(--ink); color: var(--ink); background: var(--panel); }
kbd { font-family: var(--sans); font-size: 10.5px; font-weight: 600; padding: 1px 5px; border: 1px solid var(--line); background: var(--bg); color: var(--ink-2); }
.content-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 32px; padding: 28px 36px 96px; max-width: 1560px; }
.content { min-width: 0; }
.view[hidden] { display: none !important; }
@media (min-width: 1480px) { .content-grid { grid-template-columns: minmax(0, 1fr) 280px; } }
@media (max-width: 899px) {
  .nav { position: sticky; top: 0; inset: auto; width: auto; flex-direction: row; align-items: center; overflow-x: auto;
    padding: 0; border-right: 0; border-bottom: 1px solid var(--line-strong); }
  .brand { padding: 12px 14px; margin: 0; border: 0; border-right: 1px solid var(--line); }
  .brand > div, .nav-group, .nav-count, .nav-hint { display: none; }
  .nav a.nav-link { display: flex; gap: 6px; white-space: nowrap; padding: 12px 14px; }
  .nav-foot { margin: 0; padding: 0 8px; border: 0; flex-direction: row; }
  .main { margin-left: 0; }
  .topbar { position: static; padding: 14px 16px; gap: 10px; }
  .topbar-head { flex-direction: column; gap: 4px; max-width: 100%; }
  .status { max-width: 100%; }
  #wsSlot { max-width: 100%; overflow-x: auto; }
  #wsSlot .ws-switcher { flex-wrap: nowrap; }
  #wsSlot .ws-switcher a { white-space: nowrap; }
  .topbar-actions { margin-left: 0; flex-wrap: wrap; }
  .search-btn { min-width: 0; }
  .content-grid { padding: 18px 16px 96px; }
}

/* ---------- type ---------- */
h1 { font-size: 34px; font-weight: 700; letter-spacing: -.04em; margin: 0 0 4px; }
h2 { font-size: 22px; font-weight: 700; letter-spacing: -.03em; margin: 44px 0 14px; padding: 0 0 10px; border: 0;
  border-bottom: 1px solid var(--line-strong); display: flex; align-items: baseline; gap: 10px; justify-content: flex-start; }
.view > h2:first-child { margin-top: 0; }
h3 { font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-2); margin: 26px 0 10px; }
.meta, .sec-sub, .poll-status, .acct-meta, .auth-note, .cc-sub, .td-empty, .empty, .obj-next-none, .tm-thinking { color: var(--ink-3); }
.meta { font-size: 12.5px; margin-bottom: 10px; }
.quick-line { font-size: 14px; color: var(--ink-2); margin-bottom: 10px; }
.view-intro { color: var(--ink-2); font-size: 14.5px; margin: -2px 0 22px; max-width: 70ch; }
pre { white-space: pre-wrap; font-family: var(--sans); font-size: 14px; line-height: 1.55; color: var(--ink-2);
  background: var(--panel); border: 0; padding: 18px 20px; max-height: 360px; overflow-y: auto; }
code { font-family: var(--mono); font-size: .86em; background: var(--panel-2); padding: .1em .35em; }

/* ---------- controls ---------- */
button { height: 32px; padding: 0 14px; border: 1px solid var(--ink); background: var(--bg); color: var(--ink);
  font: inherit; font-size: 13px; font-weight: 600; cursor: pointer; white-space: nowrap; margin: 0; transition: background .1s, color .1s; }
button:hover { background: var(--ink); color: var(--bg); }
button.primary { background: var(--cobalt); color: var(--on-cobalt); border-color: var(--cobalt); }
button.primary:hover { background: var(--cobalt-hover); border-color: var(--cobalt-hover); color: var(--on-cobalt); }
button.small { height: 28px; padding: 0 11px; font-size: 12.5px; }
button.ghost { background: transparent; border-color: transparent; color: var(--ink-2); padding: 0; height: auto; font-weight: 500; }
button.ghost:hover { color: var(--cobalt); background: transparent; }
button:focus-visible, a:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible, .todo-row:focus-visible {
  outline: 2px solid var(--cobalt); outline-offset: 1px; }
textarea, input[type=text], input[type=password], input[type=time], input[type=number], input:not([type]), select {
  font: inherit; font-size: 14px; color: var(--ink); background: var(--bg); border: 1px solid var(--line); padding: 7px 10px; }
textarea:hover, input:hover, select:hover { border-color: var(--ink-3); }
textarea:focus, input:focus, select:focus { border-color: var(--ink); outline: 0; }
textarea { width: 100%; resize: vertical; margin-bottom: 10px; }
select { height: 32px; padding: 0 8px; }
input::placeholder, textarea::placeholder { color: var(--ink-3); }
.actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
.result { font-size: 12.5px; margin-top: 8px; white-space: pre-wrap; color: var(--green); }
.pill-row { display: flex; gap: 0; flex-wrap: wrap; margin-bottom: 12px; }
.day-pill { height: 28px; padding: 0 12px; font-size: 12.5px; margin-left: -1px; }
.day-pill.on { background: var(--ink); color: var(--bg); }

/* ---------- surfaces ---------- */
.card, .objective-card, .acct-row, .start-research-card, .chat-box, .todo-detail, .side-panel, .auth-box, .mdl-box {
  background: var(--bg); border: 1px solid var(--line); }
.card { padding: 18px 20px; margin-bottom: 12px; }
.card.stale, .card.approved, .card.rejected, .card.superseded { opacity: .55; }
.card.failed { border-color: var(--amber); }
.card.drafted { border-color: var(--cobalt); }
.card-title { font-size: 17px; font-weight: 700; letter-spacing: -.02em; line-height: 1.25; margin: 10px 0 4px; }
.badge, .priority-tag, .tag-pill, .todo-draft, .ws-chip, .sec-count {
  display: inline-flex; align-items: center; height: 20px; padding: 0 7px; border: 0;
  font-size: 11px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; white-space: nowrap;
  background: var(--panel-2); color: var(--ink-2); margin: 0 4px 0 0; }
.badge.pending { background: var(--amber-soft); color: var(--amber); }
.badge.approved { background: var(--green-soft); color: var(--green); }
.badge.rejected, .badge.stale, .badge.superseded { background: var(--red-soft); color: var(--red); }
.badge.failed { background: var(--amber-soft); color: var(--amber); }
.badge.drafted { background: var(--cobalt-soft); color: var(--cobalt); }
.priority-high { background: var(--red); color: #fff; }
.priority-medium { background: var(--panel-2); color: var(--ink); }
.priority-low { background: var(--panel); color: var(--ink-3); }
.tag-ticket, .tag-meeting { background: var(--cobalt-soft); color: var(--cobalt); }
.tag-message { background: var(--violet-soft); color: var(--violet); }
.tag-calendar { background: var(--green-soft); color: var(--green); }
.tag-domain { background: var(--red-soft); color: var(--red); }
.sec-count { background: transparent; color: var(--ink-3); padding: 0; font-size: 14px; font-weight: 500; letter-spacing: 0; text-transform: none; }
.priority-note { color: var(--ink-2); }
.tabs { display: inline-flex; margin: 14px 0 12px; border: 1px solid var(--ink); }
.tab-btn { height: 28px; padding: 0 14px; border: 0; background: transparent; color: var(--ink); font-size: 12.5px; font-weight: 600; }
.tab-btn + .tab-btn { border-left: 1px solid var(--ink); }
.tab-btn:hover { background: var(--panel); color: var(--ink); }
.tab-btn.active { background: var(--ink); color: var(--bg); }
.tab-panel { display: none; } .tab-panel.active { display: block; }
.demo-banner { background: var(--panel); color: var(--ink-2); border: 0; border-left: 4px solid var(--cobalt); padding: 12px 16px; margin: 0 0 26px; font-size: 13px; }
.demo-banner b { color: var(--ink); }
.guardrail-alert { margin: 0 0 18px; padding: 14px 18px; background: var(--red-soft); border: 0; border-left: 4px solid var(--red); font-size: 14px; }
.coverage-note { margin: 0 0 18px; padding: 12px 16px; background: var(--amber-soft); border: 0; border-left: 4px solid var(--amber); font-size: 13.5px; color: var(--ink); }
.start-research-card { padding: 20px 22px; margin: 0 0 18px; border-color: var(--ink); }
.start-research-card h2 { margin: 0 0 8px; border: 0; padding: 0; }

/* ---------- figures ---------- */
.stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 0 0 8px; border-top: 4px solid var(--ink); }
.stat { padding: 14px 18px 18px 0; }
.stat + .stat { padding-left: 18px; border-left: 1px solid var(--line); }
.stat-num { font-size: 64px; font-weight: 700; line-height: .95; letter-spacing: -.06em; font-variant-numeric: tabular-nums; }
.stat-label { color: var(--ink-2); font-size: 12px; font-weight: 600; margin-top: 8px; letter-spacing: .01em; }
.stat-danger .stat-num { color: var(--red); }
.stat-accent .stat-num { color: var(--cobalt); }
@media (max-width: 699px) {
  .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .stat:nth-child(3) { border-left: 0; padding-left: 0; }
  .stat:nth-child(n+3) { border-top: 1px solid var(--line); }
  .stat-num { font-size: 48px; }
}
.briefing { margin: 0 0 32px; border-bottom: 1px solid var(--line); }
.briefing summary { cursor: pointer; color: var(--ink-2); font-size: 12.5px; font-weight: 600; list-style: none; padding: 10px 0; }
.briefing summary::-webkit-details-marker { display: none; }
.briefing summary::before { content: "+  "; color: var(--cobalt); font-weight: 700; }
.briefing[open] summary::before { content: "\2212  "; }
.briefing pre { margin: 0 0 14px; }

/* ---------- task table ---------- */
.graph-command-center { margin: 0 0 26px; padding: 0; background: transparent; border: 0; }
.graph-command-center > h2 { display: none; }
.ws-switcher { display: inline-flex; flex-wrap: wrap; border: 1px solid var(--ink); }
.ws-switcher a { display: inline-flex; align-items: center; height: 28px; padding: 0 12px; color: var(--ink); font-size: 12.5px; font-weight: 600; }
.ws-switcher a + a { border-left: 1px solid var(--ink); }
.ws-switcher a:hover { background: var(--panel); text-decoration: none; }
.ws-switcher a.ws-active { background: var(--ink); color: var(--bg); }
.graph-section { margin: 0 0 34px; }
.graph-section > h3 { font-size: 22px; font-weight: 700; letter-spacing: -.03em; text-transform: none; color: var(--ink); margin: 0 0 4px; display: flex; align-items: baseline; gap: 10px; }
.graph-section > .quick-line { font-size: 13px; color: var(--ink-3); margin: 0 0 16px; }
.graph-section ul { margin: 0; padding: 0; list-style: none; border-top: 1px solid var(--line-strong); }
.graph-section li { margin: 0; padding: 10px 0; font-size: 14px; color: var(--ink); border-bottom: 1px solid var(--line); }
.graph-section a { color: inherit; }
.sec-type { color: var(--ink-3); font-size: 10.5px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; margin-right: 6px; }
.todo-filters { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; margin: 0 0 12px; }
.tf-chips { display: flex; flex-wrap: wrap; }
.tf-chip { height: 30px; padding: 0 12px; border: 1px solid var(--ink); margin-left: -1px; background: var(--bg); color: var(--ink); font-size: 12.5px; font-weight: 600; }
.tf-chip:first-child { margin-left: 0; }
.tf-chip:hover { background: var(--panel); color: var(--ink); }
.tf-chip.tf-on { background: var(--ink); color: var(--bg); }
.tf-n { margin-left: 6px; font-weight: 500; opacity: .6; font-variant-numeric: tabular-nums; }
.tf-tools { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.tf-sel { display: inline-flex; align-items: center; border: 1px solid var(--line); height: 30px; }
.tf-sel span { padding: 0 8px; font-size: 10.5px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-3); border-right: 1px solid var(--line); height: 100%; display: inline-flex; align-items: center; }
.tf-sel select { border: 0; height: 28px; font-size: 13px; background: transparent; }
.tf-search { height: 30px; width: 180px; padding: 0 10px; font-size: 13px; }
.todo-board { display: grid; grid-template-columns: minmax(0, 1.45fr) minmax(340px, 1fr); gap: 28px; align-items: start; }
@media (max-width: 1199px) { .todo-board { grid-template-columns: minmax(0, 1fr); } }
.todo-table { border-top: 4px solid var(--ink); min-width: 0; }
.todo-head, .todo-row { display: grid; grid-template-columns: 58px minmax(0, 1fr) 96px 78px; gap: 14px; align-items: baseline; }
.todo-head { padding: 8px 10px 8px 0; border-bottom: 1px solid var(--line-strong); }
.todo-head > * { font-size: 10.5px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-3); text-align: left; }
.todo-head > :first-child { text-align: right; }
.todo-head button { height: auto; padding: 0; border: 0; background: none; cursor: pointer; }
.todo-head button:hover { color: var(--cobalt); background: none; }
.todo-list { max-height: 72vh; overflow-y: auto; scrollbar-width: thin; }
.todo-row { position: relative; padding: 11px 10px 11px 0; border-bottom: 1px solid var(--line); cursor: pointer; color: var(--ink); background: transparent; margin: 0; outline: 0; }
.todo-row:hover { background: var(--row-hover); }
.todo-selected { background: var(--row-sel) !important; box-shadow: inset 4px 0 0 var(--cobalt); }
.todo-when { font-size: 13px; font-weight: 600; color: var(--ink-2); text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.todo-overdue .todo-when { color: var(--red); }
.todo-main { min-width: 0; }
.todo-title { display: block; font-size: 14.5px; line-height: 1.35; font-weight: 500; }
.todo-high .todo-title { font-weight: 700; }
.todo-sub { display: flex; flex-wrap: wrap; gap: 3px 12px; margin-top: 3px; font-size: 12px; }
.todo-sub:empty { display: none; }
.todo-why { color: var(--ink-3); }
.todo-sub .sec-sub, .todo-late, .todo-quiet { color: var(--ink-3); font-size: 12px; }
.todo-late { color: var(--red); }
.todo-draft { height: auto; padding: 0; background: transparent; color: var(--cobalt); font-size: 12px; font-weight: 600; letter-spacing: 0; text-transform: none; margin: 0; }
.todo-draft::before { content: "\2192\00a0"; }
.todo-kind { font-size: 12px; color: var(--ink-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.todo-pcell { white-space: nowrap; }
.todo-pri { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600; color: var(--ink-2); }
.pri-bars { display: inline-block; height: 11px; }
.todo-pri .pri-bars { background:
    linear-gradient(var(--c1), var(--c1)) 0 100% / 3px 5px no-repeat,
    linear-gradient(var(--c2), var(--c2)) 5px 100% / 3px 8px no-repeat,
    linear-gradient(var(--c3), var(--c3)) 10px 100% / 3px 11px no-repeat; width: 13px; }
.pri-high { color: var(--red); --c1: var(--red); --c2: var(--red); --c3: var(--red); }
.pri-medium { --c1: var(--ink); --c2: var(--ink); --c3: var(--line); }
.pri-low { color: var(--ink-3); --c1: var(--ink-3); --c2: var(--line); --c3: var(--line); }
@media (max-width: 699px) {
  .todo-head, .todo-row { grid-template-columns: 48px minmax(0, 1fr) 62px; }
  .todo-kind, .todo-head > :nth-child(3) { display: none; }
}
.todo-badge { display: none; }
.todo-row[hidden], .todo-divider[hidden], .todo-none[hidden] { display: none !important; }
.todo-none { padding: 28px 0; color: var(--ink-3); text-align: center; }
.todo-divider { padding: 26px 0 8px 72px; font-size: 10.5px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-3); border-bottom: 1px solid var(--line-strong); }
.todo-stale { opacity: .55; } .todo-stale:hover, .todo-stale.todo-selected { opacity: 1; }
.todo-detail { position: sticky; top: 92px; padding: 24px 26px 24px; min-height: 340px; border: 0; border-top: 4px solid var(--cobalt); background: var(--panel); }
.todo-detail .tm-title { width: 100%; font-size: 26px; font-weight: 700; line-height: 1.12; letter-spacing: -.035em; color: var(--ink);
  background: transparent; border: 0; padding: 0; margin: 0; resize: none; overflow: hidden; display: block; field-sizing: content; }
.todo-detail .tm-title:hover, .todo-detail .tm-title:focus { background: var(--bg); }
.tm-meta { margin: 10px 0 18px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; font-size: 13px; color: var(--ink-2); }
.tm-controls { display: flex; gap: 8px; align-items: center; margin: 0 0 22px; flex-wrap: wrap; }
.tm-next { border-top: 1px solid var(--line-strong); padding: 14px 0 0; margin: 0 0 20px; }
.tm-next-head { font-size: 10.5px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--cobalt); margin: 0 0 8px; }
.tm-next .card { margin: 0; padding: 0; background: transparent; border: 0; }
.tm-plan { white-space: pre-wrap; font-size: 14.5px; line-height: 1.55; color: var(--ink); }
.draft-text { background: var(--bg); border: 0; border-left: 4px solid var(--cobalt); padding: 14px 16px; margin: 12px 0 6px; font-size: 15px; line-height: 1.55; }
#tmNote { width: 100%; }
.tm-evidence { margin: 2px 0 12px; font-size: 12px; }
.tm-chat { border-top: 1px solid var(--line); margin-top: 18px; padding-top: 14px; }
.tm-chat-log { max-height: 240px; overflow-y: auto; font-size: 13.5px; display: flex; flex-direction: column; gap: 6px; }
.tm-msg { background: var(--bg); padding: 8px 12px; margin: 0; white-space: pre-wrap; align-self: flex-start; max-width: 90%; }
.tm-you { background: var(--ink); color: var(--bg); align-self: flex-end; }
.objective-card { margin: 0 0 10px; padding: 14px 16px; }
.obj-title { font-weight: 700; font-size: 14.5px; }
.obj-timeline, .obj-next { font-size: 13.5px; color: var(--ink-2); margin-top: 4px; }
.obj-details summary { font-size: 12.5px; color: var(--ink-3); cursor: pointer; margin-top: 6px; }

/* ---------- side column ---------- */
.side-panel { display: none; }
@media (min-width: 1480px) {
  .side-panel { display: block; position: sticky; top: 92px; align-self: start; padding: 0 0 20px; background: transparent;
    border: 0; border-top: 4px solid var(--ink); max-height: calc(100vh - 116px); overflow-y: auto; }
  .side-panel h3 { margin: 12px 0 12px; color: var(--ink); }
}
.today-brief { margin: 0 0 18px; padding: 0; background: transparent; border: 0; font-size: 13.5px; color: var(--ink-2); }
.tb-line { margin: 0 0 12px; } .tb-line strong { color: var(--ink); font-weight: 700; }
.tb-overdue strong { color: var(--red); } .today-brief a { color: var(--ink); text-decoration: underline; text-decoration-color: var(--line); text-underline-offset: 2px; }
.cal-box { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--line-strong); }
.cal-head { font-weight: 700; font-size: 13px; margin-bottom: 8px; }
.cal { width: 100%; border-collapse: collapse; font-size: 12px; text-align: center; font-variant-numeric: tabular-nums; }
.cal th { color: var(--ink-3); font-weight: 700; padding: 4px; font-size: 10px; letter-spacing: .06em; }
.cal td { padding: 0; height: 30px; color: var(--ink-2); }
.cal-out { color: var(--ink-3) !important; opacity: .35; }
.cal-marked { color: var(--ink); font-weight: 700; box-shadow: inset 0 -2px 0 var(--cobalt); }
.cal-today, .cal-today.cal-marked { background: var(--ink); color: var(--bg) !important; font-weight: 700; box-shadow: none; }
.cal-dot { display: none; }

/* ---------- jump palette ---------- */
.palette { position: fixed; inset: 0; z-index: 1200; display: flex; align-items: flex-start; justify-content: center;
  padding: 12vh 16px 16px; background: color-mix(in srgb, var(--bg) 70%, transparent); }
.palette[hidden] { display: none; }
.palette-box { width: min(640px, 100%); background: var(--bg); border: 1px solid var(--line-strong); box-shadow: 12px 12px 0 var(--cobalt); overflow: hidden; }
.palette-input { width: 100%; height: 58px; border: 0 !important; border-bottom: 1px solid var(--line-strong) !important; background: transparent !important;
  padding: 0 20px !important; font-size: 20px !important; font-weight: 600; letter-spacing: -.02em; }
.palette-list { max-height: 52vh; overflow-y: auto; }
.palette-group { padding: 10px 20px 4px; font-size: 10.5px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-3); }
.palette-item { display: flex; align-items: baseline; gap: 14px; padding: 9px 20px; cursor: pointer; font-size: 14.5px; }
.palette-item .pi-when { width: 50px; flex: none; text-align: right; color: var(--ink-3); font-size: 12.5px; font-weight: 600; }
.palette-item .pi-text { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.palette-item .pi-hint { color: var(--ink-3); font-size: 11.5px; }
.palette-item.active { background: var(--cobalt); color: var(--on-cobalt); }
.palette-item.active .pi-when, .palette-item.active .pi-hint { color: var(--on-cobalt); opacity: .8; }
.palette-empty { padding: 18px 20px; color: var(--ink-3); font-size: 14px; }
.palette-foot { display: flex; flex-wrap: wrap; gap: 16px; padding: 10px 20px; border-top: 1px solid var(--line); font-size: 11.5px; color: var(--ink-3); }

/* ---------- chat ---------- */
.chat-bubble { position: fixed; bottom: max(24px, env(safe-area-inset-bottom, 0px)); right: max(24px, env(safe-area-inset-right, 0px));
  width: 52px; height: 52px; background: var(--cobalt); display: grid; place-items: center; cursor: pointer; z-index: 1000; }
.chat-bubble path { fill: var(--on-cobalt); }
.chat-bubble:hover { background: var(--cobalt-hover); }
.chat-panel-hidden { display: none; }
#chatPanel { position: fixed; bottom: 24px; right: 24px; width: min(420px, 92vw); z-index: 1000; padding: 16px; border: 1px solid var(--line-strong); box-shadow: 10px 10px 0 var(--cobalt); }
.chat-panel-header { display: flex; justify-content: space-between; align-items: center; font-weight: 700; font-size: 18px; letter-spacing: -.02em; margin-bottom: 12px; }
.chat-close { cursor: pointer; color: var(--ink-3); font-weight: 400; font-size: 15px; }
.chat-log { max-height: 420px; overflow-y: auto; margin-bottom: 12px; display: flex; flex-direction: column; gap: 6px; }
#chatPanel .chat-log { max-height: 360px; }
.chat-msg { padding: 9px 12px; max-width: 88%; font-size: 14px; }
.chat-you { background: var(--ink); color: var(--bg); align-self: flex-end; }
.chat-assistant { background: var(--panel); color: var(--ink); align-self: flex-start; }
.chat-role { font-size: 10.5px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; opacity: .6; margin-bottom: 2px; }
.chat-you .meta { color: inherit; opacity: .75; }
.chat-body { white-space: pre-wrap; }
.chat-input-row { display: flex; gap: 8px; align-items: flex-end; }
.chat-input-row textarea { flex: 1; margin-bottom: 0; }

/* ---------- settings ---------- */
.mdl-box { padding: 0 20px; margin-bottom: 16px; border-color: var(--line-strong); }
.mdl-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding: 16px 0; border-bottom: 1px solid var(--line); }
.mdl-row:last-child { border-bottom: 0; }
.mdl-tier { flex: 0 1 200px; min-width: 0; } .mdl-tier b { font-size: 16px; font-weight: 700; letter-spacing: -.02em; } .mdl-tier .meta { margin: 2px 0 0; }
.mdl-prov { flex: 0 1 240px; min-width: 0; }
.mdl-model { flex: 1 1 170px; min-width: 0; }
.mdl-effort { flex: 0 0 auto; }
.mdl-key { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--line); }
.mdl-key-name { flex: 0 0 240px; font-weight: 600; }
.mdl-keys { margin: 16px 0; } .mdl-keys summary { cursor: pointer; font-weight: 700; }
.usage-table { width: 100%; border-collapse: collapse; font-size: 14px; margin: 4px 0 10px; border-top: 4px solid var(--ink); }
.usage-table th { text-align: left; font-size: 10.5px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-3); padding: 8px 4px; border-bottom: 1px solid var(--line-strong); }
.usage-table td { padding: 10px 4px; border-bottom: 1px solid var(--line); }
.usage-table .num { text-align: right; font-variant-numeric: tabular-nums; }
.acct-row { margin: 0 0 -1px; padding: 12px 16px; font-size: 14px; }
.acct-dot { font-weight: 700; margin-right: 4px; } .acct-id { color: var(--ink-2); margin: 0 6px; }
.acct-fix { color: var(--red); font-size: 12.5px; margin-top: 4px; }
.auth-overlay { position: fixed; inset: 0; background: color-mix(in srgb, var(--bg) 70%, transparent); z-index: 1100; display: flex; align-items: center; justify-content: center; padding: 16px; }
.auth-box { padding: 22px 24px; max-width: 460px; border-color: var(--line-strong); box-shadow: 10px 10px 0 var(--cobalt); }
.auth-box h3 { margin: 0 0 10px; color: var(--ink); font-size: 18px; letter-spacing: -.02em; text-transform: none; }
.auth-reason { color: var(--ink-2); } .auth-buttons { margin-top: 16px; display: flex; gap: 8px; } .auth-refuse { color: var(--red); }
.inbox-item { font-size: 14px; padding: 10px 0; border-bottom: 1px solid var(--line); color: var(--ink); }
.linked-domain { margin-top: 16px; padding: 14px 16px; background: var(--red-soft); border: 0; border-left: 4px solid var(--red); }
.linked-domain-title { font-weight: 700; font-size: 14px; color: var(--red); margin-bottom: 8px; }
.linked-domain pre { background: var(--bg); color: var(--ink); }
.lite-markdown ul { margin: 4px 0 8px; padding-left: 20px; } .lite-markdown li, .lite-markdown p { font-size: 13.5px; margin: 4px 0; }
.archived-item { opacity: .7; padding: 14px 18px; }
.slack-preview-label, .extra-notes-label { font-size: 12px; color: var(--ink-3); margin: 10px 0 4px; }
.slack-preview { background: var(--panel); border: 0; padding: 10px 12px; font-size: 14px; min-height: 1.5em; margin-bottom: 6px; }
.button-link { display: inline-flex; align-items: center; height: 32px; padding: 0 14px; background: var(--cobalt); color: var(--on-cobalt); font-size: 13px; font-weight: 600; margin: 6px 0; }
.button-link:hover { text-decoration: none; background: var(--cobalt-hover); }
""")
