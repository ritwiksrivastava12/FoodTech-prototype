import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api';

export default function CookMode() {
  const { id } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const serv = Number(sp.get('servings') || 2);
  const [data, setData] = useState(null);
  const [step, setStep] = useState(0);
  const [left, setLeft] = useState(null);
  const [err, setErr] = useState('');
  const [done, setDone] = useState(false);

  useEffect(() => {
    api(`/api/cook/${id}?servings=${serv}`).then(d => {
      setData(d);
      setLeft(d.steps?.[0]?.timer_sec ?? null);
    }).catch(e => setErr(e.message));
  }, [id]);

  useEffect(() => {
    if (left === null || left <= 0) return;
    const t = setTimeout(() => setLeft(l => l - 1), 1000);
    return () => clearTimeout(t);
  }, [left]);

  const go = (n) => {
    if (!data) return;
    const nx = Math.max(0, Math.min(data.steps.length - 1, n));
    setStep(nx);
    setLeft(data.steps[nx]?.timer_sec ?? null);
  };

  const finish = async (mode = 'cooked') => {
    try {
      await api('/api/history/complete', {
        method: 'POST',
        body: { meal_id: Number(id), meal_type: 'dinner', servings: serv, mode, deduct_inventory: mode === 'cooked' },
      });
      setDone(true);
    } catch (e) { setErr(e.message); }
  };

  if (err) return <div className="page"><div className="alert err">{err}</div><Link className="link" to={`/meals/${id}`}>← Back</Link></div>;
  if (!data) return <div className="page"><div className="skel" style={{ height: 300 }} /></div>;

  const s = data.steps[step];
  const mm = left !== null ? `${String(Math.floor(left / 60)).padStart(2, '0')}:${String(left % 60).padStart(2, '0')}` : null;

  if (done) return (
    <div className="page cook" style={{ textAlign: 'center', paddingTop: 60 }}>
      <div style={{ fontSize: 70 }}>🎉</div>
      <h1>Well done, chef!</h1>
      <p className="small">{data.meal} tracked — history, nutrition & kitchen updated.</p>
      <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 16 }}>
        <button className="btn btn-primary" onClick={() => nav('/nutrition')}>View nutrition 📊</button>
        <button className="btn btn-ghost" onClick={() => nav('/')}>Decide next meal</button>
      </div>
    </div>
  );

  return (
    <div className="page cook">
      <Link className="link" to={`/meals/${id}`}>← Exit Cook Mode</Link>
      <div className="small" style={{ marginTop: 8 }}>{data.meal} · {serv} serving{serv > 1 ? 's' : ''} · distraction-free</div>
      <div className="progress" style={{ margin: '12px 0' }}>
        <div style={{ width: `${((step + 1) / data.steps.length) * 100}%` }} />
      </div>
      <div className="step-card">
        <div className="step-num">STEP {step + 1} / {data.steps.length}</div>
        <h2>{s.title}</h2>
        <p>{s.detail}</p>
        {s.timer_sec ? (
          <div>
            <div className="timer">{mm}</div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
              <button className="btn btn-ghost btn-sm" onClick={() => setLeft(s.timer_sec)}>↺ Reset</button>
              <button className="btn btn-leaf btn-sm" onClick={() => setLeft(l => (l || 0) + 60)}>+1 min</button>
            </div>
          </div>
        ) : <div className="small">≈ {s.minutes} min · {step === 0 ? 'mise en place' : 'keep the flame as instructed'}</div>}
        <div className="panel" style={{ marginTop: 16, textAlign: 'left', background: '#faf6ec' }}>
          <strong style={{ fontSize: 13 }}>You need for this recipe ({serv} servings)</strong>
          <div className="small">{data.ingredients.map(i => `${i.name} ${i.qty}${i.unit}`).join(' · ')}</div>
        </div>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 18, flexWrap: 'wrap' }}>
          <button className="btn btn-ghost" disabled={step === 0} onClick={() => go(step - 1)}>← Back</button>
          {step < data.steps.length - 1
            ? <button className="btn btn-primary" onClick={() => go(step + 1)}>Next →</button>
            : <button className="btn btn-leaf" onClick={() => finish('cooked')}>✅ Done — I cooked it</button>}
        </div>
        {step === data.steps.length - 1 && (
          <button className="link" style={{ marginTop: 10, background: 'none', border: 0 }} onClick={() => finish('ordered')}>
            I ended up ordering instead
          </button>
        )}
      </div>
    </div>
  );
}
