import { Link } from 'react-router-dom';
import { fmtRs } from '../api';

export default function MealCard({ m, onFav, favIds, onReplace }) {
  const avail = m.availability || {};
  const dot = avail.overall === 'all' ? 'g' : avail.overall === 'partial' ? 'y' : avail.overall === 'missing' ? 'r' : 'y';
  return (
    <div className="meal-card">
      <Link to={`/meals/${m.id}`} style={{ textDecoration: 'none', color: 'inherit', display: 'flex', flexDirection: 'column', flex: 1 }}>
        <div className="meal-img">
          <span>{m.image_emoji || '🍛'}</span>
          <span className="time">⏱ {m.time_min} min</span>
        </div>
        <div className="meal-body">
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'flex-start' }}>
            <h3>{m.name}</h3>
            <span className="badge grey">★ {Number(m.rating || 4).toFixed(1)}</span>
          </div>
          <div className="meal-meta">
            <span className="badge green"><span className={`dot ${dot}`} />{avail.overall === 'all' ? 'All ingredients' : avail.overall === 'partial' ? `${avail.available_count}/${avail.total_count} in kitchen` : 'Check kitchen'}</span>
            <span className="badge">{m.category}</span>
          </div>
          <div className="macros">
            <span>🔥 {Math.round(m.calories)} kcal</span>
            <span>💪 {Math.round(m.protein_g)}g protein</span>
          </div>
          <div className="cost-row">
            <span className="cost-cook">🍳 {fmtRs(m.cost_cook_scaled ?? m.cost_cook)}</span>
            <span className="cost-order">· Order {fmtRs(m.cost_order_low)}–{fmtRs(m.cost_order_high)}</span>
          </div>
          {(m.reasons || []).length > 0 && <div className="reasons">💡 {(m.reasons || []).slice(0, 2).join(' · ')}</div>}
        </div>
      </Link>
      <div className="meal-body" style={{ paddingTop: 0 }}>
        <div className="card-actions">
          <Link className="btn btn-primary btn-sm" to={`/meals/${m.id}`}>Cook / Order</Link>
          <button className="btn btn-ghost btn-sm" onClick={(e) => { e.stopPropagation(); onFav && onFav(m); }}>
            {favIds?.has(m.id) ? '❤️ Saved' : '🤍 Save'}
          </button>
          {onReplace && <button className="btn btn-ghost btn-sm" onClick={(e) => { e.stopPropagation(); onReplace(m); }}>🔁 Replace</button>}
        </div>
      </div>
    </div>
  );
}
