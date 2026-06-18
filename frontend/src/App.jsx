import React, { useState, useEffect, useMemo, useRef, useCallback } from "react";
import {
  Search, LayoutDashboard, FileSearch, Award, Radio, KanbanSquare,
  Bot, Bell, BellOff, Plus, ChevronRight, ChevronLeft, CalendarClock,
  Target, TrendingUp, Star, ArrowRight, Sparkles, Send, Filter, X,
  ShieldCheck, Workflow,
} from "lucide-react";
import { LogOut, Brain } from "lucide-react";
import { api } from "./api.js";
import { getSession, clearSession } from "./auth.js";
import Login from "./Login.jsx";
import Intel from "./Intel.jsx";

/* ── helpers ── */
const fmtGBP = (n) =>
  n >= 1e6 ? `£${(n / 1e6).toFixed(n >= 1e7 ? 0 : 1)}M` : `£${(n / 1e3).toFixed(0)}k`;
const daysUntil = (d) => (d ? Math.round((new Date(d) - new Date()) / 86400000) : null);
const STAGES = ["Identify", "Qualify", "Capture", "Proposal", "Submitted"];

function Stat({ lab, val, meta, kind }) {
  return (
    <div className={`ch-stat ${kind || ""}`}>
      <div className="lab">{lab}</div>
      <div className="val ch-serif">{val}</div>
      {meta && <div className="meta">{meta}</div>}
    </div>
  );
}
function Deadline({ date }) {
  const d = daysUntil(date);
  if (d === null) return <span className="ch-pip ok">—</span>;
  const cls = d <= 5 ? "hot" : d <= 14 ? "soon" : "ok";
  return (
    <span className={`ch-pip ${cls}`}>
      <CalendarClock size={13} />
      {d}d · {new Date(date).toLocaleDateString("en-GB", { day: "2-digit", month: "short" })}
    </span>
  );
}
function MarketChip({ m }) {
  const cls = { Federal: "fed", SLED: "sled", EU: "eu" }[m] || "";
  const label = { Federal: "UK CENTRAL", SLED: "UK LOCAL/NHS", EU: "EU" }[m] || m;
  return <span className={`ch-chip ${cls}`}>{label}</span>;
}

function marginNote(o) {
  const d = daysUntil(o.close);
  const sov = /sovereign|air-gapped|UK-hosted|residency|on-prem/i.test(o.desc);
  return [
    `${o.agency} — a ${fmtGBP(o.value)} requirement${d !== null ? `, closing in ${d} days` : ""}. ${
      o.incumbent.includes("None")
        ? "No incumbent: a genuine open field."
        : `Incumbent is ${o.incumbent} — frame this as a credible challenger, not a like-for-like swap.`
    }`,
    sov
      ? "Sovereignty is the decisive axis. Lead with data-residency, auditability and the absence of third-country processing — where US-hosted incumbents are structurally exposed."
      : "Sovereignty is not the primary lever here; compete on delivery confidence, references and total cost.",
    `Fit signal: matches graph-intelligence and causal-reasoning capability. Recommend ${
      d !== null && d < 10 ? "an expedited go/no-go this week" : "moving to Qualify and assigning a capture lead"
    }.`,
  ];
}

/* ── Drawer ── */
function Drawer({ opp, onClose, onAdd }) {
  if (!opp) return null;
  const notes = marginNote(opp);
  return (
    <>
      <div className="ch-scrim" onClick={onClose} />
      <aside className="ch-drawer" role="dialog" aria-label={opp.title}>
        <div className="ch-drawer-h" style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", gap: 7, marginBottom: 9 }}>
              <MarketChip m={opp.market} />
              <span className="ch-chip">{opp.vehicle}</span>
            </div>
            <h3 className="ch-serif" style={{ margin: 0, fontSize: 19, color: "var(--ink)", lineHeight: 1.3 }}>
              {opp.title}
            </h3>
            <div className="ch-mono" style={{ fontSize: 11.5, color: "var(--moss)", marginTop: 6 }}>{opp.ref}</div>
          </div>
          <button className="ch-x" onClick={onClose} aria-label="Close"><X size={16} /></button>
        </div>
        <div className="ch-drawer-b">
          <div className="ch-margin" style={{ marginBottom: 20 }}>
            <div className="tag"><Sparkles size={13} /> Analyst margin note</div>
            {notes.map((n, i) => <p key={i}>{n}</p>)}
          </div>
          <p style={{ fontSize: 13.5, lineHeight: 1.6, color: "var(--slate)", marginTop: 0 }}>{opp.desc}</p>
          <dl className="ch-deflist" style={{ marginTop: 14 }}>
            <dt>Buyer</dt><dd>{opp.agency}</dd>
            <dt>Value</dt><dd className="ch-mono">{fmtGBP(opp.value)}</dd>
            <dt>Closes</dt><dd><Deadline date={opp.close} /></dd>
            <dt>CPV code</dt><dd className="ch-mono">{opp.cpv || "—"}</dd>
            <dt>Incumbent</dt><dd>{opp.incumbent}</dd>
            <dt>Region</dt><dd>{opp.region || "—"}</dd>
          </dl>
          <div style={{ display: "flex", gap: 10, marginTop: 22 }}>
            <button className="ch-btn amber" onClick={() => onAdd(opp.id)}><Plus size={15} /> Add to capture board</button>
            <button className="ch-btn ghost"><Star size={15} /> Save search</button>
          </div>
        </div>
      </aside>
    </>
  );
}

/* ── Dashboard ── */
function Dashboard({ go }) {
  const [sum, setSum] = useState(null);
  const [closing, setClosing] = useState([]);
  const [signals, setSignals] = useState([]);
  useEffect(() => {
    api.summary().then(setSum).catch(() => {});
    api.opportunities().then((o) =>
      setClosing(o.filter((x) => { const d = daysUntil(x.close); return d !== null && d <= 14; })
        .sort((a, b) => daysUntil(a.close) - daysUntil(b.close)))
    ).catch(() => {});
    api.signals().then(setSignals).catch(() => {});
  }, []);
  return (
    <div className="ch-page">
      <div className="ch-grid" style={{ gridTemplateColumns: "repeat(4,1fr)" }}>
        <Stat lab="Live pipeline value" val={sum ? fmtGBP(sum.pipeline_value) : "—"} meta={<><b>{sum?.active_pursuits ?? "–"}</b> active pursuits</>} />
        <Stat lab="Closing this week" val={sum?.closing_this_week ?? "—"} meta="needs go/no-go" kind="amber" />
        <Stat lab="New signals" val={sum?.signals ?? "—"} meta={<><b>{sum?.high_signals ?? "–"}</b> high relevance</>} />
        <Stat lab="Win rate (12mo)" val="31%" meta={<><b>+22%</b> bid rate vs last yr</>} />
      </div>
      <div className="ch-grid" style={{ gridTemplateColumns: "1.5fr 1fr", marginTop: 16 }}>
        <div className="ch-panel">
          <div className="ch-panel-h"><CalendarClock size={17} className="ic" /><h3>Closing soon</h3><span className="right">{closing.length} within 14 days</span></div>
          <table className="ch-table"><tbody>
            {closing.map((o) => (
              <tr key={o.id} className="row" onClick={() => go("opps", o.id)}>
                <td><div className="title">{o.title}</div><div className="agency">{o.agency}</div></td>
                <td style={{ whiteSpace: "nowrap" }}><Deadline date={o.close} /></td>
                <td className="ch-mono" style={{ textAlign: "right", color: "var(--forest-hi)", fontWeight: 600 }}>{fmtGBP(o.value)}</td>
              </tr>
            ))}
          </tbody></table>
        </div>
        <div className="ch-panel">
          <div className="ch-panel-h"><Radio size={17} className="ic" /><h3>Top signals</h3></div>
          <div style={{ padding: "6px 8px" }}>
            {signals.slice(0, 3).map((s) => (
              <div key={s.id} style={{ display: "flex", gap: 12, padding: "12px", borderBottom: "1px solid var(--bone-2)" }}>
                <div className="ch-score" style={{ flex: "0 0 38px" }}><div className="num" style={{ fontSize: 19 }}>{s.score}</div></div>
                <div><div style={{ fontSize: 13, fontWeight: 600, color: "var(--ink)", lineHeight: 1.35 }}>{s.title}</div><div style={{ fontSize: 11.5, color: "var(--moss)", marginTop: 4 }}>{s.when}</div></div>
              </div>
            ))}
            <div style={{ padding: 12 }}><button className="ch-btn ghost sm" onClick={() => go("signals")}>View all signals <ArrowRight size={14} /></button></div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Opportunities ── */
function Opportunities({ openId, setOpenId, onAdd }) {
  const [q, setQ] = useState("");
  const [market, setMarket] = useState("All");
  const [vehicle, setVehicle] = useState("All");
  const [alertOn, setAlertOn] = useState(false);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [opp, setOpp] = useState(null);

  useEffect(() => {
    setLoading(true);
    const t = setTimeout(() => {
      api.opportunities({ q, market, vehicle }).then((r) => { setRows(r); setLoading(false); }).catch(() => setLoading(false));
    }, 180); // debounce
    return () => clearTimeout(t);
  }, [q, market, vehicle]);

  useEffect(() => {
    if (openId) api.opportunity(openId).then(setOpp).catch(() => setOpp(null));
    else setOpp(null);
  }, [openId]);

  const vehicles = useMemo(() => [...new Set(rows.map((r) => r.vehicle))], [rows]);

  return (
    <div className="ch-page">
      <div className="ch-filters">
        <div className="ch-searchbar" style={{ marginLeft: 0, width: 280 }}>
          <Search size={15} color="var(--moss)" />
          <input placeholder="Search title, buyer, reference…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <select className="ch-sel" value={market} onChange={(e) => setMarket(e.target.value)}>
          <option>All</option><option value="Federal">UK Central</option><option value="SLED">UK Local / NHS</option><option value="EU">EU</option>
        </select>
        <select className="ch-sel" value={vehicle} onChange={(e) => setVehicle(e.target.value)}>
          <option value="All">All vehicles</option>
          {["G-Cloud 14", "DOS 6", "Tech Services 3", "FTS / OJEU", "NHS SBS", "Contracts Finder", "DE&S Direct", "EU TED", ...vehicles]
            .filter((v, i, a) => a.indexOf(v) === i).map((v) => <option key={v}>{v}</option>)}
        </select>
        <button className={`ch-toggle ${alertOn ? "on" : ""}`} onClick={() => setAlertOn((a) => !a)}>
          {alertOn ? <Bell size={14} /> : <BellOff size={14} />} {alertOn ? "Alerts on for this search" : "Alert me on new matches"}
        </button>
        <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--moss)" }} className="ch-mono">{rows.length} results</span>
      </div>
      <div className="ch-panel">
        <table className="ch-table">
          <thead><tr><th>Opportunity</th><th>Market</th><th>Vehicle</th><th>Closes</th><th>Incumbent</th><th style={{ textAlign: "right" }}>Value</th></tr></thead>
          <tbody>
            {loading ? <tr><td colSpan={6}><div className="ch-load">Loading the feed…</div></td></tr> :
              rows.map((o) => (
                <tr key={o.id} className="row" onClick={() => setOpenId(o.id)}>
                  <td><div className="title">{o.title}</div><div className="agency ch-mono">{o.ref} · {o.agency}</div></td>
                  <td><MarketChip m={o.market} /></td>
                  <td><span className="ch-chip">{o.vehicle}</span></td>
                  <td style={{ whiteSpace: "nowrap" }}><Deadline date={o.close} /></td>
                  <td style={{ fontSize: 12.5, color: o.incumbent.includes("None") ? "var(--forest-hi)" : "var(--slate)" }}>{o.incumbent}</td>
                  <td className="ch-mono" style={{ textAlign: "right", fontWeight: 600, color: "var(--ink)" }}>{fmtGBP(o.value)}</td>
                </tr>
              ))}
            {!loading && rows.length === 0 && <tr><td colSpan={6}><div className="ch-empty"><FileSearch size={34} className="ic" /><p>No solicitations match.</p><span>Widen the market or clear the search.</span></div></td></tr>}
          </tbody>
        </table>
      </div>
      <Drawer opp={opp} onClose={() => setOpenId(null)} onAdd={(id) => { onAdd(id); setOpenId(null); }} />
    </div>
  );
}

/* ── Awards ── */
function Awards() {
  const [awards, setAwards] = useState([]);
  const [trend, setTrend] = useState([]);
  useEffect(() => {
    api.awards().then(setAwards).catch(() => {});
    api.awardTrend().then(setTrend).catch(() => {});
  }, []);
  const max = Math.max(1, ...trend.map((d) => d.v));
  const W = 560, H = 170, P = 26;
  const step = trend.length > 1 ? (W - P * 2) / (trend.length - 1) : 0;
  const pts = trend.map((d, i) => [P + i * step, H - P - (d.v / max) * (H - P * 2)]);
  const line = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const area = pts.length ? `${line} L ${pts[pts.length - 1][0].toFixed(1)} ${H - P} L ${pts[0][0].toFixed(1)} ${H - P} Z` : "";
  return (
    <div className="ch-page">
      <div className="ch-grid" style={{ gridTemplateColumns: "1fr 1fr", marginBottom: 16 }}>
        <div className="ch-panel">
          <div className="ch-panel-h"><TrendingUp size={17} className="ic" /><h3>Sovereign-AI award value</h3><span className="right">£M / quarter</span></div>
          <div style={{ padding: "18px 12px 8px" }}>
            <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label="Award value trend">
              <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#2C5544" stopOpacity="0.28" /><stop offset="1" stopColor="#2C5544" stopOpacity="0" /></linearGradient></defs>
              {area && <path d={area} fill="url(#g)" />}
              {line && <path d={line} fill="none" stroke="#2C5544" strokeWidth="2.5" />}
              {pts.map((p, i) => <circle key={i} cx={p[0]} cy={p[1]} r="3.5" fill="#C8852A" />)}
              {trend.map((d, i) => <text key={i} x={pts[i][0]} y={H - 7} fontSize="9.5" textAnchor="middle" fill="#5C7A6A" fontFamily="IBM Plex Mono">{d.q}</text>)}
            </svg>
          </div>
        </div>
        <div className="ch-grid" style={{ gridTemplateColumns: "1fr 1fr", alignContent: "start" }}>
          <Stat lab="Total awarded (12mo)" val="£135M" meta={<><b>+58%</b> YoY</>} />
          <Stat lab="Avg. contract" val="£22.5M" kind="amber" />
          <Stat lab="US-hosted incumbents" val="46%" meta="of awarded value" kind="ox" />
          <Stat lab="Open re-competes" val="7" meta="next 18 months" />
        </div>
      </div>
      <div className="ch-panel">
        <div className="ch-panel-h"><Award size={17} className="ic" /><h3>Recent awards</h3><span className="right">incumbents · contracting officers</span></div>
        <table className="ch-table">
          <thead><tr><th>Contract</th><th>Buyer</th><th>Awarded to</th><th>Vehicle</th><th>Contracting officer</th><th style={{ textAlign: "right" }}>Value</th></tr></thead>
          <tbody>
            {awards.map((a) => (
              <tr key={a.ref}>
                <td><div className="title" style={{ fontSize: 13 }}>{a.title}</div><div className="agency ch-mono">{a.ref} · {a.date ? new Date(a.date).toLocaleDateString("en-GB", { month: "short", year: "numeric" }) : "—"}</div></td>
                <td style={{ fontSize: 12.5 }}>{a.agency}</td>
                <td style={{ fontWeight: 600, color: "var(--ink)", fontSize: 12.5 }}>{a.vendor}</td>
                <td><span className="ch-chip">{a.vehicle}</span></td>
                <td className="ch-mono" style={{ fontSize: 12, color: "var(--forest-hi)" }}>{a.co}</td>
                <td className="ch-mono" style={{ textAlign: "right", fontWeight: 600, color: "var(--ink)" }}>{fmtGBP(a.value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ── Signals ── */
function Signals() {
  const [focus, setFocus] = useState("All");
  const [all, setAll] = useState([]);
  useEffect(() => { api.signals().then(setAll).catch(() => {}); }, []);
  const list = all.filter((s) => focus === "All" || s.tags.some((t) => t.includes(focus)));
  return (
    <div className="ch-page">
      <div className="ch-filters">
        <Filter size={15} color="var(--moss)" />
        {["All", "Budget", "Pre-solicitation", "Policy", "Compliance", "RFI"].map((f) => (
          <button key={f} className={`ch-toggle ${focus === f ? "on" : ""}`} onClick={() => setFocus(f)}>{f}</button>
        ))}
      </div>
      <div className="ch-grid" style={{ gridTemplateColumns: "1fr" }}>
        {list.map((s) => (
          <div className="ch-signal" key={s.id}>
            <div className="ch-score"><div className="num">{s.score}</div><div className="lab">relevance</div></div>
            <div style={{ flex: 1 }}>
              <h4>{s.title}</h4><p>{s.body}</p>
              <div className="tags">{s.tags.map((t) => <span className="ch-chip" key={t}>{t}</span>)}<span style={{ marginLeft: "auto", fontSize: 11.5, color: "var(--moss)" }}>{s.when}</span></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Capture board ── */
function CaptureBoard() {
  const [board, setBoard] = useState(null);
  const [opps, setOpps] = useState({});
  const [dragId, setDragId] = useState(null);
  const [overCol, setOverCol] = useState(null);

  const load = useCallback(() => {
    api.board().then(setBoard).catch(() => {});
    api.opportunities().then((list) => setOpps(Object.fromEntries(list.map((o) => [o.id, o])))).catch(() => {});
  }, []);
  useEffect(load, [load]);

  const move = (id, stage) => {
    setBoard((b) => { const nb = {}; STAGES.forEach((s) => (nb[s] = (b[s] || []).filter((x) => x !== id))); nb[stage] = [...(nb[stage] || []), id]; return nb; });
    api.move(id, stage).catch(load);
  };
  const shift = (id, from, dir) => { const i = STAGES.indexOf(from) + dir; if (i >= 0 && i < STAGES.length) move(id, STAGES[i]); };

  if (!board) return <div className="ch-page"><div className="ch-load">Loading the capture board…</div></div>;
  return (
    <div className="ch-page" style={{ maxWidth: "none" }}>
      <div className="ch-board">
        {STAGES.map((stage) => (
          <div key={stage} className={`ch-col ${overCol === stage ? "drop" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setOverCol(stage); }}
            onDragLeave={() => setOverCol((c) => (c === stage ? null : c))}
            onDrop={() => { if (dragId) move(dragId, stage); setDragId(null); setOverCol(null); }}>
            <div className="ch-col-h"><span className="name">{stage}</span><span className="n">{(board[stage] || []).length}</span></div>
            <div className="ch-col-b">
              {(board[stage] || []).map((id) => {
                const o = opps[id]; if (!o) return null;
                const col = o.market === "Federal" ? "#1F3D30" : o.market === "SLED" ? "#26384a" : "#3a2f4a";
                return (
                  <div key={id} className="ch-dossier" draggable onDragStart={() => setDragId(id)} onDragEnd={() => { setDragId(null); setOverCol(null); }}>
                    <div className="stripe" style={{ background: col }} />
                    <div className="num">{o.ref}</div>
                    <div className="ttl">{o.title}</div>
                    <Deadline date={o.close} />
                    <div className="ft">
                      <span className="val">{fmtGBP(o.value)}</span>
                      <div className="ch-move">
                        <button disabled={stage === STAGES[0]} onClick={() => shift(id, stage, -1)} aria-label="Move left"><ChevronLeft size={13} /></button>
                        <button disabled={stage === STAGES[STAGES.length - 1]} onClick={() => shift(id, stage, 1)} aria-label="Move right"><ChevronRight size={13} /></button>
                      </div>
                    </div>
                  </div>
                );
              })}
              {(board[stage] || []).length === 0 && <div className="ch-serif" style={{ fontSize: 12, color: "var(--moss)", textAlign: "center", padding: "18px 0", fontStyle: "italic" }}>drop here</div>}
            </div>
          </div>
        ))}
      </div>
      <p style={{ fontSize: 12, color: "var(--moss)", marginTop: 14 }}>
        Drag a dossier between columns, or use the arrows — every move is persisted to the backend. Stripe colour marks the market:{" "}
        <b style={{ color: "#1F3D30" }}>UK central</b> · <b style={{ color: "#26384a" }}>UK local/NHS</b> · <b style={{ color: "#3a2f4a" }}>EU</b>.
      </p>
    </div>
  );
}

/* ── Automate ── */
function Automate() {
  const [tab, setTab] = useState("agent");
  const [flows, setFlows] = useState([]);
  const [msgs, setMsgs] = useState([{ role: "a", text: "I'm your capture analyst, grounded in the live feed. Ask about a buyer, an opportunity, the incumbent landscape, or how to position against a US-hosted vendor.", prov: "" }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const logRef = useRef(null);

  useEffect(() => { api.workflows().then(setFlows).catch(() => {}); }, []);
  useEffect(() => { logRef.current?.scrollTo(0, 1e6); }, [msgs, busy]);

  const ask = async (textArg) => {
    const text = (textArg ?? input).trim();
    if (!text || busy) return;
    setInput(""); setMsgs((m) => [...m, { role: "u", text }]); setBusy(true);
    try {
      const r = await api.agent(text);
      setMsgs((m) => [...m, { role: "a", text: r.answer, prov: r.provider }]);
    } catch {
      setMsgs((m) => [...m, { role: "a", text: "Couldn't reach the analyst service. Is the backend running?", prov: "error" }]);
    } finally { setBusy(false); }
  };
  const toggle = (wf) => {
    setFlows((fs) => fs.map((x) => (x.id === wf.id ? { ...x, enabled: !x.enabled } : x)));
    api.toggleWorkflow(wf.id, !wf.enabled).catch(() => api.workflows().then(setFlows));
  };

  return (
    <div className="ch-page">
      <div className="ch-filters">
        <button className={`ch-toggle ${tab === "agent" ? "on" : ""}`} onClick={() => setTab("agent")}><Bot size={14} /> Agent</button>
        <button className={`ch-toggle ${tab === "flows" ? "on" : ""}`} onClick={() => setTab("flows")}><Workflow size={14} /> Workflows</button>
      </div>
      {tab === "agent" ? (
        <div className="ch-panel">
          <div className="ch-panel-h"><Bot size={17} className="ic" /><h3>Capture analyst</h3><span className="right">Anthropic · Ollama · offline</span></div>
          <div className="ch-chat">
            <div className="ch-chat-log" ref={logRef}>
              {msgs.map((mm, i) => (
                <div key={i} className={`ch-msg ${mm.role}`}>
                  {mm.role === "a" && mm.prov && <div className="prov">{mm.prov}</div>}
                  {mm.text}
                </div>
              ))}
              {busy && <div className="ch-msg a" style={{ fontStyle: "italic", color: "var(--moss)" }}>Analysing the feed…</div>}
            </div>
            <div className="ch-suggest">
              {["Which 3 should we bid first?", "How do we beat Palantir on the NHS demand model?", "Who's the CO to contact at HMRC?", "Summarise the Frontex requirement"].map((s) => (
                <button key={s} onClick={() => ask(s)} disabled={busy}>{s}</button>
              ))}
            </div>
            <div className="ch-chat-in">
              <input placeholder="Ask the analyst…" value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask()} />
              <button className="ch-btn" onClick={() => ask()} disabled={busy}><Send size={15} /></button>
            </div>
          </div>
        </div>
      ) : (
        <div>
          {flows.map((f) => (
            <div className="ch-flow" key={f.id}>
              <div className="ch-flow-h">
                <Workflow size={17} color="var(--forest-hi)" /><h4>{f.name}</h4>
                <button className={`ch-switch ${f.enabled ? "on" : ""}`} aria-label="Toggle workflow" onClick={() => toggle(f)} />
              </div>
              <div className="ch-steps">
                {f.steps.map(([k, t], i) => (
                  <React.Fragment key={i}>
                    <span className={`ch-step ${k}`}>{k === "trig" ? "WHEN" : ""} {t}</span>
                    {i < f.steps.length - 1 && <ChevronRight size={13} color="var(--moss)" />}
                  </React.Fragment>
                ))}
              </div>
            </div>
          ))}
          <button className="ch-btn ghost"><Plus size={15} /> New workflow</button>
        </div>
      )}
    </div>
  );
}

/* ── Shell ── */
const NAV = [
  { key: "dash", label: "Command", icon: LayoutDashboard },
  { key: "opps", label: "Opportunities", icon: FileSearch },
  { key: "awards", label: "Awards", icon: Award },
  { key: "signals", label: "Signals", icon: Radio },
  { key: "board", label: "Capture board", icon: KanbanSquare },
];
const TITLES = {
  dash: ["Command", "Your pipeline, deadlines and signals at a glance"],
  opps: ["Opportunities", "Federal, devolved, NHS and EU solicitations in one feed"],
  awards: ["Awards", "Historical contracts, incumbents and contracting officers"],
  signals: ["Signals", "Pre-solicitation intelligence from budgets, policy and news"],
  board: ["Capture board", "Move pursuits from identify to submitted"],
  automate: ["Automate", "Agents and workflows that do the manual work"],
  intel: ["Intelligence", "Predict where funding, mission and technology converge — before the RFP"],
};

export default function App() {
  const [session, setSession] = useState(getSession());
  const [view, setView] = useState("dash");
  const [openId, setOpenId] = useState(null);
  const go = (v, id = null) => { setView(v); setOpenId(id); };
  const addToBoard = (id) => { api.move(id, "Identify").finally(() => setView("board")); };
  const signOut = () => { clearSession(); setSession(null); };
  const [t, sub] = TITLES[view];

  if (!session) return <Login onAuthed={setSession} />;

  return (
    <div className="ch-root">
      <nav className="ch-side">
        <div className="ch-brand"><h1>Chancery</h1><div className="seal"><ShieldCheck size={12} /> Sovereign Procurement Intelligence</div></div>
        <div className="ch-nav">
          <div className="ch-navlabel">Pipeline</div>
          {NAV.map((n) => { const I = n.icon; return (
            <button key={n.key} className={`ch-navitem ${view === n.key ? "on" : ""}`} onClick={() => go(n.key)}><I size={17} className="ic" /> {n.label}</button>
          ); })}
          <div className="ch-navlabel">Operations</div>
          <button className={`ch-navitem ${view === "intel" ? "on" : ""}`} onClick={() => go("intel")}><Brain size={17} className="ic" /> Intelligence</button>
          <button className={`ch-navitem ${view === "automate" ? "on" : ""}`} onClick={() => go("automate")}><Bot size={17} className="ic" /> Automate</button>
        </div>
        <div className="ch-who">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
            <div style={{ minWidth: 0 }}>
              <b style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis" }}>{session.name || "Signed in"}</b>
              <span style={{ textTransform: "uppercase", letterSpacing: ".5px", fontSize: 10.5 }}>{session.role} · OFFICIAL-SENSITIVE</span>
            </div>
            <button className="ch-signout" onClick={signOut} aria-label="Sign out" title="Sign out"><LogOut size={15} /></button>
          </div>
        </div>
      </nav>
      <main className="ch-main">
        <header className="ch-top">
          <div><h2>{t}</h2><div className="sub">{sub}</div></div>
          <div className="ch-searchbar"><Search size={15} color="var(--moss)" /><input placeholder="Search the platform…" onFocus={() => setView("opps")} /></div>
          <button className="ch-btn"><Plus size={15} /> New pursuit</button>
        </header>
        {view === "dash" && <Dashboard go={go} />}
        {view === "opps" && <Opportunities openId={openId} setOpenId={setOpenId} onAdd={addToBoard} />}
        {view === "awards" && <Awards />}
        {view === "signals" && <Signals />}
        {view === "board" && <CaptureBoard />}
        {view === "intel" && <Intel />}
        {view === "automate" && <Automate />}
      </main>
    </div>
  );
}
