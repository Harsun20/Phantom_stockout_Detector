/* Phantom Stock Detector frontend.
   Backend base URL can be changed here if Flask runs on another host/port. */
const API_BASE = "";
const API = {
  health: "/api/health",
  summary: "/api/summary",
  recovery: "/api/recovery-estimate",
  dates: "/api/dates",
  stores: "/api/stores",
  alerts: "/api/alerts",
  history: "/api/history",
  run: "/api/run-pipeline",
  download: "/download/daily-alerts"
};

const state = {
  summary: null, recovery: null, dates: [], stores: [], alerts: [], history: [],
  selectedDate: "", selectedStore: "", includeHistory: false, chartTrend: null, chartRisk: null,
  currentPage: "overview"
};
const $ = (id) => document.getElementById(id);
const numberFmt = new Intl.NumberFormat("en-IN");
const moneyFmt = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) }
  });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message = payload && payload.detail ? payload.detail : (payload && payload.error ? payload.error : `Request failed (${response.status})`);
    throw new Error(message);
  }
  return payload;
}
function fmt(value) {
  if (value === null || value === undefined || value === "" || Number.isNaN(Number(value))) return "—";
  return numberFmt.format(Number(value));
}
function fmtScore(value) { return value === null || value === undefined ? "—" : `${Math.round(Number(value))}/100`; }
function safe(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[ch]));
}
function dateOnly(value) { return String(value || "").slice(0, 10); }
function showGlobal(message, type = "info") {
  const el = $("globalMessage");
  el.className = "rounded-2xl border px-4 py-3 text-sm";
  const styles = {
    info: "border-blue-200 bg-blue-50 text-blue-900 dark:border-blue-300/20 dark:bg-blue-300/10 dark:text-blue-200",
    success: "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-300/20 dark:bg-emerald-300/10 dark:text-emerald-200",
    error: "border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-300/20 dark:bg-rose-300/10 dark:text-rose-200"
  };
  el.classList.add(...styles[type].split(" "));
  el.textContent = message;
  el.classList.remove("hidden");
}
function hideGlobal() { $("globalMessage").classList.add("hidden"); }
function setConnection(ok, detail = "") {
  $("connectionDot").className = `h-2 w-2 rounded-full ${ok ? "bg-emerald-400" : "bg-rose-400"}`;
  $("connectionText").textContent = ok ? "API connected" : "API unavailable";
  $("connectionDetail").textContent = detail || (ok ? "Local Flask service is responding." : "Start app.py and check the API URL.");
}
function setText(id, value) { $(id).textContent = value; }

async function checkHealth() {
  try {
    const data = await apiFetch(API.health);
    setConnection(true, `${fmt(data.daily_alert_rows)} alerts · ${fmt(data.history_rows)} history rows`);
    return true;
  } catch (error) {
    setConnection(false, error.message);
    return false;
  }
}
async function loadBaseData() {
  hideGlobal();
  try {
    const [summary, recovery, dates, health] = await Promise.all([
      apiFetch(API.summary), apiFetch(API.recovery), apiFetch(API.dates), checkHealth()
    ]);
    state.summary = summary;
    state.recovery = recovery;
    state.dates = Array.isArray(dates) ? dates : [];
    state.selectedDate = state.selectedDate || state.dates[state.dates.length - 1] || "";
    renderMetrics();
    populateDateFilter();
    await loadStores();
    await loadAlerts();
    await loadHistory();
    renderCharts();
    renderOverviewQueue();
    $("lastUpdated").textContent = `Updated ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    if (!health) showGlobal("Dashboard data loaded, but the health check reported a connection issue.", "error");
  } catch (error) {
    setConnection(false, error.message);
    showGlobal(`Could not load dashboard data: ${error.message}. Make sure the pipeline has run and Flask is running at ${API_BASE}.`, "error");
    renderEmptyStates();
  }
}
function renderMetrics() {
  const s = state.summary || {};
  const r = state.recovery || {};
  setText("kpiScanned", fmt(s.merged_row_count));
  setText("kpiAlerts", fmt(s.total_top_20_alert_count));
  setText("kpiCandidateCount", fmt(s.total_candidate_count));
  setText("kpiUnits", fmt(r.expected_lost_units_proxy));
  if (r.potential_revenue_at_risk === null || r.potential_revenue_at_risk === undefined) {
    setText("kpiRevenue", "N/A");
    setText("revenueFoot", "Add selling-price data to estimate rupee value");
  } else {
    setText("kpiRevenue", moneyFmt.format(Number(r.potential_revenue_at_risk)));
    setText("revenueFoot", "Scenario estimate · not measured recovery");
  }
  setText("navAlertCount", fmt(s.total_top_20_alert_count));
}
function populateDateFilter() {
  const select = $("dateFilter");
  const old = state.selectedDate;
  select.innerHTML = '<option value="">Latest available</option>' + state.dates.slice().reverse().map(d => `<option value="${safe(d)}">${safe(d)}</option>`).join("");
  select.value = old || "";
}
async function loadStores() {
  try {
    const query = state.selectedDate ? `?date=${encodeURIComponent(state.selectedDate)}` : "";
    const stores = await apiFetch(`${API.stores}${query}`);
    state.stores = Array.isArray(stores) ? stores : [];
    const select = $("storeFilter");
    const current = state.selectedStore;
    select.innerHTML = '<option value="">All stores</option>' + state.stores.map(s => `<option value="${safe(s)}">${safe(s)}</option>`).join("");
    if (state.stores.includes(current)) select.value = current;
    else { state.selectedStore = ""; select.value = ""; }
  } catch (error) { console.warn("Store list unavailable:", error); }
}
async function loadAlerts() {
  const chosenDate = state.selectedDate || state.dates[state.dates.length - 1] || "";
  if (!chosenDate) { state.alerts = []; renderAlertsTable(); return; }
  try {
    const stores = state.selectedStore ? [state.selectedStore] : state.stores;
    const requests = stores.map(store => apiFetch(`${API.alerts}?date=${encodeURIComponent(chosenDate)}&store_id=${encodeURIComponent(store)}`));
    const arrays = await Promise.all(requests);
    state.alerts = arrays.flat().map(a => ({ ...a, date: dateOnly(a.date) }));
    state.alerts.sort((a,b) => Number(a.rank_in_store || 999) - Number(b.rank_in_store || 999) || Number(b.phantom_score || 0) - Number(a.phantom_score || 0));
    renderAlertsTable();
  } catch (error) {
    state.alerts = [];
    renderAlertsTable();
    showGlobal(`Could not load alerts: ${error.message}`, "error");
  }
}
async function loadHistory() {
  if (!state.includeHistory) { state.history = []; return; }
  try {
    // The backend history endpoint needs a specific store + SKU. Fetch one series for each
    // SKU represented by current alerts, then deduplicate the resulting daily history.
    const keys = [...new Set(state.alerts.map(a => `${a.store_id}::${a.sku_id}`))].slice(0, 100);
    const arrays = await Promise.all(keys.map(key => {
      const [store, sku] = key.split("::");
      return apiFetch(`${API.history}?store_id=${encodeURIComponent(store)}&sku_id=${encodeURIComponent(sku)}`);
    }));
    state.history = arrays.flat();
  } catch (error) {
    console.warn("History endpoint unavailable:", error);
    state.history = [];
  }
}
function filteredAlerts() {
  let rows = state.alerts.slice();
  const search = $("searchInput").value.trim().toLowerCase();
  const risk = $("riskFilter").value;
  if (search) rows = rows.filter(row => [row.sku_id,row.sku_name,row.category,row.store_id,row.reason,row.recommended_action,row.alert_type].some(v => String(v ?? "").toLowerCase().includes(search)));
  if (risk) rows = rows.filter(row => {
    const score = Number(row.phantom_score || 0);
    return risk === "high" ? score >= 70 : risk === "medium" ? score >= 45 && score < 70 : score < 45;
  });
  return rows;
}
function scoreClass(score) {
  const value = Number(score || 0);
  return value >= 70 ? "score-high" : value >= 45 ? "score-medium" : "score-low";
}
function alertLabel(type) {
  if (type === "likely_phantom_stockout") return "Likely phantom";
  if (type === "possible_wrong_shelf") return "Possible wrong shelf";
  return "Monitor";
}
function tableMarkup(rows, compact = false) {
  if (!rows.length) return '<div class="empty-state"><div class="mb-2 text-2xl">⌁</div>No alerts match these filters.</div>';
  return `<table class="data-table"><thead><tr><th>Rank</th><th>Item / SKU</th><th>Store</th><th>Risk score</th><th>On hand</th><th>Zero sales</th>${compact ? "" : "<th>Alert type</th><th>Reason</th><th>Recommended action</th>"}</tr></thead><tbody>${rows.map(row => `<tr>
    <td><span class="font-extrabold text-slate-400">#${safe(row.rank_in_store ?? "—")}</span></td>
    <td><div class="font-extrabold">${safe(row.sku_name || row.sku_id || "Unknown item")}</div><div class="mt-1 text-[10px] text-slate-400">${safe(row.sku_id || "")}${row.category ? " · " + safe(row.category) : ""}</div></td>
    <td><span class="rounded-lg bg-slate-100 px-2 py-1 text-[10px] font-bold dark:bg-white/5">${safe(row.store_id || "—")}</span></td>
    <td><span class="score-pill ${scoreClass(row.phantom_score)}">${safe(fmtScore(row.phantom_score))}</span></td>
    <td class="font-bold">${safe(fmt(row.on_hand))}</td>
    <td><span class="font-bold">${safe(fmt(row.zero_sales_streak))}d</span></td>
    ${compact ? "" : `<td><span class="text-[10px] font-bold ${row.alert_type === "likely_phantom_stockout" ? "text-rose-600 dark:text-rose-300" : "text-amber-600 dark:text-amber-300"}">${safe(alertLabel(row.alert_type))}</span></td><td class="reason-cell">${safe(row.reason || "No reason provided.")}</td><td class="action-cell">${safe(row.recommended_action || "Physically verify item")}</td>`}
  </tr>`).join("")}</tbody></table>`;
}
function renderAlertsTable() {
  const rows = filteredAlerts();
  $("tableResultCount").textContent = `${rows.length} alert${rows.length === 1 ? "" : "s"} shown`;
  $("tableDateLabel").textContent = state.selectedDate ? `Date: ${state.selectedDate}` : "";
  $("alertsTableWrap").innerHTML = tableMarkup(rows, false);
}
function renderOverviewQueue() {
  const rows = state.alerts.slice().sort((a,b) => Number(b.phantom_score || 0) - Number(a.phantom_score || 0)).slice(0, 5);
  $("overviewQueue").innerHTML = tableMarkup(rows, true);
}
function renderCharts() {
  if (typeof Chart === "undefined") return;
  const history = state.history.length ? state.history : [];
  const currentAlerts = state.alerts;
  const trendLabels = history.length ? [...new Set(history.map(x => dateOnly(x.date)))].sort().slice(-30) : state.dates.slice(-14);
  const trendValues = trendLabels.map(d => history.length ? history.filter(x => dateOnly(x.date) === d && (x.candidate === true || String(x.candidate).toLowerCase() === "true")).length : 0);
  if (state.chartTrend) state.chartTrend.destroy();
  const ctx = $("trendChart").getContext("2d");
  state.chartTrend = new Chart(ctx, {
    type: "line",
    data: { labels: trendLabels, datasets: [{ label: history.length ? "Candidate records" : "Candidate records (history not loaded)", data: trendValues, borderColor: "#10b981", backgroundColor: "rgba(16,185,129,.12)", fill: true, tension: .35, borderWidth: 2, pointRadius: 2 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: {
      x: { grid: { display: false }, ticks: { color: chartText(), maxTicksLimit: 7, maxRotation: 0 } },
      y: { beginAtZero: true, grid: { color: chartGrid() }, ticks: { color: chartText(), precision: 0 } }
    }}
  });
  const bands = [
    { label: "High risk · 70+", count: currentAlerts.filter(x => Number(x.phantom_score) >= 70).length, color: "#f43f5e" },
    { label: "Medium · 45–69", count: currentAlerts.filter(x => Number(x.phantom_score) >= 45 && Number(x.phantom_score) < 70).length, color: "#f59e0b" },
    { label: "Low · below 45", count: currentAlerts.filter(x => Number(x.phantom_score) < 45).length, color: "#10b981" }
  ];
  if (state.chartRisk) state.chartRisk.destroy();
  state.chartRisk = new Chart($("riskChart").getContext("2d"), {
    type: "doughnut",
    data: { labels: bands.map(x => x.label), datasets: [{ data: bands.map(x => x.count), backgroundColor: bands.map(x => x.color), borderWidth: 0, hoverOffset: 5 }] },
    options: { cutout: "74%", plugins: { legend: { display: false } }, maintainAspectRatio: true }
  });
  $("riskLegend").innerHTML = bands.map(b => `<div class="flex items-center justify-between gap-3 text-xs"><div class="flex items-center gap-2"><span class="h-2.5 w-2.5 rounded-full" style="background:${b.color}"></span><span class="text-slate-500 dark:text-slate-300">${safe(b.label)}</span></div><span class="font-extrabold">${fmt(b.count)}</span></div>`).join("");
}
function chartText() { return document.documentElement.classList.contains("dark") ? "#94a3b8" : "#64748b"; }
function chartGrid() { return document.documentElement.classList.contains("dark") ? "rgba(255,255,255,.08)" : "rgba(148,163,184,.18)"; }
function renderEmptyStates() {
  $("overviewQueue").innerHTML = '<div class="empty-state">No data yet. Run the backend pipeline, then refresh.</div>';
  $("alertsTableWrap").innerHTML = '<div class="empty-state">Connect to Flask to load alerts.</div>';
  ["kpiScanned","kpiAlerts","kpiCandidateCount","kpiUnits","kpiRevenue"].forEach(id => setText(id, "—"));
}
function setPage(page) {
  state.currentPage = page;
  document.querySelectorAll(".page-section").forEach(section => section.classList.toggle("hidden", section.id !== `section-${page}`));
  document.querySelectorAll(".nav-link").forEach(link => link.classList.toggle("active", link.dataset.section === page));
  const titles = { overview: "Operations overview", alerts: "Alert center", pipeline: "Pipeline control" };
  setText("pageTitle", titles[page] || titles.overview);
  if (window.innerWidth < 1024) closeSidebar();
  if (page === "alerts") renderAlertsTable();
  if (page === "overview") renderOverviewQueue();
}
function openSidebar() {
  $("sidebar").classList.remove("-translate-x-full");
  $("mobileOverlay").classList.remove("hidden");
}
function closeSidebar() {
  $("sidebar").classList.add("-translate-x-full");
  $("mobileOverlay").classList.add("hidden");
}
function toggleTheme() {
  document.documentElement.classList.toggle("dark");
  const isDark = document.documentElement.classList.contains("dark");
  try { localStorage.setItem("phantom-theme", isDark ? "dark" : "light"); } catch (_) {}
  $("themeToggle").textContent = isDark ? "☾" : "☼";
  renderCharts();
}
async function refreshAll() {
  await loadBaseData();
  if (state.currentPage === "alerts") renderAlertsTable();
}
async function runPipeline() {
  const button = $("runPipeline");
  const overviewButton = $("overviewRun");
  const feedback = $("pipelineFeedback");
  [button, overviewButton].forEach(b => { b.disabled = true; if (b) b.classList.add("opacity-60"); });
  $("pipelineState").textContent = "Pipeline is running…";
  $("pipelineBadge").className = "status-pill neutral";
  $("pipelineBadge").textContent = "RUNNING";
  $("pipelineProgress").style.width = "65%";
  $("pipelineLog").textContent = `[${new Date().toLocaleTimeString()}] Sending POST ${API.run}\n`;
  feedback.className = "mt-4 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 dark:border-blue-300/20 dark:bg-blue-300/10 dark:text-blue-200";
  feedback.textContent = "Running detection pipeline. This can take a few seconds…";
  feedback.classList.remove("hidden");
  try {
    const result = await apiFetch(API.run, { method: "POST", body: JSON.stringify({}) });
    $("pipelineProgress").style.width = "100%";
    $("pipelineBadge").className = "status-pill success";
    $("pipelineBadge").textContent = "COMPLETED";
    $("pipelineState").textContent = `Completed at ${new Date().toLocaleTimeString()}`;
    $("pipelineLog").textContent += `${result.message || "Pipeline completed."}\n${result.stdout || ""}${result.stderr ? "\nWarnings/errors:\n" + result.stderr : ""}`;
    feedback.className = "mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 dark:border-emerald-300/20 dark:bg-emerald-300/10 dark:text-emerald-200";
    feedback.textContent = "Pipeline completed. Refreshing dashboard data…";
    await refreshAll();
    feedback.textContent = "Pipeline completed and dashboard data refreshed.";
    showGlobal("Detection pipeline completed successfully.", "success");
  } catch (error) {
    $("pipelineProgress").style.width = "0%";
    $("pipelineBadge").className = "status-pill error";
    $("pipelineBadge").textContent = "FAILED";
    $("pipelineState").textContent = "Run failed";
    $("pipelineLog").textContent += `\nERROR: ${error.message}\n`;
    feedback.className = "mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900 dark:border-rose-300/20 dark:bg-rose-300/10 dark:text-rose-200";
    feedback.textContent = `Could not run pipeline: ${error.message}. Ensure the POST route is added to app.py (see backend_integration/README.md).`;
    feedback.classList.remove("hidden");
    showGlobal("Pipeline action failed. Check the pipeline log and backend integration instructions.", "error");
  } finally {
    [button, overviewButton].forEach(b => { b.disabled = false; b.classList.remove("opacity-60"); });
  }
}
function setupEvents() {
  document.querySelectorAll(".nav-link").forEach(link => link.addEventListener("click", e => { e.preventDefault(); setPage(link.dataset.section); }));
  document.querySelectorAll("[data-go]").forEach(button => button.addEventListener("click", () => setPage(button.dataset.go)));
  $("openMenu").addEventListener("click", openSidebar);
  $("closeMenu").addEventListener("click", closeSidebar);
  $("mobileOverlay").addEventListener("click", closeSidebar);
  $("themeToggle").addEventListener("click", toggleTheme);
  $("headerRefresh").addEventListener("click", refreshAll);
  $("retryConnection").addEventListener("click", checkHealth);
  $("alertsRefresh").addEventListener("click", refreshAll);
  $("refreshAfterRun").addEventListener("click", refreshAll);
  $("overviewRun").addEventListener("click", () => { setPage("pipeline"); runPipeline(); });
  $("runPipeline").addEventListener("click", runPipeline);
  $("searchInput").addEventListener("input", renderAlertsTable);
  $("riskFilter").addEventListener("change", renderAlertsTable);
  $("dateFilter").addEventListener("change", async e => {
    state.selectedDate = e.target.value || state.dates[state.dates.length - 1] || "";
    state.selectedStore = "";
    await loadStores(); await loadAlerts(); await loadHistory(); renderCharts(); renderOverviewQueue();
  });
  $("storeFilter").addEventListener("change", async e => {
    state.selectedStore = e.target.value;
    await loadAlerts(); await loadHistory(); renderCharts(); renderOverviewQueue();
  });
  $("showMonitor").addEventListener("change", async e => {
    state.includeHistory = e.target.checked;
    await loadHistory(); renderCharts();
  });
  $("downloadLink").href = `${API_BASE}${API.download}`;
  document.querySelectorAll('a[href^="http://127.0.0.1:5000/download"]').forEach(a => a.href = `${API_BASE}${API.download}`);
}
function initializeTheme() {
  let theme = "light";
  try { theme = localStorage.getItem("phantom-theme") || "light"; } catch (_) {}
  if (theme === "dark") document.documentElement.classList.add("dark");
  $("themeToggle").textContent = theme === "dark" ? "☾" : "☼";
}
document.addEventListener("DOMContentLoaded", async () => {
  initializeTheme();
  setupEvents();
  await refreshAll();
});
