"""The dashboard's look: one token set, dark first, light via [data-theme=light].

Kept out of server.py so the page template stays readable and the theme can be
edited on its own. No web fonts are loaded (the local app makes no outside
requests); Inter and JetBrains Mono are used when installed.
"""

CSS = r"""
/* ---- tokens: dark first, light via [data-theme=light] ---- */
:root {
  --bg: #0a0b0d; --bg-elev: #0f1114; --surface: #14161a; --surface-2: #1a1d22; --surface-3: #22262c;
  --border: #23272e; --border-strong: #333841;
  --text: #eceef1; --text-2: #a6abb5; --text-3: #7d838e;
  --accent: #d4ff3a; --accent-ink: #0a0b0d; --accent-text: #d4ff3a; --accent-soft: rgba(212,255,58,.12);
  --danger: #ff6369; --danger-soft: rgba(255,99,105,.13);
  --warn: #ffb224; --warn-soft: rgba(255,178,36,.13);
  --ok: #3dd68c; --ok-soft: rgba(61,214,140,.13);
  --info: #8fb0ff; --info-soft: rgba(143,176,255,.13);
  --violet: #b9a5ff; --violet-soft: rgba(185,165,255,.13);
  --shadow: 0 10px 40px rgba(0,0,0,.45);
  --radius: 12px; --radius-sm: 8px;
  --font: Inter, "SF Pro Text", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  --mono: "JetBrains Mono", "SF Mono", ui-monospace, Menlo, Consolas, monospace;
  color-scheme: dark;
}
:root[data-theme="light"] {
  --bg: #f5f6f8; --bg-elev: #ffffff; --surface: #ffffff; --surface-2: #f2f3f6; --surface-3: #e8eaee;
  --border: #e3e5ea; --border-strong: #cfd3da;
  --text: #0b0c0e; --text-2: #474d58; --text-3: #626873;
  --accent: #d4ff3a; --accent-ink: #0a0b0d; --accent-text: #3f6212; --accent-soft: rgba(132,170,0,.14);
  --danger: #c8232f; --danger-soft: rgba(200,35,47,.09);
  --warn: #a25b00; --warn-soft: rgba(255,178,36,.18);
  --ok: #0e7a4a; --ok-soft: rgba(14,122,74,.10);
  --info: #2851c6; --info-soft: rgba(40,81,198,.09);
  --violet: #5b3cc4; --violet-soft: rgba(91,60,196,.09);
  --shadow: 0 10px 30px rgba(15,20,30,.12);
  color-scheme: light;
}
* { box-sizing: border-box; }
html { background: var(--bg); }
body {
  margin: 0; font-family: var(--font); font-size: 14.5px; line-height: 1.55;
  color: var(--text); background: var(--bg);
  -webkit-font-smoothing: antialiased; font-feature-settings: "cv11", "ss01";
}
a { color: var(--accent-text); }
::selection { background: var(--accent); color: var(--accent-ink); }

/* ---- app shell ---- */
.nav {
  position: fixed; inset: 0 auto 0 0; width: 232px; padding: 18px 12px;
  background: var(--bg-elev); border-right: 1px solid var(--border);
  display: flex; flex-direction: column; gap: 2px; z-index: 60;
}
.brand { display: flex; align-items: center; gap: 10px; padding: 4px 10px 18px; font-weight: 750; letter-spacing: -.02em; font-size: 15px; }
.brand-mark { width: 26px; height: 26px; border-radius: 7px; background: var(--accent); color: var(--accent-ink);
  display: grid; place-items: center; font-weight: 900; font-size: 14px; font-family: var(--mono); }
.brand small { display: block; color: var(--text-3); font-weight: 500; font-size: 11px; letter-spacing: .02em; }
.nav-group { margin: 14px 10px 6px; font-size: 10.5px; font-weight: 650; letter-spacing: .09em; text-transform: uppercase; color: var(--text-3); }
.nav a.nav-link {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  padding: 7px 10px; border-radius: var(--radius-sm); color: var(--text-2); text-decoration: none; font-weight: 520;
}
.nav a.nav-link:hover { background: var(--surface-2); color: var(--text); }
.nav a.nav-link.active { background: var(--surface-3); color: var(--text); box-shadow: inset 2px 0 0 var(--accent); }
.nav-count { font-family: var(--mono); font-size: 11px; color: var(--text-3); }
.nav a.active .nav-count { color: var(--accent-text); }
.nav-foot { margin-top: auto; padding: 10px; display: flex; gap: 6px; align-items: center; color: var(--text-3); font-size: 11.5px; }
.main { margin-left: 232px; min-height: 100vh; }
.topbar {
  position: sticky; top: 0; z-index: 50; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  padding: 14px max(28px, env(safe-area-inset-right, 0px)) 14px 28px;
  background: color-mix(in srgb, var(--bg) 82%, transparent); backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
}
.topbar-title { font-weight: 700; font-size: 15px; letter-spacing: -.01em; }
.status { display: inline-flex; align-items: center; gap: 7px; color: var(--text-3); font-size: 12.5px; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--ok); box-shadow: 0 0 0 3px var(--ok-soft); }
.topbar-actions { margin-left: auto; display: flex; gap: 8px; }
.content-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 24px; padding: 24px 28px 80px; max-width: 1480px; }
.content { min-width: 0; }
.view[hidden] { display: none !important; }
@media (min-width: 1400px) { .content-grid { grid-template-columns: minmax(0, 1fr) 300px; } }
@media (max-width: 899px) {
  .nav { position: sticky; top: 0; width: auto; inset: auto; flex-direction: row; align-items: center; overflow-x: auto;
         padding: 10px 12px; border-right: 0; border-bottom: 1px solid var(--border); gap: 4px; }
  .brand { padding: 0 6px 0 0; } .brand > div, .nav-group { display: none; }
  .nav-foot { display: flex; margin: 0; padding: 0; }
  .status { flex-basis: 100%; order: 3; font-size: 12px; }
  .demo-banner { font-size: 12.5px; }
  .nav a.nav-link { white-space: nowrap; padding: 6px 10px; }
  .nav-count { display: none; }
  .main { margin-left: 0; }
  .topbar { position: static; padding: 12px 16px; }
  .content-grid { padding: 16px 16px 90px; }
}

/* ---- type ---- */
h1 { font-size: 26px; letter-spacing: -.03em; margin: 0 0 4px; }
h2 { font-size: 17px; font-weight: 700; letter-spacing: -.015em; margin: 32px 0 12px; padding: 0;
     display: flex; align-items: center; justify-content: space-between; gap: 10px; border: 0; }
.view > h2:first-child, .view > *:first-child h2:first-child { margin-top: 4px; }
h3 { font-size: 13px; font-weight: 650; letter-spacing: .01em; color: var(--text-2); margin: 18px 0 8px; }
.meta, .sec-sub, .poll-status, .acct-meta, .auth-note, .cc-sub, .td-empty, .empty, .obj-next-none, .tm-thinking { color: var(--text-3); }
.meta { font-size: 12.5px; margin-bottom: 10px; }
.quick-line { font-size: 13.5px; color: var(--text-2); margin-bottom: 10px; }
code, pre, .tl-step { font-family: var(--mono); }
pre { white-space: pre-wrap; background: var(--surface); border: 1px solid var(--border); color: var(--text-2);
      padding: 14px 16px; border-radius: var(--radius); font-size: 12.5px; line-height: 1.6; max-height: 340px; overflow-y: auto; }
code { font-size: .9em; background: var(--surface-2); padding: .05em .35em; border-radius: 5px; }

/* ---- controls ---- */
button {
  height: 34px; padding: 0 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-strong);
  background: var(--surface-2); color: var(--text); cursor: pointer; font: inherit; font-size: 13px; font-weight: 500;
  margin-right: 0; white-space: nowrap; transition: background .12s, border-color .12s, transform .06s;
}
button:hover { background: var(--surface-3); border-color: var(--text-3); }
button:active { transform: translateY(1px); }
button:focus-visible, a:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible {
  outline: 2px solid var(--accent); outline-offset: 2px; }
button.primary { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); font-weight: 700; }
button.primary:hover { filter: brightness(1.06); background: var(--accent); }
button.small { height: 30px; padding: 0 11px; font-size: 12.5px; }
button.ghost { background: transparent; border-color: transparent; color: var(--text-2); }
textarea, input[type=text], input[type=password], input[type=time], input[type=number], input:not([type]), select {
  font: inherit; font-size: 13.5px; color: var(--text); background: var(--bg-elev);
  border: 1px solid var(--border-strong); border-radius: var(--radius-sm); padding: 8px 10px;
}
textarea { width: 100%; resize: vertical; margin-bottom: 8px; }
select { height: 34px; padding: 0 8px; }
input::placeholder, textarea::placeholder { color: var(--text-3); }
.actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
.result { font-size: 12.5px; margin-top: 8px; white-space: pre-wrap; color: var(--ok); }
.pill-row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
.day-pill { height: 28px; padding: 0 10px; font-size: 12px; border-radius: 999px; background: var(--surface-2); }
.day-pill.on { background: var(--accent-soft); color: var(--accent-text); border-color: var(--accent-text); }

/* ---- surfaces ---- */
.card, .objective-card, .acct-row, .start-research-card, .chat-box, .todo-detail, .side-panel, .auth-box {
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); }
.card { padding: 18px 20px; margin-bottom: 12px; }
.card.stale, .card.approved, .card.rejected, .card.superseded { opacity: .55; }
.card.failed { border-color: var(--warn); }
.card.drafted { border-color: var(--info); }
.card-title { font-size: 15.5px; font-weight: 680; letter-spacing: -.01em; margin: 6px 0 6px; }
.badge, .priority-tag, .tag-pill, .todo-draft, .ws-chip, .sec-count {
  display: inline-flex; align-items: center; gap: 5px; height: 22px; padding: 0 8px; border-radius: 6px;
  font-size: 11.5px; font-weight: 650; letter-spacing: .01em; background: var(--surface-3); color: var(--text-2);
  margin: 0 4px 0 0; white-space: nowrap; border: 0; }
.badge { text-transform: uppercase; letter-spacing: .06em; font-size: 10.5px; font-family: var(--mono); }
.badge.pending { background: var(--warn-soft); color: var(--warn); }
.badge.approved { background: var(--ok-soft); color: var(--ok); }
.badge.rejected, .badge.stale, .badge.superseded { background: var(--danger-soft); color: var(--danger); }
.badge.failed { background: var(--warn-soft); color: var(--warn); }
.badge.drafted { background: var(--info-soft); color: var(--info); }
.priority-high { background: var(--danger-soft); color: var(--danger); }
.priority-medium { background: var(--warn-soft); color: var(--warn); }
.priority-low { background: var(--surface-3); color: var(--text-3); }
.tag-ticket, .tag-meeting { background: var(--info-soft); color: var(--info); }
.tag-message { background: var(--violet-soft); color: var(--violet); }
.tag-calendar { background: var(--ok-soft); color: var(--ok); }
.tag-domain { background: var(--danger-soft); color: var(--danger); }
.ws-chip { background: var(--surface-3); color: var(--text-2); font-family: var(--mono); font-size: 11px; }
.sec-count { height: 20px; padding: 0 6px; font-family: var(--mono); background: var(--surface-3); color: var(--text-2); margin-left: 6px; }
.todo-draft { background: var(--accent-soft); color: var(--accent-text); height: 20px; font-size: 11px; margin: 4px 0 0; }
.tabs { display: flex; gap: 4px; margin: 10px 0; padding: 3px; background: var(--surface-2); border-radius: 9px; width: fit-content; }
.tab-btn { height: 26px; padding: 0 12px; border: 0; background: transparent; color: var(--text-3); font-size: 12px; border-radius: 6px; }
.tab-btn.active { background: var(--surface); color: var(--text); box-shadow: 0 1px 2px rgba(0,0,0,.25); }
.tab-panel { display: none; } .tab-panel.active { display: block; }
.priority-note { font-style: italic; }
.demo-banner { display: block; background: var(--accent-soft); border: 1px solid color-mix(in srgb, var(--accent-text) 35%, transparent);
  color: var(--text-2); border-radius: var(--radius); padding: 10px 14px; margin: 0 0 18px; font-size: 13px; }
.demo-banner b { color: var(--accent-text); }
.guardrail-alert { margin: 0 0 16px; padding: 12px 16px; background: var(--danger-soft); border: 1px solid var(--danger); border-radius: var(--radius); font-size: 13.5px; }
.coverage-note { margin: 0 0 16px; padding: 10px 14px; background: var(--warn-soft); border: 1px solid color-mix(in srgb, var(--warn) 45%, transparent); border-radius: var(--radius); font-size: 13px; color: var(--text-2); }
.start-research-card { padding: 16px 20px; margin: 0 0 16px; border-color: var(--accent-text); }
.start-research-card h2 { margin: 0 0 6px; }

/* ---- stat strip ---- */
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 0 0 18px; }
.stat { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 16px; text-decoration: none; color: inherit; }
.stat:hover { border-color: var(--border-strong); }
.stat-num { font-family: var(--mono); font-size: 28px; font-weight: 700; letter-spacing: -.04em; line-height: 1.1; }
.stat-label { color: var(--text-3); font-size: 12px; font-weight: 560; margin-top: 4px; }
.stat-danger .stat-num { color: var(--danger); } .stat-accent .stat-num { color: var(--accent-text); }
.briefing { margin: -6px 0 18px; }
.briefing summary { cursor: pointer; color: var(--text-3); font-size: 12.5px; }
.briefing pre { margin-top: 8px; }

/* ---- command center + board ---- */
.graph-command-center { margin: 0 0 20px; padding: 0; background: transparent; border: 0; }
.graph-command-center > h2 { display: none; }
.ws-switcher { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin: 0 0 16px; }
.ws-switcher a { display: inline-flex; align-items: center; height: 28px; padding: 0 11px; border-radius: 999px; text-decoration: none;
  color: var(--text-2); border: 1px solid var(--border); margin: 0; }
.ws-switcher a:hover { border-color: var(--border-strong); color: var(--text); }
.ws-switcher a.ws-active { background: var(--text); color: var(--bg); border-color: var(--text); font-weight: 650; text-decoration: none; }
.graph-section { margin: 0 0 20px; }
.graph-section h3 { margin: 0 0 10px; font-size: 13px; color: var(--text); display: flex; align-items: center; }
.graph-section ul { margin: 0; padding-left: 18px; }
.graph-section li { margin: 4px 0; font-size: 13.5px; color: var(--text-2); }
.graph-section a { color: inherit; text-decoration: underline; text-decoration-color: var(--border-strong); text-underline-offset: 3px; }
.sec-type { color: var(--text-3); font-size: 10.5px; text-transform: uppercase; letter-spacing: .07em; font-family: var(--mono); }
.todo-board { display: grid; grid-template-columns: minmax(280px, 360px) minmax(0, 1fr); gap: 14px; align-items: start; }
@media (max-width: 1099px) { .todo-board { grid-template-columns: minmax(0, 1fr); } }
.todo-list { max-height: 72vh; overflow-y: auto; padding-right: 4px; display: flex; flex-direction: column; gap: 6px; }
.todo-row { position: relative; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px 10px 16px;
  cursor: pointer; font-size: 13.5px; line-height: 1.45; color: var(--text); margin: 0; transition: border-color .12s, background .12s; }
.todo-row::before { content: ""; position: absolute; left: 0; top: 10px; bottom: 10px; width: 3px; border-radius: 0 3px 3px 0; background: var(--border-strong); }
.todo-row:hover { border-color: var(--border-strong); background: var(--surface-2); }
.todo-high::before { background: var(--danger); } .todo-medium::before { background: var(--warn); } .todo-low::before { background: var(--text-3); }
.todo-high, .todo-medium, .todo-low { border-left-width: 1px; }
.todo-selected { border-color: var(--accent-text); background: var(--surface-2); box-shadow: 0 0 0 1px var(--accent-text) inset; }
.todo-badge { display: none; }
.todo-late { color: var(--danger); font-weight: 650; font-size: 12px; font-family: var(--mono); }
.todo-row .sec-sub { font-size: 12px; font-family: var(--mono); }
.todo-divider { margin: 10px 0 2px; padding-top: 10px; border-top: 1px dashed var(--border-strong); font-size: 12px; color: var(--text-3); }
.todo-stale { opacity: .6; } .todo-stale:hover { opacity: 1; }
.todo-quiet { color: var(--text-3); font-size: 12px; font-family: var(--mono); }
.todo-detail { position: sticky; top: 76px; padding: 20px 22px; min-height: 320px; }
.todo-detail .tm-title { width: 100%; font-size: 19px; font-weight: 720; letter-spacing: -.02em; border: 1px solid transparent; background: transparent; color: var(--text); padding: 4px 6px; margin-left: -6px; }
.todo-detail .tm-title:hover, .todo-detail .tm-title:focus { border-color: var(--border-strong); background: var(--bg-elev); }
.tm-meta { margin: 6px 0 12px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; font-size: 12.5px; }
.tm-controls { display: flex; gap: 8px; align-items: center; margin: 0 0 14px; flex-wrap: wrap; }
.tm-next { border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 16px; margin: 0 0 14px; background: var(--bg-elev); }
.tm-next-head { font-size: 10.5px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; color: var(--accent-text); margin: 0 0 8px; font-family: var(--mono); }
.tm-next .card { margin: 0; border: 0; padding: 0; background: transparent; }
.tm-plan { white-space: pre-wrap; font-size: 13.5px; color: var(--text); }
.draft-text { background: var(--surface); border: 1px solid var(--border); border-left: 3px solid var(--accent-text); border-radius: var(--radius-sm); padding: 10px 12px; margin: 8px 0; }
#tmNote { width: 100%; }
.tm-evidence { margin: 2px 0 12px; font-family: var(--mono); font-size: 11.5px; }
.tm-chat { border-top: 1px solid var(--border); margin-top: 12px; padding-top: 12px; }
.tm-chat-log { max-height: 220px; overflow-y: auto; font-size: 13px; }
.tm-msg { background: var(--surface-2); border-radius: 9px; padding: 7px 10px; margin: 5px 0; white-space: pre-wrap; }
.tm-you { background: var(--accent-soft); }
.objective-card { margin: 6px 0; padding: 12px 14px; }
.obj-title { font-weight: 650; font-size: 13.5px; }
.obj-timeline, .obj-next { font-size: 12.5px; color: var(--text-2); margin-top: 4px; }
.obj-next a { color: var(--accent-text); text-decoration: none; }
.obj-details summary { font-size: 12px; color: var(--text-3); cursor: pointer; margin-top: 4px; }

/* ---- right rail ---- */
.side-panel { display: none; }
@media (min-width: 1400px) {
  .side-panel { display: block; position: sticky; top: 76px; align-self: start; padding: 16px; max-height: calc(100vh - 100px); overflow-y: auto; }
  .side-panel h3 { margin: 0 0 10px; color: var(--text); font-size: 13px; }
}
.today-brief { margin: 0 0 14px; padding: 0; background: transparent; border: 0; font-size: 13px; color: var(--text-2); }
.tb-line { margin: 0 0 10px; } .tb-overdue { color: var(--danger); } .today-brief a { color: var(--accent-text); }
.cal-box { margin-top: 10px; } .cal-head { font-weight: 650; font-size: 12.5px; margin-bottom: 6px; }
.cal { width: 100%; border-collapse: collapse; font-size: 11.5px; text-align: center; font-family: var(--mono); }
.cal th { color: var(--text-3); font-weight: 500; padding: 3px; }
.cal td { padding: 4px 1px; border-radius: 6px; color: var(--text-2); }
.cal-out { color: var(--border-strong) !important; } .cal-marked { background: var(--surface-2); }
.cal-today, .cal-today.cal-marked { background: var(--accent); color: var(--accent-ink) !important; font-weight: 800; }
.cal-dot { color: var(--danger); font-size: 9px; vertical-align: top; }

/* ---- chat ---- */
.chat-bubble { position: fixed; bottom: max(22px, env(safe-area-inset-bottom, 0px)); right: max(22px, env(safe-area-inset-right, 0px));
  width: 52px; height: 52px; border-radius: 16px; background: var(--accent); color: var(--accent-ink); display: flex; align-items: center;
  justify-content: center; font-size: 22px; cursor: pointer; box-shadow: var(--shadow); z-index: 1000; }
.chat-panel-hidden { display: none; }
#chatPanel { position: fixed; bottom: 22px; right: 22px; width: min(400px, 92vw); z-index: 1000; box-shadow: var(--shadow); padding: 14px; }
.chat-panel-header { display: flex; justify-content: space-between; align-items: center; font-weight: 700; margin-bottom: 10px; }
.chat-close { cursor: pointer; color: var(--text-3); font-weight: 400; }
.chat-log { max-height: 420px; overflow-y: auto; margin-bottom: 10px; display: flex; flex-direction: column; gap: 8px; }
#chatPanel .chat-log { max-height: 340px; }
.chat-msg { padding: 9px 12px; border-radius: 12px; max-width: 88%; font-size: 13.5px; }
.chat-you { background: var(--accent); color: var(--accent-ink); align-self: flex-end; }
.chat-assistant { background: var(--surface-2); color: var(--text); align-self: flex-start; }
.chat-role { font-size: 11px; opacity: .7; margin-bottom: 2px; }
.chat-you .meta { color: inherit; opacity: .7; }
.chat-body { white-space: pre-wrap; }
.chat-input-row { display: flex; gap: 8px; align-items: flex-end; }
.chat-input-row textarea { flex: 1; margin-bottom: 0; }

/* ---- settings panels ---- */
.mdl-box, .acct-list { border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); padding: 4px 16px; margin-bottom: 12px; }
.mdl-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--border); }
.mdl-row:last-child { border-bottom: 0; }
.mdl-tier { flex: 0 1 230px; min-width: 0; }
.mdl-prov { flex: 0 1 250px; min-width: 0; } .mdl-tier .meta { margin: 2px 0 0; }
.mdl-model { flex: 1 1 200px; min-width: 0; font-family: var(--mono); }
.mdl-key { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 6px 0; }
.mdl-key-name { flex: 0 0 240px; color: var(--text-2); }
.mdl-keys { margin: 12px 0; } .mdl-keys summary { cursor: pointer; font-weight: 600; }
.acct-row { margin: 6px 0; padding: 10px 14px; font-size: 13.5px; }
.acct-dot { font-weight: 700; margin-right: 4px; } .acct-id { color: var(--text-2); margin: 0 6px; font-family: var(--mono); font-size: 12.5px; }
.acct-fix { color: var(--danger); font-size: 12.5px; margin-top: 4px; }
.auth-overlay { position: fixed; inset: 0; background: rgba(5,6,8,.7); backdrop-filter: blur(4px); z-index: 1100; display: flex; align-items: center; justify-content: center; padding: 16px; }
.auth-box { padding: 20px 22px; max-width: 460px; box-shadow: var(--shadow); }
.auth-box h3 { margin: 0 0 10px; color: var(--text); font-size: 16px; }
.auth-reason { color: var(--text-2); } .auth-buttons { margin-top: 14px; display: flex; gap: 8px; } .auth-refuse { color: var(--danger); }
.inbox-item { font-size: 13.5px; padding: 8px 0; border-bottom: 1px solid var(--border); color: var(--text-2); }
.linked-domain { margin-top: 14px; padding: 14px 16px; background: var(--danger-soft); border: 1px solid color-mix(in srgb, var(--danger) 40%, transparent); border-radius: var(--radius); }
.linked-domain-title { font-weight: 700; font-size: 14px; color: var(--danger); margin-bottom: 8px; }
.linked-domain pre { background: var(--surface); color: var(--text); font-size: 12.5px; }
.lite-markdown ul { margin: 4px 0 8px; padding-left: 18px; } .lite-markdown li, .lite-markdown p { font-size: 13px; line-height: 1.55; margin: 4px 0; }
.archived-item { opacity: .7; padding: 12px 16px; }
.slack-preview-label, .extra-notes-label { font-size: 11.5px; color: var(--text-3); margin: 8px 0 4px; }
.slack-preview { background: var(--bg-elev); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 10px 12px; font-size: 13.5px; min-height: 1.5em; margin-bottom: 6px; }
.slack-preview code { background: var(--surface-3); }
.button-link { display: inline-flex; align-items: center; height: 34px; padding: 0 14px; border-radius: var(--radius-sm); background: var(--accent); color: var(--accent-ink); text-decoration: none; font-size: 13px; font-weight: 700; margin: 6px 0; }
.view-intro { color: var(--text-3); font-size: 13px; margin: -4px 0 16px; max-width: 70ch; }
"""
