import { useEffect, useState } from 'react';
import { api } from '../api';

export default function Nutrition() {
  const [day, setDay] = useState(new Date().toISOString().slice(0, 10));
  const [data, setData] = useState(null);
  const [goals, setGoals] = useState({ calorie_target: 2000, protein_target: 70, nutrition_goal: 'balanced', fitness_goal: 'stay-fit' });
  const [gym, setGym] = useState(false);
  const [highP, setHighP] = useState([]);
  const [msg, setMsg] = useState('');

  const load = async () => {
    try {
      const [d, g] = await Promise.all([api(`/api/nutrition/daily?day=${day}`), api('/api/nutrition/goals')]);
      setData(d); setGoals(g);
      const r = await api('/api/recommendations', { method: 'POST', body: { intent_text: 'high protein muscle gain', limit: 6 } });
      setHighP((r.results || []).filter(m => m.protein_g >= 15).slice(0, 4));
    } catch (e) { setMsg(e.message); }
  };
  useEffect(() => { load(); }, [day]);

  const saveGoals = async () => {
    await api('/api/nutrition/goals', { method: 'PUT', body: goals });
    setMsg('Goals saved ✅');
    load();
  };

  const c = data?.consumed || { calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0, fiber_g: 0 };
  const calPct = Math.min(100, Math.round((c.calories / (goals.calorie_target || 2000)) * 100));
  const proPct = Math.min(100, Math.round((c.protein_g / (goals.protein_target || 70)) * 100));

  return (
    <div className="page">
      <h1>Nutrition 💪</h1>
      <p className="small">General info from structured data — not medical advice. {gym || goals.nutrition_goal === 'high-protein' ? '🏋️ Gym mode on: high-protein picks prioritized.' : ''}</p>
      {msg && <div className="alert ok">{msg}</div>}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <input className="input" type="date" value={day} onChange={(e) => setDay(e.target.value)} style={{ maxWidth: 190 }} />
        <button className={`chip ${gym ? 'on' : ''}`} onClick={() => setGym(!gym)}>🏋️ Gym mode</button>
      </div>
      <div className="two-col" style={{ marginTop: 14 }}>
        <div className="panel">
          <h3>Today · {day}</h3>
          <div className="small">Calories {Math.round(c.calories)} / {goals.calorie_target} kcal ({calPct}%)</div>
          <div className="progress" style={{ margin: '6px 0 12px' }}><div style={{ width: `${calPct}%` }} /></div>
          <div className="small">Protein {Math.round(c.protein_g)} / {goals.protein_target} g ({proPct}%)</div>
          <div className="progress" style={{ margin: '6px 0 12px' }}><div style={{ width: `${proPct}%` }} /></div>
          <div className="kv"><span>Carbs</span><strong>{Math.round(c.carbs_g)} g</strong></div>
          <div className="kv"><span>Fat</span><strong>{Math.round(c.fat_g)} g</strong></div>
          <div className="kv"><span>Fiber</span><strong>{Math.round(c.fiber_g)} g</strong></div>
          <hr className="soft" />
          <h3>Logged meals</h3>
          {(data?.meals || []).length === 0 ? <div className="small">Nothing logged yet — finish a Cook Mode or order to track.</div> :
            (data.meals || []).map((m, i) => <div className="kv" key={i}><span>{m.meal_type} · {m.meal_name}</span><strong>{Math.round(m.calories)} kcal · {Math.round(m.protein_g)}g</strong></div>)}
        </div>
        <div>
          <div className="panel">
            <h3>Goals</h3>
            <label className="label">Calorie target</label>
            <input className="input" type="number" value={goals.calorie_target} onChange={(e) => setGoals({ ...goals, calorie_target: Number(e.target.value) })} />
            <label className="label">Protein target (g)</label>
            <input className="input" type="number" value={goals.protein_target} onChange={(e) => setGoals({ ...goals, protein_target: Number(e.target.value) })} />
            <label className="label">Nutrition goal</label>
            <select className="select" value={goals.nutrition_goal} onChange={(e) => setGoals({ ...goals, nutrition_goal: e.target.value })}>
              {['balanced', 'high-protein', 'muscle-gain', 'weight-loss', 'low-carb'].map(g => <option key={g} value={g}>{g}</option>)}
            </select>
            <button className="btn btn-primary btn-sm" style={{ marginTop: 12 }} onClick={saveGoals}>Save goals</button>
          </div>
          {(gym || goals.nutrition_goal === 'high-protein' || goals.nutrition_goal === 'muscle-gain') && (
            <div className="panel" style={{ marginTop: 14 }}>
              <h3>🏋️ High-protein picks</h3>
              {highP.map(m => (
                <div className="kv" key={m.id}><span>{m.image_emoji} {m.name}</span>
                  <span><strong>{Math.round(m.protein_g)}g</strong> <a className="link" href={`#/meals/${m.id}`}>View →</a></span></div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
