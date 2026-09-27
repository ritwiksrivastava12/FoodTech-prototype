// Tiny fetch client. No secrets here — token only.
const BASE = import.meta.env.VITE_API_BASE || '';

export function getToken() { return localStorage.getItem('fm_token') || ''; }
export function setToken(t) { t ? localStorage.setItem('fm_token', t) : localStorage.removeItem('fm_token'); }

export async function api(path, { method = 'GET', body, form, auth = true } = {}) {
  const headers = {};
  if (auth && getToken()) headers['Authorization'] = 'Bearer ' + getToken();
  let payload;
  if (form) { payload = form; }
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
  const res = await fetch(BASE + path, { method, headers, body: payload });
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = { detail: text }; }
  if (!res.ok) {
    const msg = (data && (data.detail || data.message)) || `Request failed (${res.status})`;
    throw new Error(Array.isArray(msg) ? msg.map(m => m.msg || m).join('; ') : msg);
  }
  return data;
}

export const fmtRs = (n) => '₹' + Math.round(Number(n || 0));
export function greeting() {
  const h = new Date().getHours();
  if (h < 11) return 'Good morning';
  if (h < 16) return 'Good afternoon';
  return 'Good evening';
}
export function mealNow() {
  const h = new Date().getHours();
  if (h >= 5 && h < 11) return 'breakfast';
  if (h >= 11 && h < 16) return 'lunch';
  if (h >= 16 && h < 19) return 'snacks';
  return 'dinner';
}
