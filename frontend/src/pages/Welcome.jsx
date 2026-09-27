import { Link } from 'react-router-dom';

export default function Welcome() {
  return (
    <div className="page">
      <div className="hero" style={{ textAlign: 'center', paddingTop: 40 }}>
        <div className="brand-mark" style={{ width: 64, height: 64, fontSize: 34, margin: '0 auto 16px' }}>🍲</div>
        <h1>Stop wondering<br /><em>what to eat.</em></h1>
        <p style={{ margin: '14px auto', textAlign: 'center' }}>
          FoodMate is your personal food operating system — it understands your mood, kitchen,
          budget, time and nutrition, then connects deciding → checking → comparing → cooking/ordering → tracking.
        </p>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 18 }}>
          <Link className="btn btn-primary" to="/signup">Get started free</Link>
          <Link className="btn btn-ghost" to="/login">Log in</Link>
        </div>
        <div className="small" style={{ marginTop: 10 }}>Demo login: demo@foodmate.app / demo1234</div>
      </div>
      <div className="two-col" style={{ marginTop: 34 }}>
        {[
          ['🧠', 'Decide', 'Mood-aware recommendations that respect diet, allergies, budget, time and what you ate already.'],
          ['🧂', 'Check', 'Quantity-aware kitchen check + expiry-smart picks that reduce waste.'],
          ['⚖️', 'Compare', 'Cook vs Order with honest cost math — cooking ₹65 vs ordering ₹149–189.'],
          ['👨‍🍳', 'Cook / Order', 'Exact-quantity Cook Mode with timers, or demo grocery & delivery comparisons.'],
          ['📊', 'Track', 'Meal history, nutrition vs goals, and spending visibility in one loop.'],
          ['✨', 'Assist', 'Text, voice and image AI that explains every pick — never bossy, never fake-live.'],
        ].map(([e, t, d]) => (
          <div className="panel" key={t}>
            <div style={{ fontSize: 30 }}>{e}</div>
            <h3 style={{ margin: '8px 0 6px' }}>{t}</h3>
            <div className="small" style={{ fontSize: 14 }}>{d}</div>
          </div>
        ))}
      </div>
      <div className="panel" style={{ marginTop: 18, background: 'linear-gradient(135deg,#1e5b3a,#2c7a4f)', color: '#fff', border: 0 }}>
        <h2 style={{ color: '#fff' }}>Tonight's example</h2>
        <p style={{ opacity: 0.9 }}>Tired after college/work · spicy comfort · high-protein · ₹100 · 20 min · rice, eggs & onions in the kitchen · no paneer (had it at lunch)</p>
        <p style={{ fontSize: 20, fontWeight: 800 }}>→ Egg Fried Rice · 15 min · cook ₹65 · 19g protein · all ingredients ✅</p>
        <Link className="btn" style={{ background: '#fff', color: '#1e5b3a' }} to="/signup">Try it yourself</Link>
      </div>
    </div>
  );
}
