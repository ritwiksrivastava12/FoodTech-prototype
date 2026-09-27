import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api, fmtRs } from '../api';

export default function Shop() {
  const [sp] = useSearchParams();
  const [lists, setLists] = useState([]);
  const [grocery, setGrocery] = useState([]);
  const [delivery, setDelivery] = useState([]);
  const [q, setQ] = useState('');
  const [dish, setDish] = useState('');
  const [msg, setMsg] = useState('');
  const mealFocus = sp.get('meal');

  const load = async () => {
    try {
      const [l, g, d] = await Promise.all([
        api('/api/shopping'), api('/api/grocery/compare'), api('/api/delivery/compare'),
      ]);
      setLists(l); setGrocery(g.results || []); setDelivery(d.results || []);
    } catch (e) { setMsg(e.message); }
  };
  useEffect(() => { load(); }, []);

  const searchGrocery = async () => {
    const r = await api(`/api/grocery/compare?q=${encodeURIComponent(q)}`);
    setGrocery(r.results || []);
  };
  const searchDelivery = async () => {
    const r = await api(`/api/delivery/compare?dish=${encodeURIComponent(dish)}`);
    setDelivery(r.results || []);
  };

  const toggle = async (listId, item) => {
    await api(`/api/shopping/item/${item.id}`, { method: 'PUT', body: { checked: !item.checked } });
    load();
  };
  const sync = async (listId) => {
    const r = await api(`/api/shopping/sync/${listId}`, { method: 'POST' });
    setMsg(`Synced ${r.synced} purchased item(s) into your kitchen 🧂`);
    load();
  };
  const genAll = async () => {
    const r = await api('/api/shopping/generate', { method: 'POST', body: { servings: 2, name: 'Weekly groceries' } });
    setMsg(r.message);
    load();
  };

  return (
    <div className="page">
      <h1>Shop 🛒</h1>
      <p className="small">Smart lists (only what's missing) + transparent <span className="demo-tag">demo</span> grocery & delivery comparisons. Real partners plug in here later.</p>
      {msg && <div className="alert ok">{msg}</div>}

      <div className="section">
        <div className="section-head"><h2>Shopping lists</h2><button className="btn btn-primary btn-sm" onClick={genAll}>✨ Generate from plan</button></div>
        {lists.length === 0 ? <div className="empty"><div className="big">🧺</div><p>No lists yet — plan meals or check a recipe first.</p></div> :
          lists.map(l => (
            <div className="panel" key={l.id} style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong>{l.name}</strong>
                <span className="small">est. {fmtRs(l.total_est)} · {l.status}</span>
              </div>
              {(l.items || []).map(it => (
                <div key={it.id} style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '7px 0', borderBottom: '1px dashed var(--line)' }}>
                  <input type="checkbox" checked={it.checked} onChange={() => toggle(l.id, it)} aria-label={it.name} />
                  <span style={{ flex: 1, textDecoration: it.checked ? 'line-through' : 'none' }}>
                    {it.name} — {it.qty}{it.unit} <span className="small">· {fmtRs(it.est_price)} · {it.reason}</span>
                  </span>
                </div>
              ))}
              <button className="btn btn-leaf btn-sm" style={{ marginTop: 10 }} onClick={() => sync(l.id)}>📦 Mark purchased → sync to kitchen</button>
            </div>
          ))}
      </div>

      <div className="two-col">
        <div className="panel">
          <h3>Compare groceries <span className="demo-tag">demo prices</span></h3>
          <div style={{ display: 'flex', gap: 8 }}>
            <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="paneer, eggs, onion…" />
            <button className="btn btn-ghost btn-sm" onClick={searchGrocery}>Go</button>
          </div>
          <div className="alert warn" style={{ fontSize: 12 }}>Demo data — no live order. Buttons explain partner redirect.</div>
          {grocery.map((g, i) => (
            <div className="kv" key={i}>
              <span><strong>{g.brand}</strong> {g.name} · {g.platform} · {g.delivery}</span>
              <span><strong>{fmtRs(g.price)}</strong> <button className="btn btn-ghost btn-sm" onClick={() => alert(`Prototype: this would open ${g.platform} to buy ${g.name} (partner integration pending).`)}>Buy →</button></span>
            </div>
          ))}
        </div>
        <div className="panel">
          <h3>Compare delivery <span className="demo-tag">demo</span></h3>
          <div style={{ display: 'flex', gap: 8 }}>
            <input className="input" value={dish} onChange={(e) => setDish(e.target.value)} placeholder="egg fried rice…" />
            <button className="btn btn-ghost btn-sm" onClick={searchDelivery}>Go</button>
          </div>
          <div className="alert warn" style={{ fontSize: 12 }}>Demo estimates — no live order. {mealFocus && `Comparing for meal #${mealFocus}.`}</div>
          {delivery.map((d, i) => (
            <div className="kv" key={i}>
              <span><strong>{d.restaurant}</strong> ★{d.rating} · {d.dish} · {d.platform} · {d.eta}</span>
              <span><strong>{fmtRs(d.total)}</strong> <span className="small">(incl. fees)</span> <button className="btn btn-ghost btn-sm" onClick={() => alert(`Prototype: this would continue to ${d.platform} for ${d.dish} (partner integration pending).`)}>Order →</button></span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
