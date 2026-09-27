import { createContext, useContext, useEffect, useState } from 'react';
import { api, getToken, setToken } from '../api';

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    if (!getToken()) { setUser(null); setLoading(false); return; }
    try {
      const me = await api('/api/auth/me');
      setUser(me);
    } catch { setToken(''); setUser(null); }
    setLoading(false);
  };

  useEffect(() => { refresh(); }, []);

  const login = async (email, password) => {
    const r = await api('/api/auth/register'.replace('/register', '/login'), { method: 'POST', body: { email, password }, auth: false });
    setToken(r.token); setUser(r.user);
    await refresh();
  };
  const register = async (payload) => {
    const r = await api('/api/auth/register', { method: 'POST', body: payload, auth: false });
    setToken(r.token); setUser(r.user);
    await refresh();
  };
  const logout = () => { setToken(''); setUser(null); };

  return <Ctx.Provider value={{ user, loading, login, register, logout, refresh }}>{children}</Ctx.Provider>;
}
