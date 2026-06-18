// API client with bearer auth. 401 clears the session so the app falls back to login.
import { token, clearSession } from "./auth.js";

function authHeaders(extra = {}) {
  const t = token();
  return t ? { ...extra, Authorization: `Bearer ${t}` } : extra;
}

async function j(r) {
  if (r.status === 401) {
    clearSession();
    if (!location.pathname.startsWith("/login")) location.reload();
    throw new Error("unauthorized");
  }
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.status === 204 ? null : r.json();
}

export const api = {
  login: (email, password) =>
    fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }).then(async (r) => {
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || "Login failed");
      return r.json();
    }),
  me: () => fetch("/api/auth/me", { headers: authHeaders() }).then(j),

  summary: () => fetch("/api/summary", { headers: authHeaders() }).then(j),
  opportunities: ({ q = "", market = "All", vehicle = "All" } = {}) => {
    const p = new URLSearchParams();
    if (q) p.set("q", q);
    if (market !== "All") p.set("market", market);
    if (vehicle !== "All") p.set("vehicle", vehicle);
    return fetch(`/api/opportunities?${p}`, { headers: authHeaders() }).then(j);
  },
  opportunity: (id) => fetch(`/api/opportunities/${id}`, { headers: authHeaders() }).then(j),
  awards: () => fetch("/api/awards", { headers: authHeaders() }).then(j),
  awardTrend: () => fetch("/api/awards/trend", { headers: authHeaders() }).then(j),
  signals: () => fetch("/api/signals", { headers: authHeaders() }).then(j),
  board: () => fetch("/api/board", { headers: authHeaders() }).then(j),
  move: (opportunity_id, stage) =>
    fetch("/api/board/move", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ opportunity_id, stage }),
    }).then(j),
  workflows: () => fetch("/api/workflows", { headers: authHeaders() }).then(j),
  toggleWorkflow: (id, enabled) =>
    fetch(`/api/workflows/${id}`, {
      method: "PATCH",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ enabled }),
    }).then(j),
  agent: (question) =>
    fetch("/api/agent", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ question }),
    }).then(j),

  // ── Intelligence engine ──
  setVendor: (company, capabilities, text = "") =>
    fetch("/api/intel/vendor", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ company, capabilities, text }),
    }).then(j),
  targets: (company) =>
    fetch(`/api/intel/targets?company=${encodeURIComponent(company || "")}`, { headers: authHeaders() }).then(j),
  intelQuery: (company, body) =>
    fetch(`/api/intel/query?company=${encodeURIComponent(company || "")}`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(body),
    }).then(j),
};
