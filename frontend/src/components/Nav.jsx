import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../store/auth.jsx';
import { useState } from 'react';
import AIDrawer from './AIDrawer.jsx';

const LINKS = [
  ['/', 'Home', '🏠'], ['/meals', 'Meals', '🍛'], ['/planner', 'Planner', '📅'],
  ['/kitchen', 'Kitchen', '🧂'], ['/shop', 'Shop', '🛒'], ['/nutrition', 'Nutrition', '💪'],
];

export default function Nav() {
  const loc = useLocation();
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [aiOpen, setAiOpen] = useState(false);

  return (
    <>
      <div className="topbar">
        <div className="topbar-in">
          <Link to={user ? '/' : '/welcome'} className="brand">
            <span className="brand-mark">🍲</span>
            <span className="brand-name">Food<span>Mate</span></span>
          </Link>
          {user && (
            <nav className="nav-links">
              {LINKS.map(([to, label]) => (
                <Link key={to} to={to} className={loc.pathname === to ? 'active' : ''}>{label}</Link>
              ))}
            </nav>
          )}
          <div className="topbar-right">
            {user ? (
              <>
                <button className="btn btn-primary btn-sm" onClick={() => setAiOpen(true)}>✨ Ask FoodMate</button>
                <Link className="btn btn-ghost btn-sm" to="/profile">👤 {user.name?.split(' ')[0]}</Link>
                <button className="btn btn-ghost btn-sm" onClick={() => { logout(); nav('/welcome'); }}>Logout</button>
              </>
            ) : (
              <>
                <Link className="btn btn-ghost btn-sm" to="/login">Log in</Link>
                <Link className="btn btn-primary btn-sm" to="/signup">Get started</Link>
              </>
            )}
          </div>
        </div>
      </div>
      {user && (
        <nav className="bottomnav">
          {[...LINKS, ['/ai', 'AI', '✨']].map(([to, label, ico]) => (
            <Link key={to} to={to} className={loc.pathname === to ? 'active' : ''}>
              <span className="ico">{ico}</span>{label}
            </Link>
          ))}
        </nav>
      )}
      {user && (
        <>
          <button className="fab" onClick={() => setAiOpen(true)} aria-label="Open FoodMate AI">✨</button>
          {aiOpen && <AIDrawer onClose={() => setAiOpen(false)} />}
        </>
      )}
    </>
  );
}
