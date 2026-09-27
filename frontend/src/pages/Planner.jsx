import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';

const TYPES = ['breakfast', 'lunch', 'snacks', 'dinner'];
const todayStr = () => new Date().toISOString().slice(0, 10);

export default function Planner() {
  const [plans, setPlans] = useState([]);
  const [meals, setMeals] = useState([]);
  const [day, setDay] = useState(todayStr());
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(true);

  const load = async () => {
    setBusy(true);
    try {
      const [p, m] = await Promise.all([api('/api/planner'), api('/api/meals')]);
      setPlans(p); setMeals(m);
    } catch (e) { setMsg(e.message); }
    setBusy(false);
  };
  useEffect(() => { load(); }, []);

  const dayPlans = plans.filter(p => p.date === day);
  const byType = Object.fromEntries(TYPES.map(t => [t, dayPlans.find(p => p.meal_type === t)]));

  const setMeal = async (type, mealId, locked = false) => {
    try {
      await api('/api/planner', { method: 'POST', body: { date: day, meal_type: type, meal_id: mealId || null, locked } });
      setMsg(`Saved ${type} ✅`);
      load();
    } catch (e) { setMsg(e.message); }
  };

  const autoFill = async () => {
    setMsg('Generating week…');
    try {
      const r = await api('/api/recommendations', { method: 'POST', body: { intent_text: 'balanced week, no repeats', limit: 12 } });
      const picks = r.results || [];
      for (let i = 0; i < 7; i++) {
        const d = new Date(day);
        d.setDate(d.getDate() + i);
        const ds = d.toISOString().slice(0, 10);
        for (const t of ['breakfast', 'lunch', 'dinner']) {
          const existing = plans.find(p => p.date === ds && p.meal_type === t);
          if (existing?.locked) continue;
          const m = picks[(i * 3 + TYPES.indexOf(t)) % Math.max(1, picks.length)];
          if (m) await api('/api/planner', { method: 'POST', body: { date: ds, meal_type: t, meal_id: m.id } });
        }
      }
      setMsg('Week planned 🎉 (locked meals untouched)');
      load();
    } catch (e) { setMsg(e.message); }
  };

  const shoppingFromPlan = async () => {
    const ids = dayPlans.map(p => p.meal_id).filter(Boolean);
    if (!ids.length) { setMsg('Plan something first, then generate the list.'); return; }
    try {
      const r = await api('/api/shopping/generate', { method: 'POST', body: { meal_ids: ids, servings: 2, name: `${day} groceries` } });
      setMsg(r.message);
    } catch (e) { setMsg(e.message); }
  };

  return (
    <div className="page">
      <h1>Planner 📅</h1>      <p className="small">Accept, replace, regenerate, lock — then generate a smart shopping list (only what's missing).</p>
      {msg && <div className="alert info">{msg}</div>}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <input className="input" type="date" value={day} onChange={(e) => setDay(e.target.value)} style={{ maxWidth: 200 }} />
        <button className="btn btn-primary btn-sm" onClick={autoFill}>✨ Auto-plan week</button>
        <button className="btn btn-ghost btn-sm" onClick={shoppingFromPlan}>🛒 Shopping list from plan</button>
        <Link className="btn btn-ghost btn-sm" to="/shop">View lists</Link>
      </div>
      {busy ? <div className="skel" style={{ height: 260, marginTop: 14 }} /> : (
        <div className="grid cards" style={{ marginTop: 14 }}>
          {TYPES.map(t => (
            <div className="panel" key={t}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ textTransform: 'capitalize' }}>{t}</h3>
                {byType[t]?.locked && <span className="badge">🔒 locked</span>}
              </div>
              {byType[t]?.meal_id ? (
                <>
                  <div style={{ fontSize: 40 }}>{meals.find(m => m.id === byType[t].meal_id)?.image_emoji || '🍽️'}</div>
                  <strong>{byType[t].meal_name}</strong>
                  <div style={{ display: 'flex', gap: 6, marginTop: 10, flexWrap: 'wrap' }}>
                    <Link className="btn btn-primary btn-sm" to={`/meals/${byType[t].meal_id}`}>View</Link>
                    <button className="btn btn-ghost btn-sm" onClick={() => setMeal(t, byType[t].meal_id, !byType[t].locked)}>
                      {byType[t].locked ? '🔓 Unlock' : '🔒 Lock'}</button>
                    <select className="select" style={{ maxWidth: 170 }} value={byType[t].meal_id}
                      onChange={(e) => setMeal(t, Number(e.target.value), byType[t].locked)} aria-label={`Replace ${t}`}>
                      {meals.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                    </select>
                  </div>
                </>
              ) : (
                <>
                  <div className="small">Nothing planned.</div>
                  <select className="select" defaultValue="" onChange={(e) => e.target.value && setMeal(t, Number(e.target.value))} aria-label={`Choose ${t}`}>
                    <option value="">+ Choose a meal…</option>
                    {meals.filter(m => m.category === t).map(m => <option key={m.id} value={m.id}>{m.name} · {m.time_min}m</option>)}
                  </select>
                  <CustomPlan day={day} type={t} onSaved={load} />
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CustomPlan({ day, type, onSaved }) {
  const [name, setName] = useState('');
  const add = async () => {
    if (!name.trim()) return;
    await api('/api/planner', { method: 'POST', body: { date: day, meal_type: type, custom_name: name.trim() } });
    setName('');
    onSaved();
  };
  return (
    <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
      <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Or type a custom meal…" aria-label={`Custom ${type}`} />
      <button className="btn btn-ghost btn-sm" onClick={add}>Add</button>
    </div>
  );
}
