// GEO Guardian frontend

const $ = (s) => document.querySelector(s);
const el = (tag, cls, html) => { const n = document.createElement(tag); if (cls) n.className = cls; if (html != null) n.innerHTML = html; return n; };
const icon = (id) => `<svg><use href="#${id}"/></svg>`;
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const runBtn = $("#run-btn");
const hint = $("#input-hint");
const fields = ["brand", "category", "competitors", "probes"].map((id) => $("#" + id));

function updateRun() {
  runBtn.disabled = !($("#brand").value.trim() && $("#category").value.trim());
  const usingFixedQuestions = !!($("#questions") && $("#questions").value.trim());
  $("#probes").disabled = usingFixedQuestions;
  hint.textContent = "";
}
fields.forEach((f) => f.addEventListener("input", updateRun));
if ($("#questions")) $("#questions").addEventListener("input", updateRun);

// presets
async function loadPresets() {
  try {
    const presets = await (await fetch("/api/presets")).json();
    if (!Array.isArray(presets)) return;
    const box = $("#preset-chips");
    presets.forEach((p) => {
      const chip = el("button", "chip");
      chip.textContent = p.name;
      chip.onclick = () => {
        document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        $("#brand").value = p.brand || "";
        $("#category").value = p.category || "";
        $("#competitors").value = p.competitors || "";
        if ($("#questions") && Array.isArray(p.questions)) {
          $("#questions").value = p.questions.join("\n");
          $("#probes").value = String(Math.min(Math.max(p.questions.length, 3), 6));
          const details = document.querySelector(".custom-q");
          if (details) details.open = true;
        }
        updateRun();
      };
      box.appendChild(chip);
    });
  } catch (e) { /* optional */ }
}

// run
runBtn.onclick = () => {
  const fd = new FormData();
  fd.append("brand", $("#brand").value.trim());
  fd.append("category", $("#category").value.trim());
  fd.append("competitors", $("#competitors").value.trim());
  fd.append("probes", $("#probes").value || "4");
  fd.append("questions", ($("#questions") && $("#questions").value) || "");

  $("#setup").classList.add("hidden");
  $("#board").classList.remove("hidden");
  $("#probe-live").innerHTML = "";
  $("#dash").innerHTML = "";
  $("#scan-status").textContent = "Starting scan...";
  $("#reset-row").classList.add("hidden");
  $("#board").scrollIntoView({ behavior: "smooth", block: "start" });

  (async () => {
    const host = window.location.hostname;
    const useStreaming = host === "localhost" || host === "127.0.0.1" || host === "::1";
    if (!useStreaming) {
      $("#scan-status").textContent = "Running hosted scan. This can take 30-60 seconds...";
      try {
        const resp = await fetch("/api/run", { method: "POST", body: fd });
        const out = await resp.json();
        if (out.error) return showError(out.error);
        if (!out.data) return showError("The server did not return scan data.");
        return renderDash(out.data);
      } catch (e) {
        return showError("Could not complete the hosted scan. Please retry.");
      }
    }

    let job;
    try { job = await (await fetch("/api/process", { method: "POST", body: fd })).json(); }
    catch (e) { return showError("Could not reach the server. Is it running?"); }
    if (!job || !job.job_id) return showError("The server did not start a job.");

    let done = false;
    const es = new EventSource("/api/events/" + job.job_id);
    es.onmessage = (msg) => {
      let ev;
      try { ev = JSON.parse(msg.data); } catch (e) { return; }
      if (ev.type === "progress") $("#scan-status").textContent = ev.status;
      else if (ev.type === "probe") addProbePill(ev.data);
      else if (ev.type === "result") { done = true; es.close(); renderDash(ev.data); }
      else if (ev.type === "error") { done = true; es.close(); showError(ev.message); }
    };
    es.onerror = () => { es.close(); if (!done) showError("Lost connection during the scan. Please retry."); };
  })();
};

function addProbePill(p) {
  const yes = p.mentioned;
  const pill = el("div", "probe-pill");
  pill.innerHTML = `<span class="pq">${esc(p.query)}</span>` +
    `<span class="badge ${yes ? "yes" : "no"}">${icon(yes ? "i-check" : "i-x")} ${yes ? (p.rank ? "rank " + p.rank : "mentioned") : "absent"}</span>`;
  $("#probe-live").appendChild(pill);
}

function showError(message) {
  $("#scan-status").textContent = "";
  document.querySelector(".scan-spark").style.animation = "none";
  $("#dash").innerHTML = `<div class="panel"><h3>${icon("i-alert")} Scan failed</h3>
    <p style="color:var(--muted)">${esc(message)}</p>
    <p style="color:var(--muted)">Use the Add API key button or set OPENAI_API_KEY on the server, then retry.</p></div>`;
  $("#reset-row").classList.remove("hidden");
}

// ---------- dashboard ----------
function band(score) {
  if (score >= 75) return { label: "Strong", color: "var(--accent)", desc: "Your brand wins most AI answers in this category." };
  if (score >= 50) return { label: "Moderate", color: "var(--accent)", desc: "Present, but competitors still take a big share of answers." };
  if (score >= 25) return { label: "Low", color: "var(--amber)", desc: "Rarely recommended — competitors dominate the answers." };
  return { label: "Critical", color: "var(--red)", desc: "Practically invisible in AI answers for this category." };
}

function ring(score) {
  const r = 66, c = 2 * Math.PI * r;
  const off = c * (1 - Math.max(0, Math.min(100, score)) / 100);
  const col = band(score).color;
  return `<div class="ring"><svg width="150" height="150" viewBox="0 0 150 150">
      <circle cx="75" cy="75" r="${r}" fill="none" stroke="var(--panel-2)" stroke-width="12"/>
      <circle cx="75" cy="75" r="${r}" fill="none" stroke="${col}" stroke-width="12" stroke-linecap="round"
        stroke-dasharray="${c.toFixed(1)}" stroke-dashoffset="${off.toFixed(1)}"/>
    </svg><div class="ring-num"><div class="rn" style="color:${col}">${score}</div><div class="rl">/ 100</div></div></div>`;
}

const sentClass = (s) => ({ positive: "positive", neutral: "neutral", negative: "negative" }[(s || "").toLowerCase()] || "absent");

let lastData = null;

function renderDash(d) {
  lastData = d;
  document.querySelector(".scan-spark").style.animation = "none";
  $("#scan-status").textContent = "Scan complete.";
  $("#probe-live").innerHTML = "";
  const dash = $("#dash");
  dash.innerHTML = "";

  const sc = d.score || {};
  const b = band(sc.visibility_score || 0);
  const curScore = sc.visibility_score || 0;
  const trendKey = "geo:last:" + (d.brand || "").toLowerCase() + "|" + (d.category || "").toLowerCase();
  let prevScan = null;
  try { prevScan = JSON.parse(localStorage.getItem(trendKey) || "null"); } catch (e) {}

  // header + download report
  const head = el("div", "panel dash-head",
    `<div><h2>${esc(d.brand)}</h2><div class="sub">${esc(d.category)}${d.competitors && d.competitors.length ? " · vs " + d.competitors.map(esc).join(", ") : ""}</div></div>
     <button class="btn-ghost dl-report">${icon("i-download")} Download report</button>`);
  head.querySelector(".dl-report").onclick = () => downloadReport(d);
  dash.appendChild(head);

  // executive summary
  const summ = d.summary || {};
  if (summ.headline) {
    dash.appendChild(el("div", "panel summary-panel",
      `<h3>${icon("i-bolt")} Executive summary</h3>
       <p class="summ-head">${esc(summ.headline)}</p>
       ${(summ.key_findings || []).length ? `<ul class="summ-list">${summ.key_findings.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
       ${summ.top_priority ? `<p class="summ-top"><b>Top priority:</b> ${esc(summ.top_priority)}</p>` : ""}`));
  }

  // score
  const delta = prevScan ? curScore - prevScan.score : null;
  const trendHtml = (delta === null) ? "" :
    `<span class="trend ${delta > 0 ? "up" : delta < 0 ? "down" : "flat"}">${delta > 0 ? "▲ +" + delta : delta < 0 ? "▼ " + delta : "no change"} vs last scan</span>`;
  dash.appendChild(el("div", "panel", `<h3>Visibility score</h3>
    <div class="scorewrap">${ring(curScore)}
      <div class="score-side">
        <p class="band" style="color:${b.color}">${b.label} ${trendHtml}</p>
        <p class="desc">${b.desc}</p>
        <div class="statline">
          <div class="s"><b>${sc.mention_rate || 0}%</b><span>mention rate</span></div>
          <div class="s"><b>${sc.mentions || 0}/${sc.probes_total || 0}</b><span>answers featuring brand</span></div>
        </div>
        <details class="method"><summary>${icon("i-info")} How is this scored?</summary>
          <p>Each question where the brand appears scores by rank (1st = 1.0, 2nd = 0.75, 3rd = 0.55, lower = 0.4) × sentiment (positive = 1.0, neutral = 0.85, negative = 0.45); absent = 0. The visibility score is the average across all questions, ×100. Share of voice is the % of questions that mention each brand. These numbers are computed in code, not by the model.</p>
        </details>
      </div></div>`));

  // share of voice
  const sov = (sc.share_of_voice || []);
  const maxPct = Math.max(100, ...sov.map((x) => x.pct || 0));
  dash.appendChild(el("div", "panel", `<h3>Share of voice</h3><div class="sov">` +
    sov.map((x) => `<div class="sov-row ${x.is_brand ? "brand" : ""}">
      <div class="sov-name"><span class="dot"></span>${esc(x.name)}</div>
      <div class="sov-track"><div class="sov-fill" style="width:${Math.round((x.pct || 0) / maxPct * 100)}%"></div></div>
      <div class="sov-pct">${x.pct || 0}%</div></div>`).join("") + `</div>`));

  // probe table (rows clickable -> the AI's full answer)
  const ptbl = el("div", "panel", `<h3>Probe results <span class="hint-inline">— click a row to read the AI's full answer</span></h3>
    <table class="ptable"><thead><tr><th>Question asked to the AI</th><th>Brand</th><th>Rank</th><th>Sentiment</th></tr></thead><tbody></tbody></table>`);
  const tb = ptbl.querySelector("tbody");
  (d.probes || []).forEach((p) => {
    const tr = el("tr", "prow");
    tr.innerHTML = `<td class="q">${esc(p.query)}<div class="snip">${esc((p.snippet || "").slice(0, 160))}</div></td>
      <td>${p.mentioned ? `<span class="badge yes">${icon("i-check")} yes</span>` : `<span class="badge no">${icon("i-x")} no</span>`}</td>
      <td>${p.rank ? "#" + p.rank : "—"}</td>
      <td><span class="sent ${sentClass(p.sentiment)}">${esc(p.sentiment || "absent")}</span></td>`;
    tr.onclick = () => openProbeModal(p);
    tb.appendChild(tr);
  });
  dash.appendChild(ptbl);

  // issues
  if (sc.issues && sc.issues.length) {
    dash.appendChild(el("div", "panel", `<h3>${icon("i-alert")} Detected errors about your brand</h3>
      <ul class="issues">${sc.issues.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`));
  }

  // remediation
  const items = (d.remediation && d.remediation.items) || [];
  const remPanel = el("div", "panel", `<h3>${icon("i-bolt")} Remediation playbook</h3>` +
    items.map((it, i) => `<label class="rem-item">
      <input type="checkbox" data-i="${i}" checked>
      <div><div class="ra">${esc(it.action)}</div><div class="rr">${esc(it.rationale)}</div></div>
      <div class="rem-badges"><span class="pill ${esc((it.impact || "").toLowerCase())}">impact: ${esc(it.impact)}</span><span class="pill ${esc((it.effort || "").toLowerCase())}">effort: ${esc(it.effort)}</span></div>
    </label>`).join("") +
    `<div class="rem-actions"><button class="btn-accent gen-brief">${icon("i-doc")} Generate content brief</button>
      <span class="brief-note" style="color:var(--muted);font-size:13px"></span></div>
     <div class="brief-out"></div>`);
  dash.appendChild(remPanel);

  remPanel.querySelector(".gen-brief").onclick = async () => {
    const chosen = Array.from(remPanel.querySelectorAll('input[type="checkbox"]:checked')).map((cb) => items[+cb.dataset.i].action);
    const note = remPanel.querySelector(".brief-note");
    const out = remPanel.querySelector(".brief-out");
    if (!chosen.length) { note.textContent = "Select at least one action."; return; }
    note.innerHTML = `<span class="spinner"></span> Drafting brief...`;
    try {
      const br = await (await fetch("/api/brief", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brand: d.brand, category: d.category, actions: chosen }) })).json();
      note.textContent = "";
      if (br.error) { note.textContent = br.error; return; }
      out.innerHTML = `<div class="brief"><h4>${esc(br.title)}</h4><p class="sub">Audience: ${esc(br.audience)}</p>
        ${br.target_queries && br.target_queries.length ? `<div class="subhead">Target queries</div><ul>${br.target_queries.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
        ${br.key_points && br.key_points.length ? `<div class="subhead">Key points</div><ul>${br.key_points.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
        ${br.outline && br.outline.length ? `<div class="subhead">Outline</div><ul>${br.outline.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}</div>`;
    } catch (e) { note.textContent = "Could not draft the brief. Please retry."; }
  };

  // audit
  dash.appendChild(el("div", "panel", `<h3>${icon("i-clip")} Audit trail</h3><div class="audit">` +
    (d.audit_log || []).map((e) => `<div><span class="a-time">[${esc(e.timestamp)}]</span> <span class="a-agent">${esc(e.agent)}</span>: ${esc(e.summary)}</div>`).join("") + `</div>`));

  try { localStorage.setItem(trendKey, JSON.stringify({ score: curScore, ts: Date.now() })); } catch (e) {}

  $("#reset-row").classList.remove("hidden");
  dash.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---------- modal + report ----------
function openModal(html) { $("#modal-body").innerHTML = html; $("#modal").classList.remove("hidden"); }
function openProbeModal(p) {
  openModal(`<h3>${icon("i-radar")} What the AI actually answered</h3>
    <p class="m-q">${esc(p.query)}</p>
    <div class="m-meta">
      ${p.mentioned ? `<span class="badge yes">${icon("i-check")} mentioned${p.rank ? " · rank " + p.rank : ""}</span>` : `<span class="badge no">${icon("i-x")} absent</span>`}
      <span class="sent ${sentClass(p.sentiment)}">${esc(p.sentiment || "absent")}</span>
    </div>
    ${(p.competitors_mentioned && p.competitors_mentioned.length) ? `<p class="m-sub">Competitors named: ${p.competitors_mentioned.map(esc).join(", ")}</p>` : ""}
    ${(p.issues && p.issues.length) ? `<p class="m-sub" style="color:var(--red)">Errors about the brand: ${p.issues.map(esc).join("; ")}</p>` : ""}
    <div class="m-answer">${esc(p.answer || "")}</div>`);
}
function downloadReport(d) {
  const sc = d.score || {}, summ = d.summary || {};
  let m = `# GEO Guardian report — ${d.brand}\n\nCategory: ${d.category}\nCompetitors: ${(d.competitors || []).join(", ")}\n\n`;
  m += `Visibility score: ${sc.visibility_score || 0}/100 (${band(sc.visibility_score || 0).label})\n`;
  m += `Mention rate: ${sc.mention_rate || 0}% · ${sc.mentions || 0}/${sc.probes_total || 0} answers feature the brand\n\n`;
  if (summ.headline) { m += `## Executive summary\n${summ.headline}\n`; (summ.key_findings || []).forEach((x) => m += `- ${x}\n`); if (summ.top_priority) m += `\nTop priority: ${summ.top_priority}\n`; m += `\n`; }
  m += `## Share of voice\n`; (sc.share_of_voice || []).forEach((x) => m += `- ${x.name}${x.is_brand ? " (you)" : ""}: ${x.pct}%\n`); m += `\n`;
  m += `## Probe results\n`; (d.probes || []).forEach((p) => { m += `### ${p.query}\n- Mentioned: ${p.mentioned ? ("yes" + (p.rank ? ", rank " + p.rank : "")) : "no"} · sentiment: ${p.sentiment || "absent"}\n`; if (p.competitors_mentioned && p.competitors_mentioned.length) m += `- Competitors named: ${p.competitors_mentioned.join(", ")}\n`; if (p.issues && p.issues.length) m += `- Errors: ${p.issues.join("; ")}\n`; m += `- AI answer: ${(p.answer || "").replace(/\s+/g, " ").trim()}\n\n`; });
  if (sc.issues && sc.issues.length) { m += `## Detected errors\n`; sc.issues.forEach((x) => m += `- ${x}\n`); m += `\n`; }
  const items = (d.remediation && d.remediation.items) || []; if (items.length) { m += `## Remediation playbook\n`; items.forEach((it) => m += `- [impact ${it.impact} / effort ${it.effort}] ${it.action} — ${it.rationale}\n`); m += `\n`; }
  const blob = new Blob([m], { type: "text/markdown" }); const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `geo-report-${(d.brand || "brand").replace(/\s+/g, "_")}.md`; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// reset
$("#reset-btn").onclick = () => {
  $("#board").classList.add("hidden");
  $("#reset-row").classList.add("hidden");
  $("#setup").classList.remove("hidden");
  document.querySelector(".scan-spark").style.animation = "";
  window.scrollTo({ top: 0, behavior: "smooth" });
};

$("#modal-x").onclick = () => $("#modal").classList.add("hidden");
$("#modal").addEventListener("click", (e) => { if (e.target === $("#modal")) $("#modal").classList.add("hidden"); });

loadPresets();
updateRun();

/* ============================================================
   Bring-your-own OpenAI key (for public / self-hosted demo).
   Adds a top-bar button; stores the key in localStorage and
   sends it as X-OpenAI-Key on every /api/ request. The server
   uses it if present, otherwise falls back to its .env key.
   ============================================================ */
(function () {
  var KEY = "OPENAI_KEY";
  var _fetch = window.fetch.bind(window);
  window.fetch = function (url, opts) {
    opts = opts || {};
    var k = localStorage.getItem(KEY);
    if (k && typeof url === "string" && url.indexOf("/api/") === 0) {
      opts = Object.assign({}, opts);
      opts.headers = Object.assign({}, opts.headers || {}, { "X-OpenAI-Key": k });
    }
    return _fetch(url, opts);
  };

  var ACC = "var(--accent, var(--teal, var(--accent-deep, #2563eb)))";
  var CARD = "var(--card, var(--panel, var(--paper, #ffffff)))";
  var INK = "var(--ink, #1a1a1a)";
  var LINE = "var(--line, #dddddd)";
  var MUTED = "var(--muted, var(--slate, var(--muted-ink, #888888)))";
  var css =
    ".kk-btn{display:inline-flex;align-items:center;gap:7px;border:1px solid " + LINE + ";background:" + CARD + ";color:" + INK + ";font:inherit;font-size:12.5px;font-weight:600;padding:7px 12px;border-radius:999px;cursor:pointer}" +
    ".kk-btn:hover{border-color:" + ACC + "}" +
    ".kk-dot{width:8px;height:8px;border-radius:50%;background:#d9a33a}" +
    ".kk-dot.on{background:#2aa676}" +
    ".kk-ov{position:fixed;inset:0;background:rgba(10,15,20,.55);display:grid;place-items:center;z-index:99999;padding:20px}" +
    ".kk-card{background:" + CARD + ";color:" + INK + ";border:1px solid " + LINE + ";border-radius:14px;max-width:440px;width:100%;padding:24px;box-shadow:0 30px 80px -30px rgba(0,0,0,.5);font-family:inherit}" +
    ".kk-card h4{margin:0 0 6px;font-size:18px}" +
    ".kk-card p{margin:0 0 14px;font-size:13px;color:" + MUTED + "}" +
    ".kk-card input{width:100%;box-sizing:border-box;border:1px solid " + LINE + ";border-radius:10px;padding:11px 13px;font:inherit;font-size:14px;background:" + CARD + ";color:" + INK + "}" +
    ".kk-card input:focus{outline:none;border-color:" + ACC + "}" +
    ".kk-row{display:flex;gap:10px;margin-top:14px}" +
    ".kk-save{flex:1;border:none;cursor:pointer;background:" + ACC + ";color:#fff;border-radius:10px;padding:11px;font:inherit;font-weight:600}" +
    ".kk-clear{border:1px solid " + LINE + ";background:transparent;color:" + INK + ";border-radius:10px;padding:11px 16px;cursor:pointer;font:inherit;font-weight:600}" +
    ".kk-note{margin-top:12px;font-size:11.5px;color:" + MUTED + ";line-height:1.5}";
  var st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);

  var btn = document.createElement("button");
  btn.className = "kk-btn";
  btn.type = "button";
  function refresh() {
    var has = !!localStorage.getItem(KEY);
    btn.innerHTML = '<span class="kk-dot' + (has ? " on" : "") + '"></span>' + (has ? "API key set" : "Add API key");
  }
  function mount() {
    var h = document.querySelector(".nav-inner") || document.querySelector(".topbar");
    if (!h) {
      btn.style.position = "fixed"; btn.style.top = "14px"; btn.style.right = "16px"; btn.style.zIndex = "9998";
      document.body.appendChild(btn);
    } else {
      h.appendChild(btn);
    }
    refresh();
  }
  btn.onclick = function () {
    var ov = document.createElement("div"); ov.className = "kk-ov";
    var cur = localStorage.getItem(KEY) || "";
    var card = document.createElement("div"); card.className = "kk-card";
    card.innerHTML =
      "<h4>OpenAI API key</h4>" +
      "<p>Use your own key to run this demo. It is stored only in this browser and sent to your local server with each request.</p>" +
      '<input type="password" class="kk-in" placeholder="sk-..." autocomplete="off">' +
      '<div class="kk-row"><button class="kk-save" type="button">Save</button><button class="kk-clear" type="button">Clear</button></div>' +
      '<div class="kk-note">Stored in your browser (localStorage) on this device only. Never commit your key to the repo. If you leave this empty, the server uses its own .env key.</div>';
    ov.appendChild(card);
    card.querySelector(".kk-in").value = cur;
    ov.addEventListener("click", function (e) { if (e.target === ov) ov.remove(); });
    card.querySelector(".kk-save").onclick = function () {
      var v = card.querySelector(".kk-in").value.trim();
      if (v) localStorage.setItem(KEY, v); else localStorage.removeItem(KEY);
      refresh(); ov.remove();
    };
    card.querySelector(".kk-clear").onclick = function () { localStorage.removeItem(KEY); refresh(); ov.remove(); };
    document.body.appendChild(ov);
    card.querySelector(".kk-in").focus();
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
