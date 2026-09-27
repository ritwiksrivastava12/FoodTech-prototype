import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, greeting, mealNow } from '../api';
import { useAuth } from '../store/auth.jsx';
import MealCard from '../components/MealCard.jsx';

const MOODS = [['tired', '😮‍💨'], ['happy', '😊'], ['stressed', '😣'], ['comfort', '🤗'], ['spicy', '🌶️'],
  ['light', '🥗'], ['healthy', '💪'], ['filling', '🍛'], ['high-protein', '🏋️'], ['budget', '💰'], ['quick', '⚡']];
const FILTERS = ['Quick & Easy', 'High Protein', 'Budget Friendly', 'Healthy', 'Comfort Food', 'Under 15 Minutes'];

const FILTER_QUERY = {
  'Quick & Easy': 'something quick and easy under 20 minutes',
  'High Protein': 'high protein meal',
  'Budget Friendly': 'something under Rs 100',
  'Healthy': 'healthy light meal',
  'Comfort Food': 'comfort food',
  'Under 15 Minutes': 'what can I make in 15 minutes',
};

export default function Home() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [mood, setMood] = useState('tired');
  const [text, setText] = useState('');
  const [recs, setRecs] = useState([]);
  const [sections, setSections] = useState([]);
  const [byId, setById] = useState({});
  const [busy, setBusy] = useState(true);
  const [err, setErr] = useState('');
  const [favIds, setFavIds] = useState(new Set());
  const [activeFilter, setActiveFilter] = useState('');

  const loadFavs = async () => {
    try {
      const f = await api('/api/favorites');
      setFavIds(new Set(f.filter(x => x.meal_id).map(x => x.meal_id)));
    } catch {}
  };

  const fetchRecs = async (intentText = '', quick = false) => {
    setBusy(true); setErr('');
    try {
      const r = await api('/api/recommendations', {
        method: 'POST', body: { mood, intent_text: intentText, meal_type: mealNow(), servings: 2, quick_only: quick, limit: 9 },
      });
      setRecs(r.results || []);
      setSections(r.sections || []);
      const map = {};
      (r.results || []).forEach(m => { map[m.id] = m; });
      setById(map);
    } catch (e) { setErr(e.message); }
    setBusy(false);
  };

  useEffect(() => { loadFavs(); fetchRecs(); }, []);

  const toggleFav = async (m) => {
    try {
      if (favIds.has(m.id)) {
        const list = await api('/api/favorites');
        const row = list.find(x => x.meal_id === m.id);
        if (row) await api(`/api/favorites/${row.id}`, { method: 'DELETE' });
        setFavIds(s => { const n = new Set(s); n.delete(m.id); return n; });
      } else {
        await api('/api/favorites', { method: 'POST', body: { meal_id: m.id } });
        setFavIds(s => new Set(s).add(m.id));
      }
    } catch (e) { alert(e.message); }
  };

  const replace = async (m) => {
    // Regenerate excluding this meal: re-fetch and drop it, showing next best
    await fetchRecs(`not ${m.name}`);
  };

  const ask = () => {
    if (!text.trim() && !mood) return;
    fetchRecs(text);
  };

  const applyFilter = (f) => {
    if (activeFilter === f) { setActiveFilter(''); fetchRecs(); return; }
    setActiveFilter(f);
    setMood(f === 'High Protein' ? 'high-protein' : f === 'Budget Friendly' ? 'budget' : f === 'Healthy' ? 'healthy' : f === 'Comfort Food' ? 'comfort' : 'tired');
    fetchRecs(FILTER_QUERY[f] || '', f === 'Quick & Easy' || f === 'Under 15 Minutes');
  };

  const secMeals = (ids) => (ids || []).map(id => byId[id]).filter(Boolean);

  return (
    <div className="page">
      <div className="hero">
        <p className="small" style={{ fontWeight: 800, letterSpacing: '.08em', textTransform: 'uppercase' }}>
          {greeting()}, {user?.name?.split(' ')[0]} · {mealNow()} time 🍽️
        </p>
        <h1>What would you<br />like to <em>eat?</em></h1>
        <div className="askbar">
          <textarea className="textarea" value={text} onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(); } }}
            placeholder="Try: tired, spicy, high-protein under ₹100 — I have rice, eggs & onions, no paneer today…" aria-label="What would you like to eat?" />
          <div className="askbar-actions">
            <button className="btn btn-primary" onClick={ask} disabled={busy}>{busy ? 'Thinking…' : '✨ Decide for me'}</button>
            <button className="btn btn-ghost btn-sm" onClick={() => nav('/ai')}>🎤 Voice / 📷 Image</button>
          </div>
        </div>
        <div style={{ marginTop: 12 }}>
          <div className="small" style={{ marginBottom: 6, fontWeight: 700 }}>How are you feeling?</div>
          <div className="chip-row">
            {MOODS.map(([id, e]) => (
              <button key={id} className={`chip ${mood === id ? 'on' : ''}`} onClick={() => { setMood(id); }}>{e} {id}</button>
            ))}
          </div>
        </div>
        <div className="chip-row" style={{ marginTop: 10 }}>
          {FILTERS.map(f => (
            <button key={f} className={`chip ${activeFilter === f ? 'on' : ''}`} onClick={() => applyFilter(f)}>{f}</button>
          ))}
        </div>
      </div>

      {err && <div className="alert err">{err} <button className="btn btn-ghost btn-sm" onClick={() => fetchRecs()}>Retry</button></div>}

      {busy ? (
        <div className="grid cards" style={{ marginTop: 18 }}>
          {[1, 2, 3].map(i => <div key={i} className="skel" style={{ height: 300 }} />)}
        </div>
      ) : recs.length === 0 ? (
        <div className="empty"><div className="big">🍽️</div>
          <h3>No safe matches</h3>
          <p className="small">Try relaxing budget/time, or tell me what you have at home.</p>
          <button className="btn btn-primary" onClick={() => { setText(''); setActiveFilter(''); fetchRecs(); }}>Reset</button>
        </div>
      ) : (
        <>
          <div className="section">
            <div className="section-head"><h2>Recommended for you</h2><p>mood · kitchen · budget · history</p></div>
            <div className="grid cards">
              {recs.slice(0, 3).map(m => <MealCard key={m.id} m={m} onFav={toggleFav} favIds={favIds} onReplace={replace} />)}
            </div>
          </div>
          {sections.filter(s => s.title !== 'Recommended for you').map(s => (
            secMeals(s.ids).length > 0 && (
              <div className="section" key={s.title}>
                <div className="section-head"><h2>{s.title}</h2><p>{s.subtitle}</p></div>
                <div className="hscroll">
                  {secMeals(s.ids).map(m => <MealCard key={m.id} m={m} onFav={toggleFav} favIds={favIds} />)}
                </div>
              </div>
            )
          ))}
          {recs.length > 3 && (
            <div className="section">
              <div className="section-head"><h2>More picks</h2><p>regenerate anytime</p></div>
              <div className="grid cards">
                {recs.slice(3).map(m => <MealCard key={m.id} m={m} onFav={toggleFav} favIds={favIds} onReplace={replace} />)}
              </div>
              <div style={{ marginTop: 12 }}>
                <button className="btn btn-ghost" onClick={() => fetchRecs(text + ' (surprise me)')}>🔀 Regenerate ideas</button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
