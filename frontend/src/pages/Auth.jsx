import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../store/auth.jsx';

export function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ email: 'demo@foodmate.app', password: 'demo1234' });
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  return (
    <div className="page" style={{ maxWidth: 480 }}>
      <h1>Welcome back 👋</h1>
      <p className="small">Log in to continue your food loop.</p>
      {err && <div className="alert err">{err}</div>}
      <label className="label">Email</label>
      <input className="input" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
      <label className="label">Password</label>
      <input className="input" type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
      <button className="btn btn-primary" style={{ marginTop: 16, width: '100%' }} disabled={busy}
        onClick={async () => { setBusy(true); setErr(''); try { await login(f.email, f.password); nav('/'); } catch (e) { setErr(e.message); } setBusy(false); }}>
        Log in
      </button>
      <p className="small">No account? <Link className="link" to="/signup">Create one</Link></p>
    </div>
  );
}

const DIETS = ['vegetarian', 'non-veg', 'eggetarian', 'vegan', 'jain', 'other'];

export function Signup() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ name: '', email: '', password: '', phone: '' });
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  return (
    <div className="page" style={{ maxWidth: 520 }}>
      <h1>Create your account 🍲</h1>
      <p className="small">Then tell FoodMate about you so picks get personal.</p>
      {err && <div className="alert err">{err}</div>}
      <div className="form-grid">
        <div><label className="label">Name</label>
          <input className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Aarav Sharma" /></div>
        <div><label className="label">Mobile (optional)</label>
          <input className="input" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} placeholder="98765 43210" /></div>
      </div>
      <label className="label">Email</label>
      <input className="input" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} placeholder="you@example.com" />
      <label className="label">Password (min 6 chars)</label>
      <input className="input" type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
      <button className="btn btn-primary" style={{ marginTop: 16, width: '100%' }} disabled={busy}
        onClick={async () => { setBusy(true); setErr(''); try { await register(f); nav('/onboarding'); } catch (e) { setErr(e.message); } setBusy(false); }}>
        Create account
      </button>
      <p className="small">Have an account? <Link className="link" to="/login">Log in</Link></p>
    </div>
  );
}

export function Onboarding() {
  const { refresh } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({
    diet: 'eggetarian', allergies: '', disliked: '', favorites_food: '',
    cuisines: '', cooking_ability: 'beginner', equipment: 'gas stove, pan',
    budget_per_meal: 100, nutrition_goal: 'high-protein', fitness_goal: 'muscle-gain',
    calorie_target: 2200, protein_target: 90, repetition_rule: 'no-same-day',
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const csv = (s) => s.split(',').map(x => x.trim()).filter(Boolean);
  const save = async () => {
    setBusy(true); setErr('');
    try {
      await api('/api/profile', { method: 'PUT', body: {
        diet: f.diet, allergies: csv(f.allergies), disliked: csv(f.disliked),
        favorites_food: csv(f.favorites_food), cuisines: csv(f.cuisines),
        cooking_ability: f.cooking_ability, equipment: csv(f.equipment),
        budget_per_meal: Number(f.budget_per_meal), nutrition_goal: f.nutrition_goal,
        fitness_goal: f.fitness_goal, calorie_target: Number(f.calorie_target),
        protein_target: Number(f.protein_target), repetition_rule: f.repetition_rule,
      }});
      await refresh();
      nav('/');
    } catch (e) { setErr(e.message); }
    setBusy(false);
  };
  return (
    <div className="page" style={{ maxWidth: 640 }}>
      <h1>Make it yours ✨</h1>
      <p className="small">FoodMate personalizes everything from this. You can change it anytime in Profile.</p>
      {err && <div className="alert err">{err}</div>}
      <div className="form-grid">
        <div><label className="label">Dietary preference</label>
          <select className="select" value={f.diet} onChange={(e) => setF({ ...f, diet: e.target.value })}>
            {DIETS.map(d => <option key={d} value={d}>{d}</option>)}
          </select></div>
        <div><label className="label">Cooking ability</label>
          <select className="select" value={f.cooking_ability} onChange={(e) => setF({ ...f, cooking_ability: e.target.value })}>
            {['beginner', 'intermediate', 'advanced'].map(d => <option key={d} value={d}>{d}</option>)}
          </select></div>
        <div><label className="label">Allergies (comma-separated)</label>
          <input className="input" value={f.allergies} onChange={(e) => setF({ ...f, allergies: e.target.value })} placeholder="peanut, milk" /></div>
        <div><label className="label">Disliked foods</label>
          <input className="input" value={f.disliked} onChange={(e) => setF({ ...f, disliked: e.target.value })} placeholder="paneer, mushroom" /></div>
        <div><label className="label">Favorite foods</label>
          <input className="input" value={f.favorites_food} onChange={(e) => setF({ ...f, favorites_food: e.target.value })} placeholder="egg fried rice, maggi" /></div>
        <div><label className="label">Preferred cuisines</label>
          <input className="input" value={f.cuisines} onChange={(e) => setF({ ...f, cuisines: e.target.value })} placeholder="north-indian, indo-chinese" /></div>
        <div><label className="label">Kitchen equipment</label>
          <input className="input" value={f.equipment} onChange={(e) => setF({ ...f, equipment: e.target.value })} placeholder="gas stove, pan, pressure cooker" /></div>
        <div><label className="label">Budget per meal (₹)</label>
          <input className="input" type="number" value={f.budget_per_meal} onChange={(e) => setF({ ...f, budget_per_meal: e.target.value })} /></div>
        <div><label className="label">Nutrition goal</label>
          <select className="select" value={f.nutrition_goal} onChange={(e) => setF({ ...f, nutrition_goal: e.target.value })}>
            {['balanced', 'high-protein', 'muscle-gain', 'weight-loss', 'low-carb'].map(d => <option key={d} value={d}>{d}</option>)}
          </select></div>
        <div><label className="label">Repetition rule</label>
          <select className="select" value={f.repetition_rule} onChange={(e) => setF({ ...f, repetition_rule: e.target.value })}>
            <option value="allow">Allow repeats</option>
            <option value="no-same-day">No same-day repeat</option>
            <option value="avoid-2-days">Avoid 2-day repeat</option>
            <option value="avoid-3-days">Avoid 3-day repeat</option>
          </select></div>
        <div><label className="label">Calorie target</label>
          <input className="input" type="number" value={f.calorie_target} onChange={(e) => setF({ ...f, calorie_target: e.target.value })} /></div>
        <div><label className="label">Protein target (g)</label>
          <input className="input" type="number" value={f.protein_target} onChange={(e) => setF({ ...f, protein_target: e.target.value })} /></div>
      </div>
      <button className="btn btn-primary" style={{ marginTop: 18, width: '100%' }} disabled={busy} onClick={save}>
        {busy ? 'Saving…' : 'Start my food journey 🍛'}
      </button>
    </div>
  );
}
