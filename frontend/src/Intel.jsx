import React, { useState } from "react";
import { Brain, Sparkles, Crosshair, Plus, X, Play } from "lucide-react";
import { api } from "./api.js";

const AGENCY = { dod: "DoD", dhs: "DHS", va: "VA", treasury: "Treasury", hhs: "HHS" };
const fmtUSD = (n) => (n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : `$${(n / 1e3).toFixed(0)}k`);

function ScoreBar({ value }) {
  const col = value >= 80 ? "var(--forest-hi)" : value >= 60 ? "var(--amber)" : "var(--moss)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 9, minWidth: 132 }}>
      <div style={{ flex: 1, height: 7, background: "var(--bone-2)", borderRadius: 5, overflow: "hidden" }}>
        <div style={{ width: `${value}%`, height: "100%", background: col }} />
      </div>
      <span className="ch-mono" style={{ fontWeight: 600, color: "var(--ink)", width: 38, textAlign: "right" }}>{value}</span>
    </div>
  );
}

function Factors({ factors }) {
  const order = ["funding", "dme_growth", "modernization", "contract_expiration",
    "hiring_growth", "technology_alignment", "competitive_position", "mission_relevance"];
  const label = {
    funding: "Funding", dme_growth: "DME growth", modernization: "Modernisation",
    contract_expiration: "Contract expiry", hiring_growth: "Hiring", technology_alignment: "Tech fit",
    competitive_position: "Open field", mission_relevance: "Mission",
  };
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: "6px 16px", marginTop: 4 }}>
      {order.map((k) => (
        <div key={k} style={{ fontSize: 11 }}>
          <span style={{ color: "var(--moss)" }}>{label[k]}</span>
          <div className="ch-mono" style={{ color: "var(--ink)", fontWeight: 600 }}>{Math.round((factors[k] ?? 0) * 100)}</div>
        </div>
      ))}
    </div>
  );
}

export default function Intel() {
  const [company, setCompany] = useState("ArangoDB");
  const [caps, setCaps] = useState(["graph database", "knowledge graph", "entity resolution", "data fabric", "rag", "link analysis"]);
  const [capInput, setCapInput] = useState("");
  const [onto, setOnto] = useState(null);
  const [rows, setRows] = useState([]);
  const [open, setOpen] = useState(null);
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState({ min_dme: 10000000, require_technologies: ["graph"], expiry_months: 24, no_dominant_incumbent: true });
  const [queryRows, setQueryRows] = useState(null);

  const addCap = () => { const c = capInput.trim(); if (c && !caps.includes(c)) setCaps([...caps, c]); setCapInput(""); };

  const analyse = async () => {
    setBusy(true);
    try {
      const r = await api.setVendor(company, caps);
      setOnto(r.ontology);
      const t = await api.targets(company);
      setRows(t.programs);
      setQueryRows(null);
    } finally { setBusy(false); }
  };

  const runQuery = async () => {
    const r = await api.intelQuery(company, q);
    setQueryRows(r.programs);
  };

  return (
    <div className="ch-page">
      <div className="ch-grid" style={{ gridTemplateColumns: "360px 1fr", alignItems: "start" }}>
        {/* Vendor profile */}
        <div className="ch-panel">
          <div className="ch-panel-h"><Brain size={17} className="ic" /><h3>Vendor profile</h3></div>
          <div style={{ padding: 18 }}>
            <label className="ch-field"><span>Company</span>
              <input value={company} onChange={(e) => setCompany(e.target.value)} />
            </label>
            <div style={{ fontSize: 11, letterSpacing: ".6px", textTransform: "uppercase", color: "var(--moss)", margin: "4px 0 7px" }}>Capabilities</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
              {caps.map((c) => (
                <span key={c} className="ch-chip" style={{ paddingRight: 4 }}>{c}
                  <button onClick={() => setCaps(caps.filter((x) => x !== c))}
                          style={{ border: 0, background: "none", cursor: "pointer", color: "var(--moss)", display: "inline-flex" }}><X size={11} /></button>
                </span>
              ))}
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <input value={capInput} placeholder="add capability…" onChange={(e) => setCapInput(e.target.value)}
                     onKeyDown={(e) => e.key === "Enter" && addCap()}
                     style={{ flex: 1, border: "1px solid var(--line)", borderRadius: 8, padding: "8px 11px", fontFamily: "inherit", fontSize: 13, background: "var(--bone)" }} />
              <button className="ch-btn ghost sm" onClick={addCap}><Plus size={14} /></button>
            </div>
            <button className="ch-btn amber" style={{ width: "100%", justifyContent: "center", marginTop: 14 }} onClick={analyse} disabled={busy}>
              <Sparkles size={15} /> {busy ? "Building ontology…" : "Build ontology & score"}
            </button>
            {onto && (
              <div style={{ marginTop: 16 }}>
                <div className="ch-mono" style={{ fontSize: 10.5, color: "var(--moss)", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 7 }}>
                  Ontology · {onto.provider}
                </div>
                <div style={{ fontSize: 12, color: "var(--moss)", marginBottom: 4 }}>Expanded keywords</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 12 }}>
                  {onto.expanded_keywords.slice(0, 12).map((k) => <span key={k} className="ch-chip" style={{ fontSize: 10.5 }}>{k}</span>)}
                </div>
                <div style={{ fontSize: 12, color: "var(--moss)", marginBottom: 4 }}>Mission alignment</div>
                {onto.mission_alignment.map((a) => (
                  <div key={a.mission} style={{ fontSize: 12, marginBottom: 3 }}>
                    <b style={{ color: "var(--ink)" }}>{a.mission}</b> <span style={{ color: "var(--moss)" }}>— {a.rationale}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Targets + query */}
        <div>
          <div className="ch-panel" style={{ marginBottom: 16 }}>
            <div className="ch-panel-h"><Crosshair size={17} className="ic" /><h3>Opportunity targets</h3>
              <span className="right">{rows.length ? `${rows.length} programs, scored for ${company}` : "build an ontology to score"}</span>
            </div>
            {rows.length === 0 ? (
              <div className="ch-empty"><Crosshair size={32} className="ic" /><p>No targets yet.</p><span>Enter a vendor profile and build the ontology.</span></div>
            ) : (
              <table className="ch-table">
                <thead><tr><th>Program</th><th>Agency</th><th>Incumbent</th><th>Opportunity</th></tr></thead>
                <tbody>
                  {rows.map((r) => (
                    <React.Fragment key={r.program}>
                      <tr className="row" onClick={() => setOpen(open === r.program ? null : r.program)}>
                        <td><div className="title">{r.name}</div><div className="agency ch-mono">{r.peo}</div></td>
                        <td><span className="ch-chip">{AGENCY[r.agency] || r.agency}</span></td>
                        <td style={{ fontSize: 12.5, color: r.incumbent ? "var(--slate)" : "var(--forest-hi)" }}>{r.incumbent || "open field"}</td>
                        <td><ScoreBar value={r.score} /></td>
                      </tr>
                      {open === r.program && (
                        <tr><td colSpan={4} style={{ background: "var(--bone)", paddingTop: 4 }}>
                          <div style={{ fontSize: 10.5, letterSpacing: ".6px", textTransform: "uppercase", color: "var(--moss)" }}>Score breakdown (0–100 per factor)</div>
                          <Factors factors={r.factors} />
                        </td></tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="ch-panel">
            <div className="ch-panel-h"><Play size={16} className="ic" /><h3>Where should we spend the next dollar?</h3></div>
            <div style={{ padding: 18 }}>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "center", fontSize: 13 }}>
                <label>DME &gt; <select className="ch-sel" value={q.min_dme} onChange={(e) => setQ({ ...q, min_dme: +e.target.value })}>
                  <option value={0}>$0</option><option value={10000000}>$10M</option><option value={20000000}>$20M</option></select></label>
                <label>expiry within <select className="ch-sel" value={q.expiry_months ?? ""} onChange={(e) => setQ({ ...q, expiry_months: e.target.value ? +e.target.value : null })}>
                  <option value="">any</option><option value={12}>12mo</option><option value={24}>24mo</option></select></label>
                <label style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <input type="checkbox" checked={q.no_dominant_incumbent} onChange={(e) => setQ({ ...q, no_dominant_incumbent: e.target.checked })} /> no dominant incumbent</label>
                <label style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <input type="checkbox" checked={q.require_technologies.includes("graph")} onChange={(e) => setQ({ ...q, require_technologies: e.target.checked ? ["graph"] : [] })} /> requires graph tech</label>
                <button className="ch-btn sm" onClick={runQuery}><Play size={13} /> Run</button>
              </div>
              {queryRows && (
                <div style={{ marginTop: 14 }}>
                  <div style={{ fontSize: 12, color: "var(--moss)", marginBottom: 8 }}>{queryRows.length} program(s) match, ranked by likelihood to buy:</div>
                  {queryRows.map((r) => (
                    <div key={r.program} style={{ display: "flex", alignItems: "center", gap: 12, padding: "9px 0", borderBottom: "1px solid var(--bone-2)" }}>
                      <span className="ch-mono" style={{ fontWeight: 600, color: "var(--forest-hi)", width: 42 }}>{r.score}</span>
                      <div style={{ flex: 1 }}><b style={{ color: "var(--ink)", fontSize: 13 }}>{r.name}</b>
                        <span style={{ color: "var(--moss)", fontSize: 12 }}> · {AGENCY[r.agency] || r.agency} · {r.incumbent || "open field"}</span></div>
                    </div>
                  ))}
                  {queryRows.length === 0 && <div style={{ fontSize: 13, color: "var(--moss)", fontStyle: "italic" }}>No programs match those constraints.</div>}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      <p style={{ fontSize: 11.5, color: "var(--moss)", marginTop: 16, lineHeight: 1.5 }}>
        Scores are a transparent weighted heuristic over a synthetic federal funding graph — defensible, not yet validated against real win/loss. Click a row to see the factor breakdown.
      </p>
    </div>
  );
}
