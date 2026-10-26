/* Dana's computer: a file browser over the full Kestrel world.
   Mount with  Explorer.mount(element, {base: "data/"}).
   Loads base + "index.json", then base + "shards/NN.json" per folder on demand.
   Colors and fonts come from the host page's CSS tokens. */
(function () {
  const CSS = `
.ex { --ex-h: 640px; border: 1px solid var(--rule); background: var(--night-2); display: grid;
  grid-template-rows: auto minmax(0, 1fr); height: var(--ex-h); font-size: 14px; color: var(--text); }
.ex.full { --ex-h: calc(100vh - 2px); }
.ex-top { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; padding: 10px 12px; border-bottom: 1px solid var(--rule); }
.ex-crumb { font: 600 13px/1.3 var(--mono); color: var(--muted); min-width: 0; flex: 1 1 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ex-crumb b { color: var(--text); }
.ex-tabs, .ex-chips { display: inline-flex; border: 1px solid var(--rule); }
.ex-tabs button, .ex-chips button { font: 600 12px/1 var(--mono); letter-spacing: .04em; padding: 8px 10px; border: 0; background: transparent; color: var(--muted); cursor: pointer; }
.ex-tabs button + button, .ex-chips button + button { border-left: 1px solid var(--rule); }
.ex-tabs button[aria-pressed="true"], .ex-chips button[aria-pressed="true"] { background: var(--signal); color: var(--night); }
.ex-search { font: 13px var(--mono); background: var(--night); color: var(--text); border: 1px solid var(--rule); padding: 8px 10px; width: 210px; max-width: 100%; }
.ex-body { display: grid; grid-template-columns: 240px minmax(0, 1fr) minmax(0, 1.15fr); min-height: 0; }
.ex-pane { min-height: 0; overflow: auto; }
.ex-tree { border-right: 1px solid var(--rule); padding: 6px 0; font: 13px/1.2 var(--body); }
.ex-node { display: flex; align-items: center; gap: 6px; padding: 5px 10px 5px calc(10px + var(--d) * 14px); cursor: pointer; color: var(--muted); user-select: none; }
.ex-node:hover { background: var(--panel); color: var(--text); }
.ex-node.sel { background: color-mix(in srgb, var(--signal) 16%, transparent); color: var(--text); }
.ex-node .tw { width: 10px; color: var(--dim); font: 10px var(--mono); flex: none; }
.ex-node .nm { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ex-node .ct { font: 11px var(--mono); color: var(--dim); font-variant-numeric: tabular-nums; }
.ex-node .mk { width: 6px; height: 6px; flex: none; }
.ex-node .mk.s { background: var(--signal); box-shadow: 0 0 8px var(--signal); }
.ex-node .mk.a { border: 1px solid var(--late); }
.ex-list { border-right: 1px solid var(--rule); position: relative; }
.ex-rows { position: relative; }
.ex-row { position: absolute; left: 0; right: 0; height: 58px; padding: 9px 12px; border-bottom: 1px solid var(--rule); cursor: pointer; display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 2px 10px; }
.ex-row:hover { background: var(--panel); }
.ex-row.sel { background: color-mix(in srgb, var(--signal) 14%, transparent); }
.ex-row .t { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ex-row .w { grid-column: 1; color: var(--dim); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ex-row .dt { font: 11px var(--mono); color: var(--dim); text-align: right; }
.ex-row .bd { grid-column: 2; grid-row: 2; display: flex; gap: 4px; justify-content: flex-end; }
.ex-badge { font: 600 10px/1 var(--mono); letter-spacing: .06em; padding: 3px 5px; border: 1px solid var(--rule); color: var(--muted); white-space: nowrap; }
.ex-badge.s { color: var(--night); background: var(--signal); border-color: var(--signal); }
.ex-badge.a { color: var(--late); border-color: color-mix(in srgb, var(--late) 50%, var(--rule)); }
.ex-badge.ok { color: var(--ok); border-color: color-mix(in srgb, var(--ok) 50%, var(--rule)); }
.ex-empty { padding: 28px 16px; color: var(--dim); font: 13px/1.5 var(--mono); }
.ex-detail { padding: 18px; display: grid; gap: 14px; align-content: start; }
.ex-detail h4 { margin: 0; font: 700 19px/1.3 var(--display); letter-spacing: -.01em; overflow-wrap: anywhere; }
.ex-meta { font: 12px/1.6 var(--mono); color: var(--dim); overflow-wrap: anywhere; }
.ex-text { white-space: pre-wrap; overflow-wrap: anywhere; font: 14px/1.6 var(--body); color: var(--text); background: var(--night); border: 1px solid var(--rule); padding: 12px 14px; }
.ex-mark { border-left: 3px solid var(--signal); background: var(--panel); padding: 10px 12px; display: grid; gap: 4px; font-size: 13px; }
.ex-mark.a { border-left-color: var(--late); }
.ex-mark .k { font: 600 11px/1 var(--mono); letter-spacing: .1em; text-transform: uppercase; color: var(--signal); }
.ex-mark.a .k { color: var(--late); }
.ex-mark .v { color: var(--muted); }
.ex-link { background: none; border: 0; padding: 0; color: var(--signal); cursor: pointer; font: inherit; text-decoration: underline; text-underline-offset: 2px; }
.ex-tl { padding: 8px; display: grid; gap: 8px; }
.ex-task { border: 1px solid var(--rule); background: var(--night); padding: 10px 12px; cursor: pointer; display: grid; gap: 4px; }
.ex-task:hover, .ex-task.sel { border-color: var(--signal); }
.ex-task .n { font-weight: 600; }
.ex-task .i { font: 11px/1.4 var(--mono); color: var(--dim); }
.ex-loading { padding: 18px; font: 13px var(--mono); color: var(--dim); }
.ex .ex-back { display: none; }
.ex, .ex-top > *, .ex-body > *, .ex-detail > * { min-width: 0; }
.ex { max-width: 100%; }
@media (max-width: 900px) {
  .ex { --ex-h: 720px; }
  .ex-body { grid-template-columns: minmax(0, 1fr); }
  .ex-tree, .ex-list { border-right: 0; }
  .ex[data-pane="tree"] .ex-list, .ex[data-pane="tree"] .ex-detail { display: none; }
  .ex[data-pane="list"] .ex-tree, .ex[data-pane="list"] .ex-detail { display: none; }
  .ex[data-pane="detail"] .ex-tree, .ex[data-pane="detail"] .ex-list { display: none; }
  .ex .ex-back { display: inline-flex; }
  .ex-top { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 8px; }
  .ex-crumb { white-space: normal; }
  .ex-tabs, .ex-chips, .ex-search { grid-column: 1 / -1; width: 100%; }
  .ex-tabs button, .ex-chips button { flex: 1; }
  .ex[data-pane="tree"] .ex-back { visibility: hidden; }
}`;
  const ROW = 58;
  const esc = s => String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const fmtDate = d => { const x = new Date(d); return isNaN(x) ? d : x.toLocaleDateString("en-US", {month: "short", day: "numeric"}) + " " + x.toISOString().slice(11, 16); };
  const num = n => Number(n || 0).toLocaleString("en-US");
  const KIND = {gmail: "Mail", slack: "Slack", jira: "Jira", github: "GitHub", calendar: "Calendar", drive: "Drive"};

  function stateLine(st) {
    if (!st) return "not started yet";
    if (st.state === "absent") return "should be gone (done, cancelled, someone else's, or a trap)";
    const bits = ["open", st.workspace, st.due ? "due " + st.due : "no date"];
    if (st.priority) bits.push(st.priority);
    if (st.owner === "counterparty") bits.push("waiting on someone");
    return bits.join(" · ");
  }

  function mount(root, opts) {
    opts = opts || {};
    const base = opts.base || "data/";
    if (!document.getElementById("ex-css")) { const s = document.createElement("style"); s.id = "ex-css"; s.textContent = CSS; document.head.appendChild(s); }
    root.classList.add("ex"); if (opts.full) root.classList.add("full");
    root.dataset.pane = "list";
    root.innerHTML = `<div class="ex-top">
        <button class="btn sm ex-back" type="button" data-back>← Folders</button>
        <div class="ex-crumb" data-crumb>Loading Dana's computer…</div>
        <div class="ex-tabs" role="group" aria-label="View">
          <button type="button" data-tab="files" aria-pressed="true">Files</button>
          <button type="button" data-tab="tasks" aria-pressed="false">What it found</button>
          <button type="button" data-tab="answers" aria-pressed="false">Answer key</button>
        </div>
        <div class="ex-chips" role="group" aria-label="Show">
          <button type="button" data-f="all" aria-pressed="true">All</button>
          <button type="button" data-f="s" aria-pressed="false">Spotted</button>
          <button type="button" data-f="a" aria-pressed="false">In answer key</button>
        </div>
        <input class="ex-search" type="search" placeholder="Search this folder" aria-label="Search this folder" data-q id="${(opts.id || "ex") + "-q"}">
      </div>
      <div class="ex-body">
        <div class="ex-pane ex-tree" data-tree></div>
        <div class="ex-pane ex-list" data-list><div class="ex-rows" data-rows></div></div>
        <div class="ex-pane ex-detail" data-detail><div class="ex-empty">Pick a folder, then an item. Items the agent used are marked SPOTTED; items behind a task in the answer key are marked ANSWER.</div></div>
      </div>`;
    const $ = sel => root.querySelector(sel);
    const S = {index: null, shards: {}, leaf: null, rows: [], view: [], sel: null, filter: "all", q: "", tab: "files", open: new Set(["Dana's computer", "Mail", "Slack"])};

    async function shard(n) {
      if (!S.shards[n]) S.shards[n] = fetch(base + "shards/" + String(n).padStart(2, "0") + ".json").then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });
      return S.shards[n];
    }

    function nodeHTML(node, depth, path) {
      const p = path ? path + "/" + node.name : node.name;
      const kids = node.children || [];
      const isOpen = S.open.has(p) || depth === 0;
      const sel = S.leaf && node.leaf === S.leaf ? " sel" : "";
      let h = `<div class="ex-node${sel}" style="--d:${depth}" data-p="${esc(p)}" ${node.leaf ? `data-leaf="${esc(node.leaf)}" data-shard="${node.shard}"` : ""} role="treeitem" tabindex="0">
        <span class="tw">${kids.length ? (isOpen ? "▾" : "▸") : ""}</span><span class="nm">${esc(node.name)}</span>
        ${node.s ? '<span class="mk s" title="has spotted items"></span>' : ""}${node.a && !node.s ? '<span class="mk a" title="has answer-key items"></span>' : ""}
        <span class="ct">${num(node.n)}</span></div>`;
      if (kids.length && isOpen) for (const k of kids) {
        if (S.filter === "s" && !k.s) continue;
        if (S.filter === "a" && !k.a) continue;
        h += nodeHTML(k, depth + 1, p);
      }
      return h;
    }
    function renderTree() { $("[data-tree]").innerHTML = nodeHTML(S.index.tree, 0, ""); }

    function crumb(text) { $("[data-crumb]").innerHTML = text; }

    function badges(it) {
      let b = "";
      if (it.s) b += '<span class="ex-badge s">SPOTTED</span>';
      if (it.a != null) { const r = S.index.answers[it.a].result || {}; const c1 = r.c1; b += `<span class="ex-badge ${c1 && c1.pass ? "ok" : "a"}">ANSWER</span>`; }
      return b;
    }
    function applyFilter() {
      const q = S.q.toLowerCase();
      S.view = S.rows.filter(it => (S.filter === "all" || (S.filter === "s" ? it.s : it.a != null)) &&
        (!q || (it.t + " " + it.w + " " + it.x).toLowerCase().includes(q)));
      const list = $("[data-list]"), rows = $("[data-rows]");
      rows.style.height = (S.view.length * ROW) + "px";
      list.scrollTop = 0; drawRows();
      if (!S.view.length) rows.innerHTML = `<div class="ex-empty">${S.rows.length ? "Nothing here matches." : "Empty folder."}</div>`;
    }
    function drawRows() {
      const list = $("[data-list]"), rows = $("[data-rows]");
      if (!S.view.length) return;
      const top = list.scrollTop, h = list.clientHeight || 600;
      const a = Math.max(0, Math.floor(top / ROW) - 8), z = Math.min(S.view.length, Math.ceil((top + h) / ROW) + 8);
      let out = "";
      for (let k = a; k < z; k++) {
        const it = S.view[k];
        out += `<div class="ex-row${S.sel && S.sel.id === it.id ? " sel" : ""}" style="top:${k * ROW}px" data-k="${k}">
          <span class="t">${esc(it.t)}</span><span class="dt">${fmtDate(it.d)}</span>
          <span class="w">${esc(it.w)}</span><span class="bd">${badges(it)}</span></div>`;
      }
      rows.innerHTML = out;
    }

    async function openLeaf(leaf, sh, selectId) {
      S.leaf = leaf; S.tab = "files"; setTab("files", true);
      leaf.split("/").reduce((acc, part) => { const p = acc ? acc + "/" + part : part; S.open.add("Dana's computer/" + p); return p; }, "");
      renderTree();
      crumb(`<b>${esc(leaf.split("/").slice(-1)[0])}</b> · ${esc(leaf.split("/").slice(0, -1).join(" / "))}`);
      $("[data-rows]").innerHTML = '<div class="ex-loading">Opening folder…</div>';
      try {
        const data = await shard(sh);
        S.rows = data[leaf] || [];
      } catch (e) { $("[data-rows]").innerHTML = '<div class="ex-empty">Could not load this folder. Try again in a moment.</div>'; return; }
      applyFilter();
      crumb(`<b>${esc(leaf.split("/").slice(-1)[0])}</b> · ${num(S.rows.length)} items · ${esc(leaf.split("/").slice(0, -1).join(" / "))}`);
      root.dataset.pane = "list";
      if (selectId) {
        const k = S.view.findIndex(x => x.id === selectId);
        if (k < 0 && S.filter !== "all") { setFilter("all"); return openLeaf(leaf, sh, selectId); }
        if (k >= 0) { $("[data-list]").scrollTop = Math.max(0, k * ROW - 120); drawRows(); showItem(S.view[k]); }
      }
    }

    function findLeaf(node, leaf) {
      if (node.leaf === leaf) return node;
      for (const c of node.children || []) { const r = findLeaf(c, leaf); if (r) return r; }
      return null;
    }
    function goto(id) {
      const leaf = S.index.where[id]; if (!leaf) return;
      const n = findLeaf(S.index.tree, leaf); if (n) openLeaf(leaf, n.shard, id);
    }

    function showItem(it) {
      S.sel = it; drawRows();
      let h = `<div class="ex-meta">${KIND[it.c] || it.c} · ${esc(it.d.replace("T", " ").replace("Z", ""))} · ${esc(it.id)}</div>
        <h4>${esc(it.t)}</h4><div class="ex-meta">${esc(it.w)}</div>`;
      if (it.s) for (const k of it.s) {
        const t = S.index.tasks[k];
        h += `<div class="ex-mark"><span class="k">Spotted · ${t.cp === "c1" ? "first read, Oct 13" : "after the weekly checks, Nov 10"}</span>
          <span>${esc(t.name)}</span><span class="v">${esc([t.ws, t.due ? "due " + t.due : "no date", t.priority, t.waiting_on ? "waiting on " + t.waiting_on : ""].filter(Boolean).join(" · "))}</span></div>`;
      }
      if (it.a != null) {
        const a = S.index.answers[it.a], r = a.result || {};
        const res = cp => r[cp] ? (r[cp].pass ? "fully right" : (a[cp] && a[cp].state === "absent" ? "should be gone, still listed" : (r[cp].caught ? "caught, a detail wrong" : "missed"))) : "not scored";
        h += `<div class="ex-mark a"><span class="k">Answer key · ${esc(a.id)} (${esc(a.split)}) · ${esc(a.kind)}</span>
          <span class="v">Oct 13: ${esc(stateLine(a.c1))}. Result: ${res("c1")}.</span>
          <span class="v">Nov 10: ${esc(stateLine(a.c2))}. Result: ${res("c2")}.</span>
          <span class="v">${a.ids.length} source items. <button type="button" class="ex-link" data-answer="${it.a}">See them all</button></span></div>`;
      }
      h += `<div class="ex-text">${esc(it.x)}</div>`;
      if (it.m) h += `<div class="ex-meta">${Object.entries(it.m).map(([k, v]) => esc(k) + ": " + esc(Array.isArray(v) ? v.join(", ") : v)).join("<br>")}</div>`;
      $("[data-detail]").innerHTML = h;
      root.dataset.pane = "detail";
    }

    function listSources(title, ids, note) {
      root.dataset.pane = "detail";
      $("[data-detail]").innerHTML = `<div class="ex-meta">${esc(note || "")}</div><h4>${esc(title)}</h4>
        <div class="ex-tl">${ids.map(id => `<div class="ex-task" data-goto="${esc(id)}"><span class="n">${esc(id)}</span><span class="i">${esc(S.index.where[id] || "")}</span></div>`).join("") || '<div class="ex-empty">No source items cited.</div>'}</div>`;
    }

    function renderTab() {
      const L = $("[data-rows]"), list = $("[data-list]");
      list.scrollTop = 0; L.style.height = "auto";
      if (S.tab === "tasks") {
        const ts = S.index.tasks;
        crumb(`<b>What it found</b> · ${num(ts.filter(t => t.cp === "c1").length)} open tasks on Oct 13, ${num(ts.filter(t => t.cp === "c2").length)} on Nov 10`);
        L.innerHTML = ts.length ? `<div class="ex-tl">${ts.map((t, k) => `<div class="ex-task" data-task="${k}"><span class="n">${esc(t.name)}</span>
          <span class="i">${t.cp === "c1" ? "Oct 13" : "Nov 10"} · ${esc(t.ws)} · ${t.due ? "due " + t.due : "no date"}${t.priority ? " · " + esc(t.priority) : ""} · ${t.ids.length} sources</span></div>`).join("")}</div>`
          : '<div class="ex-empty">The recorded run is still being added.</div>';
      } else if (S.tab === "answers") {
        const as = S.index.answers;
        const pass = as.filter(a => a.result && a.result.c1 && a.result.c1.pass).length;
        crumb(`<b>Answer key</b> · ${as.length} tasks${as[0] && as[0].result && as[0].result.c1 ? " · " + pass + " fully right on Oct 13" : ""}`);
        L.innerHTML = `<div class="ex-tl">${as.map((a, k) => { const r = a.result && a.result.c1; return `<div class="ex-task" data-answer="${k}"><span class="n">${esc(a.id)} · ${esc(a.kind)}</span>
          <span class="i">${esc(a.split)} · Oct 13: ${esc(stateLine(a.c1))}${r ? " · " + (r.pass ? "fully right" : "not right") : ""}</span></div>`; }).join("")}</div>`;
      }
    }
    function setTab(tab, quiet) {
      S.tab = tab;
      root.querySelectorAll("[data-tab]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.tab === tab)));
      $(".ex-chips").style.display = tab === "files" ? "" : "none";
      $("[data-q]").style.display = tab === "files" ? "" : "none";
      if (!quiet) { if (tab === "files") { S.leaf ? applyFilter() : null; } else { renderTab(); root.dataset.pane = "list"; } }
    }
    function setFilter(f) {
      S.filter = f;
      root.querySelectorAll("[data-f]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.f === f)));
      renderTree(); if (S.leaf) applyFilter();
    }

    root.addEventListener("click", e => {
      const n = e.target.closest(".ex-node");
      if (n) {
        const p = n.dataset.p;
        if (n.dataset.leaf) openLeaf(n.dataset.leaf, +n.dataset.shard);
        else { S.open.has(p) ? S.open.delete(p) : S.open.add(p); renderTree(); }
        return;
      }
      const r = e.target.closest(".ex-row"); if (r) { showItem(S.view[+r.dataset.k]); return; }
      const tb = e.target.closest("[data-tab]"); if (tb) { setTab(tb.dataset.tab); return; }
      const fb = e.target.closest("[data-f]"); if (fb) { setFilter(fb.dataset.f); return; }
      const g = e.target.closest("[data-goto]"); if (g) { goto(g.dataset.goto); return; }
      const t = e.target.closest("[data-task]"); if (t) { const x = S.index.tasks[+t.dataset.task]; listSources(x.name, x.ids, (x.cp === "c1" ? "Found on Oct 13" : "Open on Nov 10") + " · " + x.ws); return; }
      const an = e.target.closest("[data-answer]"); if (an) { const a = S.index.answers[+an.dataset.answer]; listSources(a.id + " · " + a.kind, a.ids, "Answer key, " + a.split + " half"); return; }
      if (e.target.closest("[data-back]")) { root.dataset.pane = root.dataset.pane === "detail" ? "list" : "tree"; }
    });
    root.addEventListener("keydown", e => { if ((e.key === "Enter" || e.key === " ") && e.target.classList.contains("ex-node")) { e.preventDefault(); e.target.click(); } });
    $("[data-list]").addEventListener("scroll", () => { if (S.tab === "files") drawRows(); }, {passive: true});
    $("[data-q]").addEventListener("input", e => { S.q = e.target.value; if (S.leaf) applyFilter(); });

    fetch(base + "index.json").then(r => r.json()).then(ix => {
      S.index = ix; renderTree();
      crumb(`<b>Dana's computer</b> · ${num(ix.total)} items · ${num(ix.before_first_read)} before the first read`);
      const first = opts.start || "Mail/Freelance (dana.builds@mailbox.example)/Inbox/2026-10 October";
      const n = findLeaf(ix.tree, first);
      if (n) openLeaf(first, n.shard);
    }).catch(() => crumb("Could not load the data. Reload the page to try again."));
  }
  window.Explorer = {mount};
})();
