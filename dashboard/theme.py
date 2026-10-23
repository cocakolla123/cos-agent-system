"""The dashboard's own look: "the ledger".

A chief of staff keeps a ledger of what is owed, and marks what matters in
red pen. So: warm paper and ink, a serif for titles and figures, the system
sans for everything you read quickly, hairline rules instead of boxes, and one
accent, vermilion, used only for what needs you now. A date column runs down
the task list like a ledger's. Night mode is the same desk with the lamp on:
warm charcoal, paper-white ink.

No web fonts are loaded (the local app makes no outside requests); the serif
stack picks the best one each system ships.
"""

_PAPER = """
  --bg: #f7f4ee; --rail: #f1ede5; --sheet: #fffdf9; --sheet-2: #f3efe7;
  --rule: #e6e0d4; --rule-strong: #d6cfbf; --fill: rgba(60,45,20,.06); --fill-2: rgba(60,45,20,.10);
  --ink: #1b1a17; --ink-2: #5d584f; --ink-3: #857f73;
  --pen: #d9442b; --pen-hover: #c43a22; --pen-soft: rgba(217,68,43,.09); --pen-text: #c13a22;
  --on-pen: #fffdf9;
  --amber: #9a6200; --amber-soft: rgba(196,128,0,.12);
  --sage: #3f7a4f; --sage-soft: rgba(63,122,79,.11);
  --slate: #3d5a80; --slate-soft: rgba(61,90,128,.10);
  --plum: #7a4b7a; --plum-soft: rgba(122,75,122,.10);
  --lift: 0 1px 0 rgba(60,45,20,.04), 0 8px 24px -12px rgba(60,45,20,.18);
  --lift-lg: 0 24px 64px -16px rgba(30,20,5,.35);
  color-scheme: light;
"""

_NIGHT = """
  --bg: #15130f; --rail: #1b1914; --sheet: #201d18; --sheet-2: #29261f;
  --rule: #34302a; --rule-strong: #46413a; --fill: rgba(255,245,225,.05); --fill-2: rgba(255,245,225,.09);
  --ink: #efe9de; --ink-2: #b4ac9e; --ink-3: #8f887b;
  --pen: #ff6a4d; --pen-hover: #ff7f66; --pen-soft: rgba(255,106,77,.13); --pen-text: #ff8269;
  --on-pen: #15130f;
  --amber: #e0a33a; --amber-soft: rgba(224,163,58,.14);
  --sage: #7cc191; --sage-soft: rgba(124,193,145,.13);
  --slate: #8fb0d8; --slate-soft: rgba(143,176,216,.13);
  --plum: #cf9bcf; --plum-soft: rgba(207,155,207,.13);
  --lift: 0 0 0 1px rgba(0,0,0,.2);
  --lift-lg: 0 24px 64px -12px rgba(0,0,0,.7);
  color-scheme: dark;
"""

CSS = (":root {" + _PAPER + """
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, "Helvetica Neue", system-ui, sans-serif;
  --serif: "Iowan Old Style", "Charter", "Bitstream Charter", "Sitka Text", "Palatino Linotype", Palatino, "Book Antiqua", Georgia, serif;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {""" + _NIGHT + """} }
:root[data-theme="dark"] {""" + _NIGHT + "}" + r"""
* { box-sizing: border-box; }
html { background: var(--bg); }
body { margin: 0; font-family: var(--sans); font-size: 15px; line-height: 1.5; color: var(--ink); background: var(--bg);
  -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility; }
a { color: var(--pen-text); text-decoration: none; }
a:hover { text-decoration: underline; text-underline-offset: 3px; }
::selection { background: var(--pen-soft); }
h1, h2, .topbar-title, .stat-num, .todo-detail .tm-title, .card-title, .graph-section > h3, .side-panel h3, .cal-head {
  font-family: var(--serif); }

/* ---------- shell ---------- */
.nav { position: fixed; inset: 0 auto 0 0; width: 236px; padding: 24px 14px 16px; z-index: 60;
  display: flex; flex-direction: column; gap: 1px; background: var(--rail); border-right: 1px solid var(--rule); }
.brand { display: flex; align-items: center; gap: 10px; padding: 0 10px 26px; }
.brand-mark { width: 9px; height: 9px; border-radius: 2px; background: var(--pen); transform: rotate(45deg); flex: none; }
.brand-mark svg { display: none; }
.brand > div { font-family: var(--serif); font-size: 19px; font-weight: 600; letter-spacing: -.01em; }
.nav-group { margin: 18px 10px 6px; font-size: 13px; color: var(--ink-3); font-style: italic; font-family: var(--serif); }
.nav a.nav-link { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 8px;
  padding: 6px 10px 6px 12px; border-radius: 6px; color: var(--ink-2); font-size: 14px; }
.nav a.nav-link:hover { background: var(--fill); color: var(--ink); text-decoration: none; }
.nav a.nav-link.active { color: var(--ink); font-weight: 600; background: var(--sheet); box-shadow: var(--lift); }
.nav a.nav-link.active::before { content: ""; position: absolute; left: 0; top: 8px; bottom: 8px; width: 2px; border-radius: 2px; background: var(--pen); }
.nav-count { font-size: 12.5px; color: var(--ink-3); font-variant-numeric: tabular-nums; }
.nav a.active .nav-count { color: var(--pen-text); }
.nav-foot { margin-top: auto; padding: 12px 6px 0; display: flex; flex-direction: column; align-items: flex-start; gap: 8px; border-top: 1px solid var(--rule); }
.nav-hint { font-size: 12px; color: var(--ink-3); padding: 0 4px; line-height: 1.9; }
.main { margin-left: 236px; min-height: 100vh; }
.topbar { position: sticky; top: 0; z-index: 50; display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
  padding: 18px 44px 16px; background: color-mix(in srgb, var(--bg) 95%, transparent); backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--rule); }
.topbar-title { font-size: 28px; line-height: 1.1; font-weight: 600; letter-spacing: -.015em; }
.topbar-head { display: flex; flex-direction: column; gap: 3px; min-width: 0; flex: 1 1 200px; }
.status { display: block; color: var(--ink-3); font-size: 12.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.status-dot { display: inline-block; vertical-align: 1px; margin-right: 6px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--sage); }
.topbar-actions { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.search-btn { display: inline-flex; align-items: center; gap: 10px; min-width: 190px; justify-content: space-between;
  height: 34px; padding: 0 8px 0 12px; border-radius: 8px; background: var(--sheet); color: var(--ink-3);
  border: 1px solid var(--rule); font-size: 13.5px; }
.search-btn:hover { border-color: var(--rule-strong); color: var(--ink-2); background: var(--sheet); }
kbd { font-family: var(--mono); font-size: 11px; padding: 1px 5px; border-radius: 4px; border: 1px solid var(--rule-strong);
  background: var(--sheet-2); color: var(--ink-2); line-height: 1.5; }
.content-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 36px; padding: 28px 44px 96px; max-width: 1480px; }
.content { min-width: 0; }
.view[hidden] { display: none !important; }
@media (min-width: 1440px) { .content-grid { grid-template-columns: minmax(0, 1fr) 292px; } }
@media (min-width: 1100px) { .topbar { flex-wrap: nowrap; } }
@media (max-width: 899px) {
  .nav { position: sticky; top: 0; inset: auto; width: auto; flex-direction: row; align-items: center; overflow-x: auto;
    padding: 10px 12px; border-right: 0; border-bottom: 1px solid var(--rule); gap: 2px; }
  .brand { padding: 0 8px 0 4px; } .brand > div, .nav-group, .nav-count, .nav-hint { display: none; }
  .nav a.nav-link { white-space: nowrap; }
  .nav a.nav-link.active::before { left: 10px; right: 10px; top: auto; bottom: 1px; width: auto; height: 2px; }
  .nav-foot { margin: 0 0 0 4px; padding: 0; border: 0; flex-direction: row; }
  .main { margin-left: 0; }
  .topbar { position: static; padding: 16px; gap: 10px; }
  .topbar-title { font-size: 24px; }
  .topbar-actions { margin-left: 0; flex-wrap: wrap; }
  .search-btn { min-width: 0; }
  .content-grid { padding: 18px 16px 96px; }
}

/* ---------- type ---------- */
h1 { font-size: 30px; font-weight: 600; margin: 0 0 4px; }
h2 { font-size: 23px; font-weight: 600; letter-spacing: -.01em; margin: 40px 0 14px; padding: 0; border: 0;
  display: flex; align-items: baseline; gap: 10px; justify-content: flex-start; }
.view > h2:first-child { margin-top: 4px; }
h3 { font-size: 13px; font-weight: 600; color: var(--ink-2); margin: 24px 0 8px; }
.meta, .sec-sub, .poll-status, .acct-meta, .auth-note, .cc-sub, .td-empty, .empty, .obj-next-none, .tm-thinking { color: var(--ink-3); }
.meta { font-size: 13px; margin-bottom: 10px; }
.quick-line { font-size: 15px; color: var(--ink-2); margin-bottom: 10px; }
.view-intro { color: var(--ink-2); font-size: 15px; margin: -4px 0 22px; max-width: 66ch; }
pre { white-space: pre-wrap; font-family: var(--sans); font-size: 14.5px; line-height: 1.6; color: var(--ink-2);
  background: var(--sheet); border: 1px solid var(--rule); border-radius: 10px; padding: 18px 20px; max-height: 360px; overflow-y: auto; }
code { font-family: var(--mono); font-size: .85em; background: var(--fill); padding: .1em .35em; border-radius: 4px; }

/* ---------- controls ---------- */
button { height: 32px; padding: 0 14px; border-radius: 8px; border: 1px solid var(--rule-strong); background: var(--sheet); color: var(--ink);
  font: inherit; font-size: 13.5px; font-weight: 500; cursor: pointer; white-space: nowrap; margin: 0;
  transition: background .12s, border-color .12s, transform .06s; }
button:hover { border-color: var(--ink-3); background: var(--sheet); }
button:active { transform: translateY(1px); }
button.primary { background: var(--ink); color: var(--bg); border-color: var(--ink); }
button.primary:hover { background: var(--ink-2); border-color: var(--ink-2); }
button.small { height: 28px; padding: 0 12px; font-size: 13px; }
button.ghost { background: transparent; border-color: transparent; color: var(--ink-2); padding: 0 8px; }
button.ghost:hover { background: var(--fill); border-color: transparent; }
.card button.primary, .tm-next button.primary { background: var(--pen); border-color: var(--pen); color: var(--on-pen); }
.card button.primary:hover, .tm-next button.primary:hover { background: var(--pen-hover); border-color: var(--pen-hover); }
button:focus-visible, a:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible, .todo-row:focus-visible {
  outline: 2px solid var(--pen); outline-offset: 2px; }
textarea, input[type=text], input[type=password], input[type=time], input[type=number], input:not([type]), select {
  font: inherit; font-size: 14.5px; color: var(--ink); background: var(--sheet); border: 1px solid var(--rule-strong); border-radius: 8px; padding: 8px 11px; }
textarea:focus, input:focus, select:focus { border-color: var(--ink-3); outline: 0; }
textarea { width: 100%; resize: vertical; margin-bottom: 10px; }
select { height: 32px; padding: 0 8px; }
input::placeholder, textarea::placeholder { color: var(--ink-3); }
.actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
.result { font-size: 13px; margin-top: 8px; white-space: pre-wrap; color: var(--sage); }
.pill-row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }
.day-pill { height: 28px; padding: 0 11px; font-size: 13px; }
.day-pill.on { background: var(--ink); color: var(--bg); border-color: var(--ink); }

/* ---------- sheets ---------- */
.card, .objective-card, .acct-row, .start-research-card, .chat-box, .todo-detail, .side-panel, .auth-box, .mdl-box {
  background: var(--sheet); border: 1px solid var(--rule); border-radius: 12px; }
.card { padding: 20px 22px; margin-bottom: 14px; }
.card.stale, .card.approved, .card.rejected, .card.superseded { opacity: .6; }
.card.failed { border-color: var(--amber); }
.card.drafted { border-color: var(--slate); }
.card-title { font-size: 19px; font-weight: 600; line-height: 1.3; margin: 10px 0 4px; }
.badge, .priority-tag, .tag-pill, .todo-draft, .ws-chip, .sec-count {
  display: inline-flex; align-items: center; height: 21px; padding: 0 8px; border-radius: 4px; border: 0;
  font-size: 12px; font-weight: 500; text-transform: none; letter-spacing: 0; white-space: nowrap;
  background: var(--fill); color: var(--ink-2); margin: 0 4px 0 0; }
.badge.pending { background: var(--amber-soft); color: var(--amber); }
.badge.approved { background: var(--sage-soft); color: var(--sage); }
.badge.rejected, .badge.stale, .badge.superseded { background: var(--pen-soft); color: var(--pen-text); }
.badge.failed { background: var(--amber-soft); color: var(--amber); }
.badge.drafted { background: var(--slate-soft); color: var(--slate); }
.priority-high { background: var(--pen-soft); color: var(--pen-text); }
.priority-medium { background: var(--amber-soft); color: var(--amber); }
.priority-low { background: var(--fill); color: var(--ink-3); }
.tag-ticket, .tag-meeting { background: var(--slate-soft); color: var(--slate); }
.tag-message { background: var(--plum-soft); color: var(--plum); }
.tag-calendar { background: var(--sage-soft); color: var(--sage); }
.tag-domain { background: var(--pen-soft); color: var(--pen-text); }
.sec-count { background: transparent; color: var(--ink-3); padding: 0; font-family: var(--sans); font-size: 14px; font-weight: 400; }
.priority-note { font-style: italic; color: var(--ink-2); }
.tabs { display: inline-flex; gap: 18px; margin: 14px 0 12px; border-bottom: 1px solid var(--rule); }
.tab-btn { height: 30px; padding: 0; border: 0; border-radius: 0; background: transparent; color: var(--ink-3); font-size: 13.5px; margin-bottom: -1px; }
.tab-btn:hover { color: var(--ink); background: transparent; }
.tab-btn.active { color: var(--ink); box-shadow: inset 0 -2px 0 var(--pen); font-weight: 600; }
.tab-panel { display: none; } .tab-panel.active { display: block; }
.demo-banner { background: transparent; color: var(--ink-2); border: 1px dashed var(--rule-strong); border-radius: 10px;
  padding: 12px 16px; margin: 0 0 24px; font-size: 13.5px; }
.demo-banner b { color: var(--ink); }
.guardrail-alert { margin: 0 0 18px; padding: 14px 18px; background: var(--pen-soft); border: 1px solid var(--pen); border-radius: 10px; font-size: 14px; }
.coverage-note { margin: 0 0 18px; padding: 12px 16px; background: var(--amber-soft); border-radius: 10px; font-size: 14px; color: var(--ink); border: 0; }
.start-research-card { padding: 20px 22px; margin: 0 0 18px; }
.start-research-card h2 { margin: 0 0 6px; }

/* ---------- masthead figures ---------- */
.stats { display: flex; flex-wrap: wrap; margin: 0 0 6px; border-top: 2px solid var(--ink); border-bottom: 1px solid var(--rule); }
.stat { flex: 1 1 150px; padding: 16px 20px 16px 0; }
.stat + .stat { padding-left: 20px; border-left: 1px solid var(--rule); }
.stat-num { font-size: 42px; font-weight: 500; line-height: 1; letter-spacing: -.02em; font-variant-numeric: lining-nums tabular-nums; }
.stat-label { color: var(--ink-2); font-size: 13px; margin-top: 6px; }
.stat-danger .stat-num { color: var(--pen-text); }
@media (max-width: 699px) { .stat { flex-basis: 40%; } .stat:nth-child(3) { border-left: 0; padding-left: 0; } }
.briefing { margin: 0 0 30px; }
.briefing summary { cursor: pointer; color: var(--ink-3); font-size: 13.5px; list-style: none; padding: 8px 0; }
.briefing summary::-webkit-details-marker { display: none; }
.briefing summary::before { content: "+ "; color: var(--pen-text); }
.briefing[open] summary::before { content: "\2212 "; }
.briefing pre { margin-top: 4px; }

/* ---------- the ledger ---------- */
.graph-command-center { margin: 0 0 26px; padding: 0; background: transparent; border: 0; }
.graph-command-center > h2 { display: none; }
.ws-switcher { display: inline-flex; flex-wrap: wrap; gap: 4px; margin: 0 0 20px; }
.ws-switcher a { display: inline-flex; align-items: center; height: 28px; padding: 0 11px; border-radius: 999px; color: var(--ink-2); font-size: 13px; }
.ws-switcher a:hover { background: var(--fill); text-decoration: none; color: var(--ink); }
.ws-switcher a.ws-active { background: var(--ink); color: var(--bg); }
.topbar .ws-switcher { margin: 0; }
.graph-section { margin: 0 0 30px; }
.graph-section > h3 { font-size: 23px; font-weight: 600; letter-spacing: -.01em; color: var(--ink); margin: 0 0 2px; display: flex; align-items: baseline; gap: 10px; }
.graph-section > .quick-line { font-size: 13.5px; color: var(--ink-3); margin: 0 0 16px; }
.graph-section ul { margin: 0; padding: 0; list-style: none; border-top: 1px solid var(--rule); }
.graph-section li { margin: 0; padding: 11px 2px; font-size: 14.5px; color: var(--ink); border-bottom: 1px solid var(--rule); }
.graph-section a { color: inherit; }
.sec-type { color: var(--ink-3); font-size: 12.5px; font-style: italic; font-family: var(--serif); margin-right: 6px; }
.todo-board { display: grid; grid-template-columns: minmax(300px, 400px) minmax(0, 1fr); gap: 28px; align-items: start; }
@media (max-width: 1099px) { .todo-board { grid-template-columns: minmax(0, 1fr); } }
.todo-list { max-height: 76vh; overflow-y: auto; border-top: 1px solid var(--rule); scrollbar-width: thin; }
.todo-row { display: grid; grid-template-columns: 54px minmax(0, 1fr); gap: 14px; align-items: baseline; position: relative;
  padding: 12px 10px 12px 0; border-bottom: 1px solid var(--rule); cursor: pointer; color: var(--ink); background: transparent;
  border-radius: 0; margin: 0; transition: background .1s; outline: 0; }
.todo-row:hover { background: var(--fill); }
.todo-row::before { content: ""; position: absolute; left: 0; top: -1px; bottom: -1px; width: 2px; background: transparent; }
.todo-selected { background: var(--sheet) !important; }
.todo-selected::before { background: var(--ink); }
.todo-when { font-family: var(--serif); font-size: 14px; color: var(--ink-3); text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.todo-overdue .todo-when { color: var(--pen-text); font-weight: 600; }
.todo-high .todo-title { font-weight: 600; }
.todo-main { min-width: 0; }
.todo-title { display: block; font-size: 14.5px; line-height: 1.4; }
.todo-sub { display: flex; flex-wrap: wrap; gap: 4px 12px; margin-top: 3px; font-size: 12.5px; }
.todo-sub:empty { display: none; }
.todo-sub .sec-sub, .todo-late, .todo-quiet { color: var(--ink-3); font-size: 12.5px; }
.todo-late { color: var(--pen-text); }
.todo-draft { height: auto; padding: 0; background: transparent; color: var(--ink-2); font-size: 12.5px; margin: 0; display: inline-flex; align-items: center; gap: 6px; }
.todo-draft::before { content: ""; width: 12px; height: 2px; background: var(--pen); border-radius: 2px; }
.todo-badge { display: none; }
.todo-row[hidden], .todo-divider[hidden], .todo-none[hidden] { display: none !important; }
.todo-none { padding: 28px 0; color: var(--ink-3); font-style: italic; font-family: var(--serif); text-align: center; }
.todo-pri { font-size: 12px; color: var(--ink-3); }
.todo-pri.pri-high { color: var(--pen-text); font-weight: 600; }
.todo-pri.pri-low { color: var(--ink-3); opacity: .8; }
.todo-filters { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin: 0 0 14px; }
.tf-chip { height: 30px; padding: 0 12px; border-radius: 999px; background: transparent; border: 1px solid var(--rule-strong); color: var(--ink-2); font-size: 13px; }
.tf-chip:hover { border-color: var(--ink-3); color: var(--ink); background: transparent; }
.tf-chip.tf-on { background: var(--ink); color: var(--bg); border-color: var(--ink); }
.tf-n { margin-left: 4px; font-variant-numeric: tabular-nums; opacity: .65; }
.tf-search { margin-left: auto; height: 30px; width: 200px; max-width: 100%; padding: 0 12px; font-size: 13px; border-radius: 999px; }
@media (max-width: 699px) { .tf-search { margin-left: 0; width: 100%; } }
.todo-divider { padding: 28px 0 10px 68px; font-family: var(--serif); font-style: italic; font-size: 14px; color: var(--ink-3); border-bottom: 1px solid var(--rule); }
.todo-stale { opacity: .6; } .todo-stale:hover, .todo-stale.todo-selected { opacity: 1; }
.todo-detail { position: sticky; top: 96px; padding: 28px 30px 26px; min-height: 340px; box-shadow: var(--lift); }
.todo-detail .tm-title { width: 100%; font-size: 27px; font-weight: 600; line-height: 1.2; letter-spacing: -.01em; color: var(--ink);
  background: transparent; border: 0; border-radius: 6px; padding: 2px 6px; margin: 0 0 0 -6px; resize: none; overflow: hidden; display: block; field-sizing: content; }
.todo-detail .tm-title:hover, .todo-detail .tm-title:focus { background: var(--fill); }
.tm-meta { margin: 8px 0 20px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; font-size: 13.5px; color: var(--ink-2); }
.tm-controls { display: flex; gap: 8px; align-items: center; margin: 0 0 22px; flex-wrap: wrap; }
.tm-next { border-top: 2px solid var(--ink); padding: 14px 0 0; margin: 0 0 20px; }
.tm-next-head { font-family: var(--serif); font-style: italic; font-size: 15px; color: var(--ink-2); margin: 0 0 6px; }
.tm-next .card { margin: 0; padding: 0; background: transparent; border: 0; }
.tm-plan { white-space: pre-wrap; font-size: 15px; line-height: 1.6; color: var(--ink); }
.draft-text { background: var(--bg); border-left: 2px solid var(--pen); border-radius: 0 8px 8px 0; padding: 14px 18px; margin: 12px 0 6px;
  font-family: var(--serif); font-size: 16px; line-height: 1.6; }
#tmNote { width: 100%; }
.tm-evidence { margin: 2px 0 12px; font-size: 12.5px; }
.tm-chat { border-top: 1px solid var(--rule); margin-top: 18px; padding-top: 16px; }
.tm-chat-log { max-height: 240px; overflow-y: auto; font-size: 14px; display: flex; flex-direction: column; gap: 8px; }
.tm-msg { background: var(--sheet-2); border-radius: 10px; padding: 8px 12px; margin: 0; white-space: pre-wrap; align-self: flex-start; max-width: 90%; }
.tm-you { background: var(--ink); color: var(--bg); align-self: flex-end; }
.objective-card { margin: 0 0 10px; padding: 16px 18px; }
.obj-title { font-weight: 600; font-size: 15px; }
.obj-timeline, .obj-next { font-size: 14px; color: var(--ink-2); margin-top: 4px; }
.obj-details summary { font-size: 13px; color: var(--ink-3); cursor: pointer; margin-top: 6px; }

/* ---------- margin column ---------- */
.side-panel { display: none; }
@media (min-width: 1440px) {
  .side-panel { display: block; position: sticky; top: 96px; align-self: start; padding: 4px 0 20px 24px; background: transparent;
    border: 0; border-left: 1px solid var(--rule); border-radius: 0; max-height: calc(100vh - 120px); overflow-y: auto; }
  .side-panel h3 { margin: 0 0 12px; color: var(--ink); font-size: 19px; font-weight: 600; }
}
.today-brief { margin: 0 0 18px; padding: 0; background: transparent; border: 0; font-size: 14px; color: var(--ink-2); }
.tb-line { margin: 0 0 12px; } .tb-line strong { color: var(--ink); font-weight: 600; }
.tb-overdue strong { color: var(--pen-text); } .today-brief a { color: var(--ink); text-decoration: underline; text-decoration-color: var(--rule-strong); text-underline-offset: 3px; }
.cal-box { margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--rule); }
.cal-head { font-weight: 600; font-size: 16px; margin-bottom: 8px; }
.cal { width: 100%; border-collapse: collapse; font-size: 12.5px; text-align: center; font-variant-numeric: tabular-nums; }
.cal th { color: var(--ink-3); font-weight: 400; padding: 4px; font-size: 11px; }
.cal td { padding: 0; height: 30px; color: var(--ink-2); position: relative; }
.cal-out { color: var(--ink-3) !important; opacity: .4; }
.cal-marked { color: var(--ink); font-weight: 600; }
.cal-today, .cal-today.cal-marked { color: var(--on-pen) !important; font-weight: 700; background: none; z-index: 0; }
.cal-today::after { content: ""; position: absolute; left: 50%; top: 50%; width: 26px; height: 26px; transform: translate(-50%, -50%); border-radius: 50%; background: var(--pen); z-index: -1; }
.cal-dot { color: var(--pen); font-size: 9px; vertical-align: top; }
.cal-today .cal-dot { color: var(--on-pen); }

/* ---------- command palette ---------- */
.palette { position: fixed; inset: 0; z-index: 1200; display: flex; align-items: flex-start; justify-content: center;
  padding: 12vh 16px 16px; background: rgba(20,15,5,.28); backdrop-filter: blur(3px); }
.palette[hidden] { display: none; }
.palette-box { width: min(620px, 100%); background: var(--sheet); border: 1px solid var(--rule); border-radius: 14px; box-shadow: var(--lift-lg); overflow: hidden; }
.palette-input { width: 100%; height: 56px; border: 0 !important; border-bottom: 1px solid var(--rule) !important; border-radius: 0 !important; background: transparent !important;
  padding: 0 20px !important; font-size: 18px !important; font-family: var(--serif) !important; }
.palette-list { max-height: 52vh; overflow-y: auto; padding: 6px; }
.palette-group { padding: 10px 14px 4px; font-family: var(--serif); font-style: italic; font-size: 13px; color: var(--ink-3); }
.palette-item { display: flex; align-items: baseline; gap: 12px; padding: 9px 14px; border-radius: 8px; cursor: pointer; font-size: 14.5px; }
.palette-item .pi-when { width: 52px; flex: none; text-align: right; font-family: var(--serif); color: var(--ink-3); font-size: 13.5px; }
.palette-item .pi-text { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.palette-item .pi-hint { color: var(--ink-3); font-size: 12px; }
.palette-item.active { background: var(--fill-2); }
.palette-item.active .pi-when { color: var(--pen-text); }
.palette-empty { padding: 18px; color: var(--ink-3); font-size: 14px; }
.palette-foot { display: flex; flex-wrap: wrap; gap: 16px; padding: 10px 16px; border-top: 1px solid var(--rule); font-size: 12px; color: var(--ink-3); }

/* ---------- chat ---------- */
.chat-bubble { position: fixed; bottom: max(24px, env(safe-area-inset-bottom, 0px)); right: max(24px, env(safe-area-inset-right, 0px));
  width: 50px; height: 50px; border-radius: 50%; background: var(--ink); display: grid; place-items: center; cursor: pointer;
  box-shadow: var(--lift-lg); z-index: 1000; transition: transform .15s; }
.chat-bubble path { fill: var(--bg); }
.chat-bubble:hover { transform: translateY(-2px); }
.chat-panel-hidden { display: none; }
#chatPanel { position: fixed; bottom: 24px; right: 24px; width: min(410px, 92vw); z-index: 1000; padding: 18px; box-shadow: var(--lift-lg); }
.chat-panel-header { display: flex; justify-content: space-between; align-items: center; font-family: var(--serif); font-weight: 600; font-size: 19px; margin-bottom: 12px; }
.chat-close { cursor: pointer; color: var(--ink-3); font-family: var(--sans); font-weight: 400; font-size: 15px; }
.chat-log { max-height: 420px; overflow-y: auto; margin-bottom: 12px; display: flex; flex-direction: column; gap: 8px; }
#chatPanel .chat-log { max-height: 360px; }
.chat-msg { padding: 9px 13px; border-radius: 12px; max-width: 88%; font-size: 14.5px; }
.chat-you { background: var(--ink); color: var(--bg); align-self: flex-end; }
.chat-assistant { background: var(--sheet-2); color: var(--ink); align-self: flex-start; }
.chat-role { font-size: 11px; opacity: .65; margin-bottom: 2px; }
.chat-you .meta { color: inherit; opacity: .75; }
.chat-body { white-space: pre-wrap; }
.chat-input-row { display: flex; gap: 8px; align-items: flex-end; }
.chat-input-row textarea { flex: 1; margin-bottom: 0; }

/* ---------- settings ---------- */
.mdl-box { padding: 2px 22px; margin-bottom: 16px; }
.mdl-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding: 16px 0; border-bottom: 1px solid var(--rule); }
.mdl-row:last-child { border-bottom: 0; }
.mdl-tier { flex: 0 1 200px; min-width: 0; } .mdl-tier b { font-family: var(--serif); font-size: 17px; font-weight: 600; } .mdl-tier .meta { margin: 2px 0 0; }
.mdl-prov { flex: 0 1 240px; min-width: 0; }
.mdl-model { flex: 1 1 170px; min-width: 0; }
.mdl-effort { flex: 0 0 auto; }
.usage-table { width: 100%; border-collapse: collapse; font-size: 14px; margin: 4px 0 10px; }
.usage-table th { text-align: left; font-weight: 500; color: var(--ink-3); font-size: 12.5px; padding: 6px 4px; border-bottom: 1px solid var(--rule-strong); }
.usage-table td { padding: 9px 4px; border-bottom: 1px solid var(--rule); }
.usage-table .num { text-align: right; font-variant-numeric: tabular-nums; }
.mdl-key { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding: 8px 0; }
.mdl-key-name { flex: 0 0 240px; }
.mdl-keys { margin: 16px 0; } .mdl-keys summary { cursor: pointer; color: var(--ink-2); }
.acct-row { margin: 0 0 8px; padding: 14px 18px; font-size: 14.5px; }
.acct-dot { font-weight: 700; margin-right: 4px; } .acct-id { color: var(--ink-2); margin: 0 6px; }
.acct-fix { color: var(--pen-text); font-size: 13px; margin-top: 4px; }
.auth-overlay { position: fixed; inset: 0; background: rgba(20,15,5,.3); backdrop-filter: blur(3px); z-index: 1100; display: flex; align-items: center; justify-content: center; padding: 16px; }
.auth-box { padding: 24px 26px; max-width: 460px; box-shadow: var(--lift-lg); }
.auth-box h3 { margin: 0 0 10px; color: var(--ink); font-family: var(--serif); font-size: 21px; font-weight: 600; }
.auth-reason { color: var(--ink-2); } .auth-buttons { margin-top: 16px; display: flex; gap: 8px; } .auth-refuse { color: var(--pen-text); }
.inbox-item { font-size: 14.5px; padding: 11px 0; border-bottom: 1px solid var(--rule); color: var(--ink); }
.linked-domain { margin-top: 16px; padding: 16px 18px; background: var(--pen-soft); border-radius: 10px; border: 0; }
.linked-domain-title { font-weight: 600; font-size: 15px; color: var(--pen-text); margin-bottom: 8px; }
.linked-domain pre { background: var(--sheet); color: var(--ink); }
.lite-markdown ul { margin: 4px 0 8px; padding-left: 20px; } .lite-markdown li, .lite-markdown p { font-size: 14px; margin: 4px 0; }
.archived-item { opacity: .7; padding: 14px 18px; }
.slack-preview-label, .extra-notes-label { font-size: 12.5px; color: var(--ink-3); margin: 10px 0 4px; }
.slack-preview { background: var(--bg); border: 1px solid var(--rule); border-radius: 8px; padding: 10px 12px; font-size: 14.5px; min-height: 1.5em; margin-bottom: 6px; }
.button-link { display: inline-flex; align-items: center; height: 32px; padding: 0 14px; border-radius: 8px; background: var(--ink); color: var(--bg); font-size: 13.5px; font-weight: 500; margin: 6px 0; }
.button-link:hover { text-decoration: none; background: var(--ink-2); }
""")
