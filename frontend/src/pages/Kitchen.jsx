import { useEffect, useState } from 'react';
import { api } from '../api';

export default function Kitchen() {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(true);
  const [msg, setMsg] = useState('');
  const [form, setForm] = useState({ name: '', qty: 1, unit: 'g', expiry_days: 7 });

  const load = async () => {
    setBusy(true);
    try { setItems(await api('/api/kitchen')); } catch (e) { setMsg(e.message); }
    setBusy(false);
  };
  useEffect(() => { load(); }, []);

  const add = async () => {
    if (!form.name.trim()) { setMsg('Name your ingredient first.'); return; }
    try {
      await api('/api/kitchen', { method: 'POST', body: { ...form, qty: Number(form.qty) } });
      setForm({ name: '', qty: 1, unit: 'g', expiry_days: 7 });
      setMsg('Added ✅');
      load();
    } catch (e) { setMsg(e.message); }
  };

  const setQty = async (it, delta) => {
    await api(`/api/kitchen/${it.id}`, { method: 'PUT', body: { name: it.display, qty: Math.max(0, Number(it.qty) + delta), unit: it.unit } });
    load();
  };

  const remove = async (id) => {
    if (!confirm('Remove this ingredient?')) return;
    await api(`/api/kitchen/${id}`, { method: 'DELETE' });
    load();
  };

  const low = items.filter(i => i.status === 'low-stock');
  const soon = items.filter(i => i.expiring_soon && i.status !== 'out-of-stock');

  return (
    <div className="page">
      <h1>My Kitchen 🧂</h1>
      <p className="small">Quantities + expiry drive recommendations, kitchen checks and shopping lists.</p>
      {msg && <div className="alert info">{msg}</div>}
      {(low.length > 0 || soon.length > 0) && (
        <div className="alert warn">
          {low.length > 0 && <div>⚠️ Low stock: {low.map(i => i.display).join(', ')}</div>}
          {soon.length > 0 && <div>⏰ Use soon: {soon.map(i => `${i.display} (${i.expiry_in_days}d)`).join(', ')} — FoodMate will prioritize these.</div>}
        </div>
      )}
      <div className="panel">
        <h3>Add ingredient</h3>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input className="input" style={{ maxWidth: 220 }} placeholder="e.g. paneer" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className="input" type="number" style={{ maxWidth: 110 }} value={form.qty} onChange={(e) => setForm({ ...form, qty: e.target.value })} aria-label="Quantity" />
          <select className="select" style={{ maxWidth: 110 }} value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })}>
            {['g', 'kg', 'ml', 'L', 'pcs'].map(u => <option key={u} value={u}>{u}</option>)}
          </select>
          <button className="btn btn-primary btn-sm" onClick={add}>＋ Add</button>
        </div>
      </div>
      {busy ? <div className="skel" style={{ height: 240, marginTop: 14 }} /> : (
        <div className="panel" style={{ marginTop: 14 }}>
          <table className="table">
            <thead><tr><th>Ingredient</th><th>Qty</th><th>Status</th><th>Expiry</th><th></th></tr></thead>
            <tbody>
              {items.map(it => (
                <tr key={it.id}>
                  <td><strong>{it.display}</strong></td>
                  <td>{it.qty}{it.unit} <button className="chip" onClick={() => setQty(it, -1)}>−</button> <button className="chip" onClick={() => setQty(it, 1)}>＋</button></td>
                  <td>{it.status === 'available' ? <span className="badge green">✅ Available</span>
                    : it.status === 'low-stock' ? <span className="badge">⚠️ Low</span>
                    : <span className="badge red">❌ Out</span>}</td>
                  <td className="small">{it.expiry ? `${it.expiry} (${it.expiry_in_days}d)` : '—'}{it.expiring_soon && ' ⏰'}</td>
                  <td><button className="link" style={{ background: 'none', border: 0 }} onClick={() => remove(it.id)}>remove</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          {items.length === 0 && <div className="empty"><div className="big">🧂</div><p>Kitchen is empty — add ingredients to unlock smart picks.</p></div>}
        </div>
      )}
    </div>
  );
}
