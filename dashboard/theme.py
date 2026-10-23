"""The dashboard's look, in the manner of Apple's own apps.

Light first, dark when the system or the Appearance toggle asks for it. The
system font (SF Pro on a Mac), large bold titles, soft grey grounds, white
grouped lists with hairline dividers, one accent (system blue), pill buttons,
and a translucent sidebar. No web fonts are loaded, so the local app makes no
outside requests.
"""

_LIGHT = """
  --bg: #f5f5f7; --sidebar: rgba(246,246,248,.78); --surface: #ffffff; --surface-2: #f2f2f7;
  --fill: rgba(120,120,128,.12); --fill-2: rgba(120,120,128,.08);
  --hairline: rgba(60,60,67,.14); --separator: rgba(60,60,67,.11);
  --text: #1d1d1f; --text-2: #6e6e73; --text-3: #86868b;
  --accent: #0071e3; --accent-hover: #0077ed; --accent-text: #0066cc; --accent-soft: rgba(0,113,227,.10);
  --on-accent: #ffffff;
  --red: #e5312b; --red-soft: rgba(255,59,48,.10);
  --orange: #c35c00; --orange-soft: rgba(255,149,0,.13);
  --green: #1d8a3c; --green-soft: rgba(52,199,89,.13);
  --purple: #8944ab; --purple-soft: rgba(175,82,222,.11);
  --shadow: 0 1px 2px rgba(0,0,0,.04), 0 4px 16px rgba(0,0,0,.04);
  --shadow-lg: 0 12px 48px rgba(0,0,0,.14);
  color-scheme: light;
"""

_DARK = """
  --bg: #000000; --sidebar: rgba(28,28,30,.72); --surface: #1c1c1e; --surface-2: #2c2c2e;
  --fill: rgba(120,120,128,.24); --fill-2: rgba(120,120,128,.16);
  --hairline: rgba(84,84,88,.6); --separator: rgba(84,84,88,.45);
  --text: #f5f5f7; --text-2: #a1a1a6; --text-3: #8e8e93;
  --accent: #0a84ff; --accent-hover: #409cff; --accent-text: #2997ff; --accent-soft: rgba(10,132,255,.18);
  --on-accent: #ffffff;
  --red: #ff453a; --red-soft: rgba(255,69,58,.16);
  --orange: #ff9f0a; --orange-soft: rgba(255,159,10,.16);
  --green: #30d158; --green-soft: rgba(48,209,88,.16);
  --purple: #bf5af2; --purple-soft: rgba(191,90,242,.16);
  --shadow: none;
  --shadow-lg: 0 12px 48px rgba(0,0,0,.6);
  color-scheme: dark;
"""

CSS = (":root {" + _LIGHT + """
  --font: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Helvetica Neue", Inter, "Segoe UI", system-ui, sans-serif;
  --mono: ui-monospace, "SF Mono", Menlo, monospace;
  --r-lg: 18px; --r: 12px; --r-sm: 9px;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {""" + _DARK + """} }
:root[data-theme="dark"] {""" + _DARK + "}" + r"""
* { box-sizing: border-box; }
html { background: var(--bg); }
body { margin: 0; font-family: var(--font); font-size: 15px; line-height: 1.47; letter-spacing: -.01em;
  color: var(--text); background: var(--bg); -webkit-font-smoothing: antialiased; }
a { color: var(--accent-text); text-decoration: none; }
a:hover { text-decoration: underline; }
::selection { background: var(--accent-soft); }

/* ---------- shell ---------- */
.nav { position: fixed; inset: 0 auto 0 0; width: 248px; padding: 22px 12px 16px; z-index: 60;
  display: flex; flex-direction: column; gap: 1px;
  background: var(--sidebar); backdrop-filter: saturate(180%) blur(24px); -webkit-backdrop-filter: saturate(180%) blur(24px);
  border-right: 1px solid var(--hairline); }
.brand { display: flex; align-items: center; gap: 10px; padding: 0 10px 22px; font-size: 15px; font-weight: 600; letter-spacing: -.02em; }
.brand-mark { width: 30px; height: 30px; border-radius: 8px; display: grid; place-items: center; flex: none;
  background: linear-gradient(160deg, #3d9bff 0%, #0063d6 55%, #4b3ad1 100%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.35), 0 1px 3px rgba(0,40,120,.35); }
.nav-group { margin: 16px 10px 4px; font-size: 12px; font-weight: 600; color: var(--text-3); letter-spacing: 0; }
.nav a.nav-link { display: flex; align-items: center; justify-content: space-between; gap: 8px;
  padding: 6px 10px; border-radius: 8px; color: var(--text); font-size: 14px; font-weight: 450; }
.nav a.nav-link:hover { background: var(--fill-2); text-decoration: none; }
.nav a.nav-link.active { background: var(--accent); color: var(--on-accent); font-weight: 550; }
.nav-count { font-size: 13px; color: var(--text-3); font-variant-numeric: tabular-nums; }
.nav a.active .nav-count { color: rgba(255,255,255,.85); }
.nav-foot { margin-top: auto; padding: 8px 4px 0; }
.main { margin-left: 248px; min-height: 100vh; }
.topbar { position: sticky; top: 0; z-index: 50; display: flex; align-items: flex-end; gap: 16px; flex-wrap: wrap;
  padding: 26px 40px 16px;
  background: color-mix(in srgb, var(--bg) 94%, transparent);
  backdrop-filter: saturate(180%) blur(20px); -webkit-backdrop-filter: saturate(180%) blur(20px); }
.topbar-title { font-size: 32px; line-height: 1.1; font-weight: 700; letter-spacing: -.025em; }
.status { display: inline-flex; align-items: center; gap: 7px; color: var(--text-2); font-size: 13px; padding-bottom: 4px; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--green); }
.topbar-actions { margin-left: auto; display: flex; gap: 8px; padding-bottom: 2px; }
.content-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 28px; padding: 8px 40px 96px; max-width: 1500px; }
.content { min-width: 0; }
.view[hidden] { display: none !important; }
@media (min-width: 1440px) { .content-grid { grid-template-columns: minmax(0, 1fr) 300px; } }
@media (max-width: 899px) {
  .nav { position: sticky; top: 0; inset: auto; width: auto; flex-direction: row; align-items: center; overflow-x: auto;
    padding: 10px 12px; border-right: 0; border-bottom: 1px solid var(--hairline); gap: 2px; }
  .brand { padding: 0 6px 0 0; } .brand > div, .nav-group, .nav-count { display: none; }
  .nav a.nav-link { white-space: nowrap; padding: 6px 12px; border-radius: 999px; }
  .nav-foot { margin: 0 0 0 4px; padding: 0; }
  .main { margin-left: 0; }
  .topbar { position: static; padding: 20px 16px 10px; }
  .topbar-title { font-size: 28px; }
  .status { flex-basis: 100%; order: 3; }
  .topbar-actions { margin-left: 0; }
  .content-grid { padding: 4px 16px 96px; }
}

/* ---------- type ---------- */
h1 { font-size: 32px; font-weight: 700; letter-spacing: -.025em; margin: 0 0 4px; }
h2 { font-size: 22px; font-weight: 700; letter-spacing: -.02em; margin: 40px 0 14px; padding: 0; border: 0;
  display: flex; align-items: center; gap: 10px; justify-content: flex-start; }
.view > h2:first-child { margin-top: 12px; }
h3 { font-size: 13px; font-weight: 600; color: var(--text-2); margin: 22px 0 8px; letter-spacing: 0; }
.meta, .sec-sub, .poll-status, .acct-meta, .auth-note, .cc-sub, .td-empty, .empty, .obj-next-none, .tm-thinking { color: var(--text-3); }
.meta { font-size: 13px; margin-bottom: 10px; }
.quick-line { font-size: 15px; color: var(--text-2); margin-bottom: 10px; }
.view-intro { color: var(--text-2); font-size: 15px; margin: -6px 0 20px; max-width: 64ch; }
pre { white-space: pre-wrap; font-family: var(--font); font-size: 14px; line-height: 1.55; color: var(--text-2);
  background: var(--surface); border-radius: var(--r-lg); padding: 18px 20px; box-shadow: var(--shadow); max-height: 360px; overflow-y: auto; border: 0; }
code { font-family: var(--mono); font-size: .86em; background: var(--fill-2); padding: .1em .35em; border-radius: 5px; }

/* ---------- controls ---------- */
button { height: 32px; padding: 0 16px; border-radius: 980px; border: 0; background: var(--fill); color: var(--text);
  font: inherit; font-size: 14px; font-weight: 500; cursor: pointer; white-space: nowrap; margin: 0;
  transition: background .15s, transform .08s, opacity .15s; }
button:hover { background: var(--fill-2); filter: brightness(.97); }
button:active { transform: scale(.98); }
button.primary { background: var(--accent); color: var(--on-accent); }
button.primary:hover { background: var(--accent-hover); filter: none; }
button.small { height: 28px; padding: 0 14px; font-size: 13px; }
button.ghost { background: transparent; color: var(--accent-text); padding: 0 8px; }
button.ghost:hover { background: var(--fill-2); }
button:focus-visible, a:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible {
  outline: 0; box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 35%, transparent); }
textarea, input[type=text], input[type=password], input[type=time], input[type=number], input:not([type]), select {
  font: inherit; font-size: 15px; color: var(--text); background: var(--fill-2); border: 0; border-radius: 10px; padding: 9px 12px; }
textarea { width: 100%; resize: vertical; margin-bottom: 10px; }
select { height: 34px; padding: 0 10px; }
input::placeholder, textarea::placeholder { color: var(--text-3); }
.actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
.result { font-size: 13px; margin-top: 8px; white-space: pre-wrap; color: var(--green); }
.pill-row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }
.day-pill { height: 28px; padding: 0 12px; font-size: 13px; background: var(--fill-2); color: var(--text-2); }
.day-pill.on { background: var(--accent); color: var(--on-accent); }

/* ---------- surfaces ---------- */
.card, .objective-card, .acct-row, .start-research-card, .chat-box, .todo-detail, .side-panel, .auth-box, .mdl-box {
  background: var(--surface); border: 0; border-radius: var(--r-lg); box-shadow: var(--shadow); }
.card { padding: 20px 22px; margin-bottom: 14px; }
.card.stale, .card.approved, .card.rejected, .card.superseded { opacity: .6; }
.card.failed { box-shadow: inset 0 0 0 1.5px var(--orange), var(--shadow); }
.card.drafted { box-shadow: inset 0 0 0 1.5px var(--accent), var(--shadow); }
.card-title { font-size: 17px; font-weight: 600; letter-spacing: -.02em; margin: 8px 0 4px; line-height: 1.3; }
.badge, .priority-tag, .tag-pill, .todo-draft, .ws-chip, .sec-count {
  display: inline-flex; align-items: center; height: 22px; padding: 0 9px; border-radius: 980px; border: 0;
  font-size: 12px; font-weight: 500; letter-spacing: 0; text-transform: none; white-space: nowrap;
  background: var(--fill-2); color: var(--text-2); margin: 0 4px 0 0; }
.badge.pending { background: var(--orange-soft); color: var(--orange); }
.badge.approved { background: var(--green-soft); color: var(--green); }
.badge.rejected, .badge.stale, .badge.superseded { background: var(--red-soft); color: var(--red); }
.badge.failed { background: var(--orange-soft); color: var(--orange); }
.badge.drafted { background: var(--accent-soft); color: var(--accent-text); }
.priority-high { background: var(--red-soft); color: var(--red); }
.priority-medium { background: var(--orange-soft); color: var(--orange); }
.priority-low { background: var(--fill-2); color: var(--text-2); }
.tag-ticket, .tag-meeting { background: var(--accent-soft); color: var(--accent-text); }
.tag-message { background: var(--purple-soft); color: var(--purple); }
.tag-calendar { background: var(--green-soft); color: var(--green); }
.tag-domain { background: var(--red-soft); color: var(--red); }
.sec-count { height: 20px; padding: 0 7px; font-size: 12px; color: var(--text-3); font-variant-numeric: tabular-nums; }
.priority-note { font-style: normal; color: var(--text-2); }
.tabs { display: inline-flex; gap: 2px; padding: 2px; margin: 12px 0; background: var(--fill-2); border-radius: 9px; }
.tab-btn { height: 26px; padding: 0 14px; border-radius: 7px; background: transparent; color: var(--text); font-size: 13px; font-weight: 500; }
.tab-btn:hover { background: transparent; filter: none; }
.tab-btn.active { background: var(--surface); box-shadow: 0 1px 3px rgba(0,0,0,.12), 0 0 0 .5px rgba(0,0,0,.04); }
:root[data-theme="dark"] .tab-btn.active { background: #636366; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) .tab-btn.active { background: #636366; } }
.tab-panel { display: none; } .tab-panel.active { display: block; }
.demo-banner { background: var(--accent-soft); color: var(--text); border-radius: var(--r); padding: 12px 16px; margin: 0 0 22px; font-size: 14px; border: 0; }
.demo-banner b { color: var(--accent-text); font-weight: 600; }
.guardrail-alert { margin: 0 0 18px; padding: 14px 18px; background: var(--red-soft); border-radius: var(--r); font-size: 14px; border: 0; }
.coverage-note { margin: 0 0 18px; padding: 12px 16px; background: var(--orange-soft); border-radius: var(--r); font-size: 14px; color: var(--text); border: 0; }
.start-research-card { padding: 20px 22px; margin: 0 0 18px; }
.start-research-card h2 { margin: 0 0 6px; }

/* ---------- summary ---------- */
.stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 4px 0 18px;
  background: var(--surface); border-radius: var(--r-lg); box-shadow: var(--shadow); overflow: hidden; }
.stat { padding: 18px 22px; position: relative; }
.stat + .stat::before { content: ""; position: absolute; left: 0; top: 18px; bottom: 18px; width: 1px; background: var(--separator); }
.stat-num { font-size: 34px; font-weight: 700; letter-spacing: -.03em; line-height: 1.05; font-variant-numeric: tabular-nums; }
.stat-label { color: var(--text-2); font-size: 13px; margin-top: 4px; }
.stat-danger .stat-num { color: var(--red); } .stat-accent .stat-num { color: var(--accent-text); }
@media (max-width: 699px) {
  .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .stat:nth-child(3)::before { display: none; }
  .stat:nth-child(n+3) { border-top: 1px solid var(--separator); }
}
.briefing { margin: 0 0 26px; }
.briefing summary { cursor: pointer; color: var(--accent-text); font-size: 14px; list-style: none; }
.briefing summary::-webkit-details-marker { display: none; }
.briefing summary::after { content: " ›"; }
.briefing[open] summary::after { content: " ⌄"; }
.briefing pre { margin-top: 10px; }

/* ---------- task board ---------- */
.graph-command-center { margin: 0 0 24px; padding: 0; background: transparent; border: 0; }
.graph-command-center > h2 { display: none; }
.ws-switcher { display: inline-flex; flex-wrap: wrap; gap: 2px; padding: 2px; margin: 0 0 22px; background: var(--fill-2); border-radius: 9px; }
.ws-switcher a { display: inline-flex; align-items: center; height: 28px; padding: 0 14px; border-radius: 7px; color: var(--text); font-size: 13px; font-weight: 500; }
.ws-switcher a:hover { text-decoration: none; }
.ws-switcher a.ws-active { background: var(--surface); box-shadow: 0 1px 3px rgba(0,0,0,.12); }
:root[data-theme="dark"] .ws-switcher a.ws-active { background: #636366; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) .ws-switcher a.ws-active { background: #636366; } }
.graph-section { margin: 0 0 26px; }
.graph-section > h3 { font-size: 22px; font-weight: 700; letter-spacing: -.02em; color: var(--text); margin: 0 0 4px; display: flex; align-items: center; gap: 8px; }
.graph-section > .quick-line { font-size: 14px; color: var(--text-3); margin: 0 0 14px; }
.graph-section ul { margin: 0; padding: 4px 0; list-style: none; background: var(--surface); border-radius: var(--r-lg); box-shadow: var(--shadow); }
.graph-section li { margin: 0; padding: 11px 18px; font-size: 14px; color: var(--text); border-bottom: 1px solid var(--separator); }
.graph-section li:last-child { border-bottom: 0; }
.graph-section a { color: inherit; }
.sec-type { color: var(--text-3); font-size: 12px; font-weight: 500; margin-right: 4px; }
.todo-board { display: grid; grid-template-columns: minmax(300px, 380px) minmax(0, 1fr); gap: 18px; align-items: start; }
@media (max-width: 1099px) { .todo-board { grid-template-columns: minmax(0, 1fr); } }
.todo-list { max-height: 74vh; overflow-y: auto; background: var(--surface); border-radius: var(--r-lg); box-shadow: var(--shadow); padding: 6px; }
.todo-row { position: relative; padding: 11px 12px 11px 30px; margin: 0; border-radius: 11px; cursor: pointer; font-size: 14.5px; line-height: 1.38;
  color: var(--text); background: transparent; border: 0; transition: background .12s; }
.todo-row + .todo-row::after { content: ""; position: absolute; left: 30px; right: 12px; top: 0; height: 1px; background: var(--separator); }
.todo-row:hover { background: var(--fill-2); }
.todo-row::before { content: ""; position: absolute; left: 12px; top: 16px; width: 8px; height: 8px; border-radius: 50%; background: var(--text-3); }
.todo-high::before { background: var(--red); } .todo-medium::before { background: var(--orange); } .todo-low::before { background: #c7c7cc; }
.todo-selected { background: var(--accent-soft) !important; }
.todo-selected::after, .todo-selected + .todo-row::after { display: none; }
.todo-badge { display: none; }
.todo-row .sec-sub, .todo-late, .todo-quiet { display: block; margin-top: 2px; font-size: 13px; font-weight: 400; }
.todo-row .sec-sub { color: var(--text-3); }
.todo-late { color: var(--red); }
.todo-quiet { color: var(--text-3); }
.todo-draft { height: auto; padding: 0; margin: 3px 0 0; background: transparent; color: var(--accent-text); font-size: 12.5px; font-weight: 500; display: inline-flex; }
.todo-draft::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: var(--accent); margin-right: 6px; align-self: center; }
.todo-divider { margin: 10px 8px 4px; padding: 12px 4px 4px; border-top: 1px solid var(--separator); font-size: 12.5px; color: var(--text-3); }
.todo-stale { opacity: .62; } .todo-stale:hover { opacity: 1; }
.todo-detail { position: sticky; top: 104px; padding: 26px 28px; min-height: 340px; }
.todo-detail .tm-title { width: 100%; font-size: 24px; font-weight: 700; letter-spacing: -.025em; line-height: 1.2; color: var(--text);
  background: transparent; border: 0; border-radius: 8px; padding: 2px 6px; margin: 0 0 0 -6px;
  resize: none; overflow: hidden; display: block; field-sizing: content; }
.todo-detail .tm-title:hover, .todo-detail .tm-title:focus { background: var(--fill-2); }
.tm-meta { margin: 8px 0 18px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; font-size: 14px; color: var(--text-2); }
.tm-meta .ws-chip { background: var(--fill-2); }
.tm-controls { display: flex; gap: 8px; align-items: center; margin: 0 0 20px; flex-wrap: wrap; }
.tm-next { background: var(--bg); border-radius: 16px; padding: 18px 20px; margin: 0 0 18px; border: 0; }
:root[data-theme="dark"] .tm-next { background: var(--surface-2); }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) .tm-next { background: var(--surface-2); } }
.tm-next-head { font-size: 13px; font-weight: 600; color: var(--text-2); margin: 0 0 8px; letter-spacing: 0; text-transform: none; }
.tm-next .card { margin: 0; padding: 0; background: transparent; box-shadow: none; }
.tm-plan { white-space: pre-wrap; font-size: 15px; line-height: 1.5; color: var(--text); }
.draft-text { background: var(--surface); border-radius: 12px; padding: 14px 16px; margin: 10px 0 4px; border: 0; box-shadow: var(--shadow); }
#tmNote { width: 100%; }
.tm-evidence { margin: 2px 0 12px; font-size: 12.5px; }
.tm-chat { border-top: 1px solid var(--separator); margin-top: 16px; padding-top: 16px; }
.tm-chat-log { max-height: 240px; overflow-y: auto; font-size: 14px; display: flex; flex-direction: column; gap: 6px; }
.tm-msg { background: var(--fill-2); border-radius: 18px; padding: 8px 14px; margin: 0; white-space: pre-wrap; align-self: flex-start; max-width: 88%; }
.tm-you { background: var(--accent); color: var(--on-accent); align-self: flex-end; }
.objective-card { margin: 0 0 10px; padding: 16px 18px; }
.obj-title { font-weight: 600; font-size: 15px; }
.obj-timeline, .obj-next { font-size: 14px; color: var(--text-2); margin-top: 4px; }
.obj-next a { color: var(--accent-text); }
.obj-details summary { font-size: 13px; color: var(--accent-text); cursor: pointer; margin-top: 6px; }

/* ---------- right rail ---------- */
.side-panel { display: none; }
@media (min-width: 1440px) {
  .side-panel { display: block; position: sticky; top: 104px; align-self: start; padding: 20px; max-height: calc(100vh - 128px); overflow-y: auto; }
  .side-panel h3 { margin: 0 0 12px; color: var(--text); font-size: 17px; font-weight: 700; letter-spacing: -.02em; }
}
.today-brief { margin: 0 0 18px; padding: 0; background: transparent; border: 0; font-size: 14px; color: var(--text-2); }
.tb-line { margin: 0 0 10px; } .tb-line strong { color: var(--text); font-weight: 600; }
.tb-overdue strong { color: var(--red); } .today-brief a { color: var(--accent-text); }
.cal-box { margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--separator); }
.cal-head { font-weight: 600; font-size: 15px; margin-bottom: 8px; }
.cal { width: 100%; border-collapse: collapse; font-size: 12.5px; text-align: center; font-variant-numeric: tabular-nums; }
.cal th { color: var(--text-3); font-weight: 500; padding: 4px; font-size: 11px; }
.cal td { padding: 0; height: 32px; color: var(--text); }
.cal-out { color: var(--text-3) !important; opacity: .45; }
.cal-marked { font-weight: 600; }
.cal-today, .cal-today.cal-marked { color: #fff !important; font-weight: 700; background: none; position: relative; z-index: 0; }
.cal-today::after { content: ""; position: absolute; left: 50%; top: 50%; width: 28px; height: 28px; transform: translate(-50%, -50%); border-radius: 50%; background: var(--red); z-index: -1; }
.cal-dot { color: var(--text-3); font-size: 9px; vertical-align: top; margin-left: 1px; }
.cal-today .cal-dot { color: #fff; }

/* ---------- chat ---------- */
.chat-bubble { position: fixed; bottom: max(24px, env(safe-area-inset-bottom, 0px)); right: max(24px, env(safe-area-inset-right, 0px));
  width: 52px; height: 52px; border-radius: 50%; background: var(--accent); display: grid; place-items: center; cursor: pointer;
  box-shadow: 0 6px 20px color-mix(in srgb, var(--accent) 45%, transparent); z-index: 1000; transition: transform .15s; }
.chat-bubble:hover { transform: scale(1.05); }
.chat-panel-hidden { display: none; }
#chatPanel { position: fixed; bottom: 24px; right: 24px; width: min(400px, 92vw); z-index: 1000; padding: 16px; box-shadow: var(--shadow-lg); }
.chat-panel-header { display: flex; justify-content: space-between; align-items: center; font-weight: 600; font-size: 17px; margin-bottom: 12px; }
.chat-close { cursor: pointer; color: var(--text-3); font-weight: 400; }
.chat-log { max-height: 420px; overflow-y: auto; margin-bottom: 12px; display: flex; flex-direction: column; gap: 6px; }
#chatPanel .chat-log { max-height: 360px; }
.chat-msg { padding: 8px 14px; border-radius: 18px; max-width: 86%; font-size: 14.5px; }
.chat-you { background: var(--accent); color: var(--on-accent); align-self: flex-end; }
.chat-assistant { background: var(--fill-2); color: var(--text); align-self: flex-start; }
.chat-role { font-size: 11px; opacity: .65; margin-bottom: 2px; }
.chat-you .meta { color: inherit; opacity: .75; }
.chat-body { white-space: pre-wrap; }
.chat-input-row { display: flex; gap: 8px; align-items: flex-end; }
.chat-input-row textarea { flex: 1; margin-bottom: 0; border-radius: 18px; }

/* ---------- settings ---------- */
.mdl-box { padding: 2px 20px; margin-bottom: 14px; }
.mdl-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding: 14px 0; border-bottom: 1px solid var(--separator); }
.mdl-row:last-child { border-bottom: 0; }
.mdl-tier { flex: 0 1 200px; min-width: 0; } .mdl-tier b { font-weight: 600; } .mdl-tier .meta { margin: 2px 0 0; }
.mdl-prov { flex: 0 1 230px; min-width: 0; }
.mdl-model { flex: 1 1 180px; min-width: 0; }
.mdl-key { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding: 8px 0; }
.mdl-key-name { flex: 0 0 240px; }
.mdl-keys { margin: 16px 0; } .mdl-keys summary { cursor: pointer; color: var(--accent-text); }
.acct-row { margin: 0 0 8px; padding: 14px 18px; font-size: 14.5px; }
.acct-dot { font-weight: 700; margin-right: 4px; } .acct-id { color: var(--text-2); margin: 0 6px; }
.acct-fix { color: var(--red); font-size: 13px; margin-top: 4px; }
.auth-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.32); backdrop-filter: blur(6px); z-index: 1100; display: flex; align-items: center; justify-content: center; padding: 16px; }
.auth-box { padding: 24px 26px; max-width: 460px; box-shadow: var(--shadow-lg); }
.auth-box h3 { margin: 0 0 10px; color: var(--text); font-size: 19px; font-weight: 700; }
.auth-reason { color: var(--text-2); } .auth-buttons { margin-top: 16px; display: flex; gap: 8px; } .auth-refuse { color: var(--red); }
.inbox-item { font-size: 14.5px; padding: 11px 0; border-bottom: 1px solid var(--separator); color: var(--text); }
.linked-domain { margin-top: 16px; padding: 16px 18px; background: var(--red-soft); border-radius: var(--r); border: 0; }
.linked-domain-title { font-weight: 600; font-size: 15px; color: var(--red); margin-bottom: 8px; }
.linked-domain pre { background: var(--surface); color: var(--text); box-shadow: none; }
.lite-markdown ul { margin: 4px 0 8px; padding-left: 20px; } .lite-markdown li, .lite-markdown p { font-size: 14px; margin: 4px 0; }
.archived-item { opacity: .7; padding: 14px 18px; }
.slack-preview-label, .extra-notes-label { font-size: 12.5px; color: var(--text-3); margin: 10px 0 4px; }
.slack-preview { background: var(--fill-2); border-radius: 10px; padding: 10px 12px; font-size: 14.5px; min-height: 1.5em; margin-bottom: 6px; border: 0; }
.button-link { display: inline-flex; align-items: center; height: 32px; padding: 0 16px; border-radius: 980px; background: var(--accent); color: var(--on-accent); font-size: 14px; font-weight: 500; margin: 6px 0; }
.button-link:hover { text-decoration: none; background: var(--accent-hover); }
""")
