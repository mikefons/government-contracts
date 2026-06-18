// Token + session helpers. Token is stored in localStorage (real app, not a sandboxed artifact).
const KEY = "chancery.session";

export function getSession() {
  try { return JSON.parse(localStorage.getItem(KEY)); } catch { return null; }
}
export function setSession(s) { localStorage.setItem(KEY, JSON.stringify(s)); }
export function clearSession() { localStorage.removeItem(KEY); }
export function token() { return getSession()?.access_token || null; }
