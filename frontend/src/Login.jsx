import React, { useState } from "react";
import { ShieldCheck, LogIn } from "lucide-react";
import { api } from "./api.js";
import { setSession } from "./auth.js";

export default function Login({ onAuthed }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!email || !password || busy) return;
    setBusy(true); setErr("");
    try {
      const s = await api.login(email, password);
      setSession(s);
      onAuthed(s);
    } catch (e) {
      setErr(e.message || "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="ch-login">
      <div className="ch-login-card">
        <div className="ch-login-brand">
          <h1 className="ch-serif">Chancery</h1>
          <div className="seal"><ShieldCheck size={12} /> Sovereign Procurement Intelligence</div>
        </div>
        <label className="ch-field">
          <span>Email</span>
          <input type="email" value={email} autoFocus
                 onChange={(e) => setEmail(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && submit()} />
        </label>
        <label className="ch-field">
          <span>Password</span>
          <input type="password" value={password}
                 onChange={(e) => setPassword(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && submit()} />
        </label>
        {err && <div className="ch-login-err">{err}</div>}
        <button className="ch-btn" style={{ width: "100%", justifyContent: "center" }} onClick={submit} disabled={busy}>
          <LogIn size={15} /> {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="ch-login-note">Access is restricted and audited. Contact your administrator for an account.</p>
      </div>
    </div>
  );
}
