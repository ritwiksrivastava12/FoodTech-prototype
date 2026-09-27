import { useEffect, useState } from 'react';
import { api } from '../api';
import MealCard from '../components/MealCard.jsx';

const CATS = ['', 'breakfast', 'lunch', 'snacks', 'dinner'];

export default function Meals() {
  const [q, setQ] = useState('');
  const [cat, setCat] = useState('');
  const [results, setResults] = useState([]);
  const [intent, setIntent] = useState(null);
  const [busy, setBusy] = useState(true);
  const [favs, setFavs] = useState([]);
  const [favIds, setFavIds] = useState(new Set());
  const [showFavs, setShowFavs] = useState(false);
  const [custom, setCustom] = useState({ name: '', category: 'dinner', time_min: 20, cost_cook: 80, protein_g: 10, calories: 400 });

  const load = async () => {
    setBusy(true);
    try {
      if (q.trim()) {
        const r = await api(`/api/meals/search?q=${encodeURIComponent(q)}`);
        setResults(r.results || []);
        setIntent(r.intent || null);
      } else {
        const r = await api(`/api/meals${cat ? `?category=${cat}` : ''}`);
        setResults(r || []);
        setIntent(null);
      }
    } catch (e) { setResults([]); }
    setBusy(false);
  };

  const loadFavs = async () => {
    try {
      const f = await api('/api/favorites');
      setFavs(f);
      setFavIds(new Set(f.filter(x => x.meal_id).map(x => x.meal_id)));
    } catch {}
  };

  useEffect(() => { load(); loadFavs(); }, []);
  useEffect(() => { const t = setTimeout(load, 450); return () => clearTimeout(t); }, [q, cat]);

  const toggleFav = async (m) => {
    if (favIds.has(m.id)) {
      const row = (await api('/api/favorites')).find(x => x.meal_id === m.id);
      if (row) await api(`/api/favorites/${row.id}`, { method: 'DELETE' });
    } else await api('/api/favorites', { method: 'POST', body: { meal_id: m.id } });
    loadFavs();
  };

  const addCustom = async () => {
    if (!custom.name.trim()) { alert('Give your meal a name'); return; }
    await api('/api/favorites', { method: 'POST', body: { name: custom.name, ...custom, custom: true } });
    setCustom({ name: '', category: 'dinner', time_min: 20, cost_cook: 80, protein_g: 10, calories: 400 });
    loadFavs();
    alert('Saved to your Go-To meals ❤️');
  };

  return (
    <div className="page">
      <h1>Meals 🍛</h1>
      <p className="small">Search naturally — dishes, cravings, cuisines, nutrition, or “I have rice, eggs & onion”.</p>
      <input className="input" value={q} onChange={(e) => setQ(e.target.value)}
        placeholder="High protein dinner under ₹150 · 15 minutes · without paneer…" aria-label="Search meals" />
      {intent && <div className="small" style={{ marginTop: 6 }}>Understood: moods [{(intent.moods || []).join(', ') || '—'}]
        {intent.budget ? ` · ≤₹${intent.budget}` : ''}{intent.max_time ? ` · ≤${intent.max_time} min` : ''}
        {(intent.have || []).length ? ` · have: ${intent.have.join(', ')}` : ''}</div>}
      <div className="chip-row" style={{ marginTop: 10 }}>
        {CATS.map(c => <button key={c} className={`chip ${cat === c ? 'on' : ''}`} onClick={() => setCat(c)}>{c || 'All'}</button>)}
        <button className={`chip ${showFavs ? 'on' : ''}`} onClick={() => setShowFavs(!showFavs)}>❤️ Go-To meals ({favs.length})</button>
      </div>

      {showFavs && (
        <div className="panel" style={{ marginTop: 14 }}>
          <h3>Your Go-To meals</h3>
          {favs.length === 0 ? <div className="small">Nothing saved yet — tap 🤍 Save on any meal.</div> :
            <div className="chip-row" style={{ marginTop: 8 }}>
              {favs.map(f => <span key={f.id} className="badge green">❤️ {f.name}</span>)}
            </div>}
          <hr className="soft" />
          <h3>Add your own meal</h3>
          <div className="form-grid">
            <div><label className="label">Meal name</label>
              <input className="input" value={custom.name} onChange={(e) => setCustom({ ...custom, name: e.target.value })} placeholder="Dadi's khichdi" /></div>
            <div><label className="label">Category</label>
              <select className="select" value={custom.category} onChange={(e) => setCustom({ ...custom, category: e.target.value })}>
                {['breakfast', 'lunch', 'snacks', 'dinner'].map(c => <option key={c} value={c}>{c}</option>)}
              </select></div>
          </div>
          <button className="btn btn-leaf btn-sm" style={{ marginTop: 10 }} onClick={addCustom}>＋ Save custom meal</button>
        </div>
      )}

      <div className="section">
        {busy ? <div className="grid cards">{[1, 2, 3].map(i => <div key={i} className="skel" style={{ height: 280 }} />)}</div>
          : results.length === 0 ? <div className="empty"><div className="big">🔍</div><p>No meals found. Try different words.</p></div>
          : <div className="grid cards">{results.map(m => <MealCard key={m.id} m={m} onFav={toggleFav} favIds={favIds} />)}</div>}
      </div>
    </div>
  );
}
