import { useEffect, useRef, useState } from 'react';
import { api } from '../api';

// Persistent assistant: text + voice (Web Speech API) + image upload (vision endpoint w/ uncertainty).
export default function AIDrawer({ onClose, initial = '' }) {
  const [msgs, setMsgs] = useState([{ role: 'ai', content: 'Hey! Tell me your mood, budget, time and what\u2019s in your kitchen — e.g. “tired, spicy, high-protein under \u20B9100, I have rice eggs onions, no paneer”.' }]);
  const [input, setInput] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [recs, setRecs] = useState([]);
  const recRef = useRef(null);
  const chatRef = useRef(null);

  useEffect(() => { chatRef.current?.scrollTo(0, 99999); }, [msgs]);
  useEffect(() => {
    api('/api/ai/history').then(h => {
      if (h?.length) setMsgs(h.slice(-12).map(m => ({ role: m.role === 'user' ? 'user' : 'ai', content: m.content })));
    }).catch(() => {});
  }, []);

  const speak = (text) => {
    try {
      if (!('speechSynthesis' in window)) return;
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text.replace(/[*#]/g, '').slice(0, 400));
      window.speechSynthesis.speak(u);
    } catch {}
  };

  const send = async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || busy) return;
    setInput('');
    setMsgs(m => [...m, { role: 'user', content: msg }]);
    setBusy(true);
    try {
      const r = await api('/api/ai/chat', { method: 'POST', body: { message: msg, servings: 2 } });
      setMsgs(m => [...m, { role: 'ai', content: r.reply }]);
      setRecs(r.recommendations || []);
      speak(r.reply);
    } catch (e) {
      setMsgs(m => [...m, { role: 'ai', content: 'Sorry, I hit a snag: ' + e.message + '. Please retry.' }]);
    }
    setBusy(false);
  };

  const toggleListen = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { alert('Voice input is not supported in this browser. Try Chrome.'); return; }
    if (listening) { recRef.current?.stop(); setListening(false); return; }
    const rec = new SR();
    rec.lang = 'en-IN';
    rec.interimResults = false;
    rec.onresult = (e) => { const t = e.results[0][0].transcript; setInput(t); send(t); };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recRef.current = rec;
    rec.start();
    setListening(true);
  };

  const onImage = async (file) => {
    if (!file) return;
    setMsgs(m => [...m, { role: 'user', content: `📷 Shared an image: ${file.name}` }]);
    setBusy(true);
    try {
      // Prototype vision: user confirms what is visible; labels sent for matching.
      const label = window.prompt('What ingredients do you see in this photo? (comma-separated, e.g. rice, eggs, onion)', 'rice, eggs, onion');
      const labels = (label || '').split(',').map(s => s.trim()).filter(Boolean);
      const r = await api('/api/ai/vision', { method: 'POST', body: { labels, description: label || '' } });
      const det = (r.detected || []).map(d => `${d.label} (${Math.round(d.confidence * 100)}%${d.needs_confirmation ? ', please confirm' : ''})`).join(', ');
      setMsgs(m => [...m, { role: 'ai', content: `${r.advice}\n\nDetected: ${det || 'nothing confident'}\n\n${r.disclaimer}` }]);
      setRecs(r.recommendations || []);
    } catch (e) {
      setMsgs(m => [...m, { role: 'ai', content: 'Image analysis failed: ' + e.message }]);
    }
    setBusy(false);
  };

  return (
    <>
      <div className="overlay" onClick={onClose} />
      <div className="drawer" role="dialog" aria-label="FoodMate AI assistant">
        <div className="drawer-head">
          <span style={{ fontSize: 26 }}>✨</span>
          <div style={{ flex: 1 }}>
            <strong>FoodMate AI</strong>
            <div className="small">Text · Voice · Image — understands mood, budget & kitchen</div>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="chat" ref={chatRef}>
          {msgs.map((m, i) => <div key={i} className={`msg ${m.role}`}>{m.content}</div>)}
          {recs.length > 0 && (
            <div className="panel" style={{ padding: 12 }}>
              <strong style={{ fontSize: 13 }}>Top picks for you</strong>
              {recs.map(r => (
                <div key={r.id} style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 8 }}>
                  <span style={{ fontSize: 24 }}>{r.image_emoji}</span>
                  <div style={{ flex: 1, fontSize: 13 }}><strong>{r.name}</strong><br />
                    <span className="small">{r.time_min} min · cook ₹{Math.round(r.cost_cook)} · {Math.round(r.protein_g)}g protein</span></div>
                  <a className="btn btn-primary btn-sm" href={`#/meals/${r.id}`} onClick={onClose}>View</a>
                </div>
              ))}
            </div>
          )}
          {busy && <div className="msg ai"><span className="skel" style={{ display: 'inline-block', width: 120, height: 14 }} /> thinking…</div>}
        </div>
        <div className="chat-input">
          <button className={`icon-btn ${listening ? 'live' : ''}`} onClick={toggleListen} title="Voice input" aria-label="Voice input">🎤</button>
          <label className="icon-btn" title="Upload fridge/ingredient photo" aria-label="Upload image" style={{ cursor: 'pointer' }}>
            📷<input type="file" accept="image/*" capture="environment" hidden onChange={(e) => onImage(e.target.files[0])} />
          </label>
          <input className="input" value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
            placeholder="Type naturally — mood, budget, time…" aria-label="Message FoodMate AI" />
          <button className="btn btn-primary" onClick={() => send()} disabled={busy}>Send</button>
        </div>
      </div>
    </>
  );
}
