// polyglot-pathforge — frontend logic
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const SAMPLE_BRIEF = `I'm learning Spanish. Absolute beginner, never studied before. My native is English. I want to reach B1 conversation level in 12 months so I can chat with my in-laws when I visit Mexico. About 7 hours per week, conversational speaking style, taking a weekly italki lesson. I have a commute so podcasts work. No immersion access locally — no native speakers nearby.`;

let currentResult = null;
let currentBrief = "";
let currentMarkdown = "";

function escapeHtml(s) {
  if (s == null) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function setError(msg) {
  const box = $("#error-box");
  if (!msg) {
    box.classList.add("hidden");
    box.textContent = "";
  } else {
    box.classList.remove("hidden");
    box.textContent = msg;
  }
}

function verdictClass(v) {
  return `verdict ${v || ""}`;
}

async function runForge() {
  const brief = $("#brief-input").value.trim();
  if (!brief) {
    setError("Please describe your learner brief first.");
    return;
  }
  setError("");
  $("#run-btn").disabled = true;
  $("#run-btn").textContent = "Forging…";
  try {
    const res = await fetch("/api/roadmap", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({brief}),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      setError(data.error || "Failed to forge roadmap.");
      $("#result-card").classList.add("hidden");
      return;
    }
    currentBrief = brief;
    currentResult = data.result;
    currentMarkdown = data.markdown;
    renderResult(data.result, data.markdown);
    $("#result-section").classList.remove("hidden");
    $("#result-card").classList.remove("hidden");
    loadHistory();
  } catch (err) {
    setError("Network error: " + err.message);
  } finally {
    $("#run-btn").disabled = false;
    $("#run-btn").textContent = "Forge roadmap →";
  }
}

function renderResult(r, md) {
  const p = r.profile;
  const tm = p.target_meta;

  $("#result-subtitle").textContent =
    `${p.target_language} · ${p.current_level.toUpperCase()} → ${p.target_level.toUpperCase()} · ` +
    `${p.weekly_hours.toFixed(1)} h/wk × ${p.horizon_months} mo`;

  const pill = $("#verdict-pill");
  pill.className = verdictClass(r.readiness_verdict);
  pill.textContent = `${r.readiness_score}/100 · ${r.readiness_verdict.replace(/_/g, " ").toUpperCase()}`;

  // Profile grid
  const profileItems = [
    {k: "Target language", v: `${p.target_language} (${tm.family}, diff ${tm.difficulty}/4)`},
    {k: "Native", v: p.native_language || "unspecified"},
    {k: "Current level", v: `${p.current_level.toUpperCase()} (conf: ${p.level_confidence})`},
    {k: "Target level", v: p.target_level.toUpperCase()},
    {k: "Weekly hours", v: `${p.weekly_hours.toFixed(1)} h`},
    {k: "Horizon", v: `${p.horizon_months} months`},
    {k: "Goals", v: p.goals.length ? p.goals.join(", ") : "—"},
    {k: "Style", v: p.styles.length ? p.styles.join(", ") : "unspecified"},
    {k: "Constraints", v: p.constraints.length ? p.constraints.join(", ") : "none"},
    {k: "Motivation", v: p.motivation.label},
    {k: "Prior exposure", v: p.prior_exposure.length ? p.prior_exposure.join(", ") : "none"},
    {k: "Family boost", v: p.family_known.length ? p.family_known.join(", ") : "—"},
  ];
  $("#profile-grid").innerHTML = profileItems
    .map(it => `<div class="profile-card"><span class="k">${escapeHtml(it.k)}</span><span class="v">${escapeHtml(it.v)}</span></div>`)
    .join("");

  // Feasibility
  const feasEl = $("#feasibility-content");
  feasEl.className = `feasibility-content ${r.feasibility}`;
  feasEl.innerHTML =
    `<strong>${r.feasibility.toUpperCase()}</strong> — ` +
    `~${r.weeks_needed} weeks needed vs ~${r.weeks_available} weeks available ` +
    `(${(r.weeks_needed / r.weeks_available * 100).toFixed(0)}% utilization)`;

  // Score
  $("#score-display").innerHTML =
    `${r.readiness_score}<span class="of">/100</span>`;

  const axesContainer = $("#axes-bars");
  axesContainer.innerHTML = Object.entries(r.readiness_axes).map(([k, v]) => {
    const label = k.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    return `
      <div class="axis-row">
        <div>${escapeHtml(label)}</div>
        <div class="axis-bar"><div class="axis-fill" style="width:${v}%"></div></div>
        <div>${v}</div>
      </div>`;
  }).join("");

  // Phases
  const phasesList = $("#phases-list");
  phasesList.innerHTML = r.phases.map((ph, i) => `
    <li class="phase-item">
      <div class="head">
        <h4 class="title">${i + 1}. ${escapeHtml(ph.name)}</h4>
        <span class="meta">${ph.est_weeks} weeks · ~${ph.est_hours} h · vocab target ${ph.vocab_target}</span>
      </div>
      <div class="focus">${escapeHtml(ph.focus)}</div>
      <ul>${ph.grammar.map(g => `<li>${escapeHtml(g)}</li>`).join("")}</ul>
      <div class="milestone"><strong>Milestone:</strong> ${escapeHtml(ph.milestone)}</div>
    </li>
  `).join("");

  // Hour split
  const split = r.hour_split.distribution;
  const splitEl = $("#split-content");
  splitEl.innerHTML = Object.entries(split).map(([k, mins]) => `
    <div class="split-card">
      <div class="k">${escapeHtml(k)}</div>
      <div class="v">${mins} min</div>
    </div>
  `).join("");

  // Immersion tactics
  const immersionEl = $("#immersion-list");
  immersionEl.innerHTML = r.immersion.map(t => `
    <li class="immersion-item priority-${t.priority}">
      <div class="head">
        <span>${escapeHtml(t.name)}</span>
        <span class="minutes">${t.weekly_minutes} min/wk</span>
      </div>
      <div class="desc">${escapeHtml(t.description)}</div>
    </li>
  `).join("");

  // SRS table
  const srsTable = $("#srs-table");
  srsTable.innerHTML = `
    <thead>
      <tr><th>Wave</th><th>Interval</th><th>Share</th><th>Note</th></tr>
    </thead>
    <tbody>
      ${r.vocab_waves.map(w => `
        <tr>
          <td>${escapeHtml(w.name)}</td>
          <td>${w.interval_days ? `every ${w.interval_days}d` : "—"}</td>
          <td>${w.interval_days ? `${Math.round(w.review_share * 100)}%` : "100%"}</td>
          <td>${escapeHtml(w.note)}</td>
        </tr>
      `).join("")}
    </tbody>
  `;

  // Cultural landmarks
  const landmarksEl = $("#landmarks-list");
  if (r.cultural_landmarks && r.cultural_landmarks.length) {
    landmarksEl.innerHTML = r.cultural_landmarks.map(c => `
      <li class="landmark-item">
        <span class="landmark-type">${escapeHtml(c.type)}</span>
        <span>${escapeHtml(c.item)}</span>
      </li>
    `).join("");
  } else {
    landmarksEl.innerHTML = `<li class="landmark-item"><span>No cultural landmarks curated for this family yet — explore the literature / film scene of the country.</span></li>`;
  }

  // Risk flags
  const flagsEl = $("#flags-list");
  if (r.risk_flags.length) {
    flagsEl.innerHTML = r.risk_flags.map(f => `
      <li class="flag-item severity-${f.severity}">
        <span class="flag-sev ${f.severity}">${f.severity}</span>
        <span>${escapeHtml(f.label)}</span>
      </li>
    `).join("");
  } else {
    flagsEl.innerHTML = `<li class="flag-item"><span class="flag-sev low">OK</span><span>No major risks detected — the plan looks solid.</span></li>`;
  }

  // Markdown preview
  $("#markdown-preview").textContent = md;
}

async function saveSession() {
  if (!currentResult) return;
  const rating = $("#rating-select").value || null;
  const notes = $("#notes-input").value.trim();
  try {
    const res = await fetch("/api/sessions", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({brief: currentBrief, result: currentResult, rating, notes}),
    });
    const data = await res.json();
    if (data.error) {
      setError(data.error);
    } else {
      setError("");
      loadHistory();
      flashSave("Session saved ✓");
    }
  } catch (err) {
    setError("Save failed: " + err.message);
  }
}

function flashSave(msg) {
  const btn = $("#save-btn");
  const orig = btn.textContent;
  btn.textContent = msg;
  setTimeout(() => { btn.textContent = orig; }, 1500);
}

async function loadHistory() {
  try {
    const res = await fetch("/api/sessions");
    const data = await res.json();
    const list = $("#history-list");
    if (!data.sessions.length) {
      list.innerHTML = `<div style="color: var(--text-dim); font-size: 13px;">No saved sessions yet.</div>`;
      return;
    }
    list.innerHTML = data.sessions.map(s => `
      <div class="history-row">
        <div class="info">
          <div class="lang">${escapeHtml(s.target_language || "?")} · ${escapeHtml(s.current_level || "?")} → ${escapeHtml(s.target_level || "?")}</div>
          <div class="meta">${escapeHtml(new Date(s.created_at).toLocaleString())} · ${escapeHtml(s.feasibility || "?")} · ${escapeHtml(s.verdict || "?")}${s.rating ? " · " + s.rating + "★" : ""}${s.notes ? " · " + escapeHtml(s.notes) : ""}</div>
        </div>
        <div class="score">${s.readiness_score ?? "—"}</div>
        <div class="actions">
          <button class="load-session" data-id="${s.id}">Load</button>
          <button class="delete-session" data-id="${s.id}">Delete</button>
        </div>
      </div>
    `).join("");
    $$(".load-session").forEach(btn => {
      btn.addEventListener("click", () => loadSession(btn.dataset.id));
    });
    $$(".delete-session").forEach(btn => {
      btn.addEventListener("click", () => deleteSession(btn.dataset.id));
    });
  } catch (err) {
    // silently fail
  }
}

async function loadSession(id) {
  try {
    const res = await fetch(`/api/sessions/${id}`);
    const data = await res.json();
    if (data.error) {
      setError(data.error);
      return;
    }
    currentBrief = data.brief;
    currentResult = data.result;
    $("#brief-input").value = data.brief;
    $("#rating-select").value = data.rating || "";
    $("#notes-input").value = data.notes || "";
    // Re-render — but we need markdown. Re-derive from stored result if missing.
    let md = "";
    try {
      const rerun = await fetch("/api/roadmap", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({brief: data.brief}),
      });
      const rd = await rerun.json();
      md = rd.markdown || "";
    } catch (e) {
      md = "";
    }
    currentMarkdown = md;
    renderResult(data.result, md);
    $("#result-section").classList.remove("hidden");
    $("#result-card").classList.remove("hidden");
  } catch (err) {
    setError("Load failed: " + err.message);
  }
}

async function deleteSession(id) {
  if (!confirm("Delete this session?")) return;
  await fetch(`/api/sessions/${id}`, {method: "DELETE"});
  loadHistory();
}

function downloadFile(content, filename, type) {
  const blob = new Blob([content], {type});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

$("#run-btn").addEventListener("click", runForge);
$("#sample-btn").addEventListener("click", () => {
  $("#brief-input").value = SAMPLE_BRIEF;
});
$("#clear-btn").addEventListener("click", () => {
  $("#brief-input").value = "";
  $("#result-card").classList.add("hidden");
  setError("");
});
$("#save-btn").addEventListener("click", saveSession);
$("#download-md").addEventListener("click", () => {
  if (!currentMarkdown) return;
  downloadFile(currentMarkdown, `polyglot-pathforge-${Date.now()}.md`, "text/markdown");
});
$("#download-json").addEventListener("click", () => {
  if (!currentResult) return;
  downloadFile(JSON.stringify(currentResult, null, 2),
    `polyglot-pathforge-${Date.now()}.json`, "application/json");
});
$("#copy-md").addEventListener("click", () => {
  if (!currentMarkdown) return;
  navigator.clipboard.writeText(currentMarkdown).then(() => {
    const btn = $("#copy-md");
    const orig = btn.textContent;
    btn.textContent = "Copied ✓";
    setTimeout(() => btn.textContent = orig, 1200);
  });
});

document.addEventListener("DOMContentLoaded", loadHistory);