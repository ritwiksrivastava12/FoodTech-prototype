import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, fmtRs } from '../api';

export default function MealDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [m, setM] = useState(null);
  const [serv, setServ] = useState(2);
  const [compare, setCompare] = useState(null);
  const [err, setErr] = useState('');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(true);

  const load = async (s = serv) => {
    setBusy(true); setErr('');
    try {
      const d = await api(`/api/meals/${id}?servings=${s}`);
      setM(d);
      const c = await api(`/api/compare/cook-vs-order/${id}?servings=${s}`);
      setCompare(c);
    } catch (e) { setErr(e.message); }
    setBusy(false);
  };

  useEffect(() => { load(2); }, [id]);

  const changeServ = (s) => {
    const v = Math.min(8, Math.max(1, s));
    setServ(v);
    load(v);
  };

  const addMissing = async () => {
    try {
      const r = await api('/api/shopping/generate', { method: 'POST', body: { meal_ids: [Number(id)], servings: serv, name: `${m.name} groceries` } });
      setMsg(r.message || `Added ${r.items_added} item(s) to shopping list.`);
    } catch (e) { setMsg(e.message); }
  };

  const saveFav = async () => {
    try { await api('/api/favorites', { method: 'POST', body: { meal_id: Number(id) } }); setMsg('Saved to Go-To meals ❤️'); }
    catch (e) { setMsg(e.message); }
  };

  const addToPlanner = async (mealType) => {
    const today = new Date().toISOString().slice(0, 10);
    try {
      await api('/api/planner', { method: 'POST', body: { date: today, meal_type: mealType, meal_id: Number(id) } });
      setMsg(`Added to today's ${mealType} planner 📅`);
    } catch (e) { setMsg(e.message); }
  };

  if (busy) return <div className="page"><div className="skel" style={{ height: 380 }} /></div>;
  if (err) return <div className="page"><div className="alert err">{err}</div><Link className="link" to="/meals">← Back to meals</Link></div>;
  if (!m) return null;

  const check = m.availability || {};
  const items = check.items || [];
  const nut = m.nutrition_scaled || {};

  return (
    <div className="page">
      <Link className="link" to="/">← Back</Link>
      <div className="two-col" style={{ marginTop: 12 }}>
        <div>
          <div className="meal-img" style={{ borderRadius: 22, height: 220, fontSize: 110 }}>
            <span>{m.image_emoji}</span><span className="time">⏱ {m.time_min} min</span>
          </div>
          <h1 style={{ marginTop: 12 }}>{m.name}</h1>
          <p className="small">{m.description}</p>
          <div className="meal-meta" style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
            <span className="badge">{m.category}</span>
            <span className="badge grey">{m.cuisine}</span>
            <span className="badge green">{m.diet}</span>
            <span className="badge">★ {Number(m.rating).toFixed(1)}</span>
          </div>
          {(m.reasons || []).length > 0 && <div className="alert info">💡 {(m.reasons || []).join(' · ')}</div>}
          {msg && <div className="alert ok">{msg}</div>}

          <div className="panel" style={{ marginTop: 12 }}>
            <h3>Servings: {serv}</h3>
            <div className="chip-row">
              {[1, 2, 4, 5].map(s => <button key={s} className={`chip ${serv === s ? 'on' : ''}`} onClick={() => changeServ(s)}>{s}</button>)}
              <button className="chip" onClick={() => changeServ(serv - 1)}>−</button>
              <button className="chip" onClick={() => changeServ(serv + 1)}>＋</button>
            </div>
            <div className="small" style={{ marginTop: 8 }}>Quantities, nutrition & cost rescale automatically.</div>
            <hr className="soft" />
            <h3>Nutrition (for {serv} serving{serv > 1 ? 's' : ''})</h3>
            <div className="kv"><span>🔥 Calories</span><strong>{Math.round(nut.calories || 0)} kcal</strong></div>
            <div className="kv"><span>💪 Protein</span><strong>{Math.round(nut.protein_g || 0)} g</strong></div>
            <div className="kv"><span>🍚 Carbs</span><strong>{Math.round(nut.carbs_g || 0)} g</strong></div>
            <div className="kv"><span>🧈 Fat</span><strong>{Math.round(nut.fat_g || 0)} g</strong></div>
            <div className="kv"><span>🌾 Fiber</span><strong>{Math.round(nut.fiber_g || 0)} g</strong></div>
            <div className="small">General info from structured recipe data — not medical advice.</div>
          </div>
        </div>

        <div>
          <div className="panel">
            <h3>🧂 Can I make this? <span className="badge green">{check.available_count}/{check.total_count} available</span></h3>
            <table className="table" style={{ marginTop: 8 }}>
              <thead><tr><th>Ingredient</th><th>Need</th><th>Have</th><th>Status</th></tr></thead>
              <tbody>
                {items.map((it, i) => (
                  <tr key={i}>
                    <td>{it.name}</td>
                    <td>{it.required}{it.required_unit}</td>
                    <td>{it.have}{it.have_unit}</td>
                    <td>{it.status === 'available' ? <span className="badge green">✅ OK</span>
                      : it.status === 'low' ? <span className="badge">⚠️ Low</span>
                      : <span className="badge red">❌ Missing</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(m.missing || []).length > 0
              ? <button className="btn btn-leaf btn-sm" style={{ marginTop: 10 }} onClick={addMissing}>＋ Add {m.missing.length} missing to shopping list</button>
              : <div className="alert ok">You have everything — ready to cook! 🎉</div>}
          </div>

          <div className="panel" style={{ marginTop: 14, border: '2px solid var(--leaf)' }}>
            <h3>⚖️ Cook vs Order</h3>
            {compare && (
              <>
                <div className="two-col">
                  <div className="panel" style={{ background: '#f2f8f2' }}>
                    <strong>🍳 Cook at home</strong>
                    <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--leaf)' }}>{fmtRs(compare.cook.cost)} <span className="small">/ {compare.cook.time_min} min</span></div>
                    {(compare.cook.pros || []).map(p => <div key={p} className="small">✅ {p}</div>)}
                  </div>
                  <div className="panel" style={{ background: '#fff6ec' }}>
                    <strong>🛵 Order <span className="demo-tag">demo</span></strong>
                    <div style={{ fontSize: 26, fontWeight: 800 }}>{fmtRs(compare.order.range[0])}–{fmtRs(compare.order.range[1])}</div>
                    {(compare.order.pros || []).map(p => <div key={p} className="small">✅ {p}</div>)}
                  </div>
                </div>
                <div className="alert ok" style={{ marginTop: 10 }}>{compare.verdict} FoodMate informs — you decide.</div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
                  <button className="btn btn-primary" onClick={() => nav(`/cook/${m.id}?servings=${serv}`)}>👨‍🍳 Cook now</button>
                  <button className="btn btn-ghost" onClick={() => nav(`/shop?meal=${m.id}`)}>🛵 Compare orders</button>
                </div>
              </>
            )}
          </div>

          <div className="panel" style={{ marginTop: 14 }}>
            <h3>Actions</h3>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button className="btn btn-ghost btn-sm" onClick={saveFav}>🤍 Save / Favorite</button>
              {['breakfast', 'lunch', 'snacks', 'dinner'].map(t =>
                <button key={t} className="btn btn-ghost btn-sm" onClick={() => addToPlanner(t)}>📅 {t}</button>)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
