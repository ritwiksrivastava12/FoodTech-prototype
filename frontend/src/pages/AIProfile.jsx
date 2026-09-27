import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../store/auth.jsx';

export default function AIPage() {
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [recs, setRecs] = useState([]);
  const nav = useNavigate();

  useEffect(() => {
    api('/api/ai/history').then(h => setMsgs((h || []).slice(-20).map(m => ({ role: m.role, content: m.content })))).catch(() => {});
  }, []);

  const send = async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || busy) return;
    setInput('');
    setMsgs(m => [...m, { role: 'user', content: msg }]);
    setBusy(true);
    try {
      const r = await api('/api/ai/chat', { method: 'POST', body: { message: msg, servings: 2 } });
      setMsgs(m => [...m, { role: 'assistant', content: r.reply }]);
      setRecs(r.recommendations || []);
    } catch (e) { setMsgs(m => [...m, { role: 'assistant', content: 'Error: ' + e.message }]); }
    setBusy(false);
  };

  const listen = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { alert('Voice needs Chrome.'); return; }
    const rec = new SR();
    rec.lang = 'en-IN';
    rec.onresult = (e) => send(e.results[0][0].transcript);
    rec.onend = () => setListening(false);
    rec.start();
    setListening(true);
  };

  const upload = async (file) => {
    if (!file) return;
    const label = window.prompt('What ingredients do you see? (comma-separated)', 'rice, eggs, onion');
    const labels = (label || '').split(',').map(s => s.trim()).filter(Boolean);
    setMsgs(m => [...m, { role: 'user', content: `📷 ${file.name}` }]);
    setBusy(true);
    try {
      const r = await api('/api/ai/vision', { method: 'POST', body: { labels, description: label || '' } });
      setMsgs(m => [...m, { role: 'assistant', content: `${r.advice}\n\n${r.disclaimer}` }]);
      setRecs(r.recommendations || []);
    } catch (e) { setMsgs(m => [...m, { role: 'assistant', content: 'Vision failed: ' + e.message }]); }
    setBusy(false);
  };

  return (
    <div className="page" style={{ maxWidth: 760 }}>
      <h1>FoodMate AI ✨</h1>
      <p className="small">Try: “I have rice, eggs and onions, what can I make?” · “tired, under ₹100” · “high-protein dinner” · “no paneer today”.</p>
      <div className="panel" style={{ minHeight: 300, display: 'flex', flexDirection: 'column', gap: 10 }}>
        {msgs.length === 0 && <div className="small">No conversation yet — say hi. 👋</div>}
        {msgs.map((m, i) => <div key={i} className={`msg ${m.role === 'user' ? 'user' : 'ai'}`} style={{ alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start' }}>{m.content}</div>)}
        {recs.map(r => (
          <div key={r.id} className="kv"><span>{r.image_emoji} <strong>{r.name}</strong> <span className="small">· {r.time_min}m · ₹{Math.round(r.cost_cook)}</span></span>
            <Link className="btn btn-primary btn-sm" to={`/meals/${r.id}`}>Cook / Order</Link></div>
        ))}
        {busy && <div className="skel" style={{ height: 40 }} />}
      </div>
      <div className="chat-input" style={{ border: '1px solid var(--line)', borderRadius: 16, marginTop: 10 }}>
        <button className={`icon-btn ${listening ? 'live' : ''}`} onClick={listen} aria-label="Speak">🎤</button>
        <label className="icon-btn" style={{ cursor: 'pointer' }}>📷
          <input type="file" accept="image/*" hidden onChange={(e) => upload(e.target.files[0])} /></label>
        <input className="input" value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()} placeholder="Ask naturally…" aria-label="Ask FoodMate" />
        <button className="btn btn-primary" onClick={() => send()} disabled={busy}>Send</button>
      </div>
    </div>
  );
}

export function Profile() {
  const { user, refresh, logout } = useAuth();
  const nav = useNavigate();
  const [p, setP] = useState(null);
  const [msg, setMsg] = useState('');
  const [history, setHistory] = useState([]);

  useEffect(() => {
    api('/api/profile').then(setP).catch(() => {});
    api('/api/history').then(setHistory).catch(() => {});
  }, []);

  const save = async () => {
    try {
      await api('/api/profile', { method: 'PUT', body: p });
      await refresh();
      setMsg('Saved ✅ — recommendations updated.');
    } catch (e) { setMsg(e.message); }
  };

  if (!p) return <div className="page"><div className="skel" style={{ height: 300 }} /></div>;
  const set = (k, v) => setP({ ...p, [k]: v });
  const csv = (k) => (p[k] || []).join(', ');

  return (
    <div className="page" style={{ maxWidth: 720 }}>
      <h1>Profile 👤</h1>
      <p className="small">{user?.name} · {user?.email}</p>
      {msg && <div className="alert ok">{msg}</div>}
      <div className="panel">
        <div className="form-grid">
          <div><label className="label">Diet</label>
            <select className="select" value={p.diet} onChange={(e) => set('diet', e.target.value)}>
              {['vegetarian', 'non-veg', 'eggetarian', 'vegan', 'jain', 'other'].map(d => <option key={d} value={d}>{d}</option>)}
            </select></div>
          <div><label className="label">Cooking ability</label>
            <select className="select" value={p.cooking_ability} onChange={(e) => set('cooking_ability', e.target.value)}>
              {['beginner', 'intermediate', 'advanced'].map(d => <option key={d} value={d}>{d}</option>)}
            </select></div>
          <div><label className="label">Allergies (comma-separated)</label>
            <input className="input" value={csv('allergies')} onChange={(e) => set('allergies', e.target.value.split(',').map(s => s.trim()).filter(Boolean))} /></div>
          <div><label className="label">Disliked</label>
            <input className="input" value={csv('disliked')} onChange={(e) => set('disliked', e.target.value.split(',').map(s => s.trim()).filter(Boolean))} /></div>
          <div><label className="label">Budget per meal (₹)</label>
            <input className="input" type="number" value={p.budget_per_meal} onChange={(e) => set('budget_per_meal', Number(e.target.value))} /></div>
          <div><label className="label">Repetition rule</label>
            <select className="select" value={p.repetition_rule} onChange={(e) => set('repetition_rule', e.target.value)}>
              <option value="allow">Allow repeats</option>
              <option value="no-same-day">No same-day repeat</option>
              <option value="avoid-2-days">Avoid 2-day repeat</option>
              <option value="avoid-3-days">Avoid 3-day repeat</option>
            </select></div>
          <div><label className="label">Calorie target</label>
            <input className="input" type="number" value={p.calorie_target} onChange={(e) => set('calorie_target', Number(e.target.value))} /></div>
          <div><label className="label">Protein target (g)</label>
            <input className="input" type="number" value={p.protein_target} onChange={(e) => set('protein_target', Number(e.target.value))} /></div>
          <div><label className="label">Nutrition goal</label>
            <select className="select" value={p.nutrition_goal} onChange={(e) => set('nutrition_goal', e.target.value)}>
              {['balanced', 'high-protein', 'muscle-gain', 'weight-loss', 'low-carb'].map(g => <option key={g} value={g}>{g}</option>)}
            </select></div>
          <div><label className="label">Fitness goal</label>
            <input className="input" value={p.fitness_goal} onChange={(e) => set('fitness_goal', e.target.value)} /></div>
        </div>
        <button className="btn btn-primary" style={{ marginTop: 14 }} onClick={save}>Save preferences</button>
        <button className="btn btn-ghost" style={{ marginTop: 14, marginLeft: 8 }} onClick={() => { logout(); nav('/welcome'); }}>Log out</button>
      </div>
      <div className="panel" style={{ marginTop: 14 }}>
        <h3>Meal history 🕘</h3>
        {(history || []).length === 0 ? <div className="small">No meals tracked yet.</div> :
          history.slice(0, 12).map(h => (
            <div className="kv" key={h.id}><span>{h.date} · {h.meal_type} · {h.meal_name} ({h.mode})</span>
              <strong>₹{Math.round(h.cost)} · {Math.round(h.calories)} kcal</strong></div>
          ))}
        <div className="small">History powers no-repeat logic, nutrition & budget insights.</div>
      </div>
    </div>
  );
}
