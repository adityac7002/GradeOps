import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Mail, Lock, Loader2, ArrowRight, Cpu, Zap, Shield, BarChart3 } from 'lucide-react';

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await login(email, password);
    } catch (err) {
      setError(err.message || 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  const features = [
    { icon: Zap,       label: 'AI-powered grading',    sub: 'Gemini & Llama 3.2 vision' },
    { icon: Shield,    label: 'Plagiarism detection',  sub: 'TF-IDF similarity scoring' },
    { icon: BarChart3, label: 'Analytics & insights',  sub: 'Score distributions, trends' },
    { icon: Cpu,       label: 'Human-in-the-loop',     sub: 'TA override & review panel' },
  ];

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--color-background)' }}>

      {/* ── Left branding panel ─────────────────────────────────────── */}
      <div className="hidden lg:flex lg:w-[460px] xl:w-[520px] flex-col justify-between p-10 relative overflow-hidden"
        style={{
          background: 'linear-gradient(155deg, #0D0F1E 0%, #11133A 40%, #1A0E2E 100%)',
          borderRight: '1px solid rgba(99,102,241,0.15)'
        }}>

        {/* Subtle mesh grid */}
        <div className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: 'linear-gradient(rgba(99,102,241,.6) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,.6) 1px, transparent 1px)',
            backgroundSize: '48px 48px'
          }} />

        {/* Glow orbs */}
        <div className="absolute -top-32 -left-32 w-64 h-64 rounded-full opacity-20"
          style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.6) 0%, transparent 70%)' }} />
        <div className="absolute bottom-0 right-0 w-96 h-96 rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, rgba(139,92,246,0.8) 0%, transparent 70%)' }} />

        {/* Top section */}
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-14">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center border"
              style={{ background: 'rgba(99,102,241,0.15)', borderColor: 'rgba(99,102,241,0.3)' }}>
              <Cpu size={18} style={{ color: '#A5B4FC' }} />
            </div>
            <span className="text-white font-semibold text-lg tracking-tight">GradeOps</span>
            <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold"
              style={{ background: 'rgba(99,102,241,0.2)', color: '#A5B4FC', border: '1px solid rgba(99,102,241,0.35)' }}>
              AI
            </span>
          </div>

          <h2 className="text-[2rem] font-bold text-white leading-tight mb-4 tracking-tight">
            Academic evaluation,<br />
            <span style={{ background: 'linear-gradient(135deg, #A5B4FC, #C4B5FD)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              redefined.
            </span>
          </h2>
          <p style={{ color: '#8B91B0' }} className="text-sm leading-relaxed max-w-xs">
            AI-assisted handwritten exam grading platform built for universities. Trusted by faculty, loved by TAs.
          </p>
        </div>

        {/* Feature list */}
        <div className="relative z-10 space-y-2.5">
          {features.map(({ icon: Icon, label, sub }) => (
            <div key={label} className="flex items-center gap-3.5 p-3.5 rounded-xl"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: 'rgba(99,102,241,0.2)', border: '1px solid rgba(99,102,241,0.25)' }}>
                <Icon size={14} style={{ color: '#A5B4FC' }} />
              </div>
              <div>
                <div className="text-sm font-medium text-white">{label}</div>
                <div className="text-xs" style={{ color: '#525870' }}>{sub}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right form panel ─────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col items-center justify-center p-8"
        style={{ background: 'var(--color-background)' }}>
        <div className="w-full max-w-[380px]">

          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white"
              style={{ background: 'linear-gradient(135deg, #6366F1, #8B5CF6)' }}>
              <Cpu size={16} />
            </div>
            <span className="font-semibold text-lg" style={{ color: 'var(--color-text)' }}>GradeOps</span>
          </div>

          <h1 className="text-2xl font-bold tracking-tight mb-1" style={{ color: 'var(--color-text)' }}>Sign in</h1>
          <p className="text-sm mb-8" style={{ color: 'var(--color-text2)' }}>Enter your credentials to access the platform.</p>

          {error && (
            <div className="mb-5 p-3.5 rounded-lg text-sm flex items-center gap-2 animate-in fade-in duration-200"
              style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)', color: '#FCA5A5' }}>
              <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: '#EF4444' }} />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label block mb-1.5">Email address</label>
              <div className="relative">
                <Mail size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--color-text3)' }} />
                <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
                  className="form-input pl-9" placeholder="you@university.edu" autoComplete="email" />
              </div>
            </div>
            <div>
              <label className="label block mb-1.5">Password</label>
              <div className="relative">
                <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--color-text3)' }} />
                <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
                  className="form-input pl-9" placeholder="••••••••" autoComplete="current-password" />
              </div>
            </div>
            <button type="submit" disabled={loading} className="btn btn-primary btn-lg w-full mt-2">
              {loading
                ? <Loader2 size={16} className="animate-spin" />
                : <><span>Sign in</span><ArrowRight size={15} /></>
              }
            </button>
          </form>

          <div className="flex items-center gap-3 my-7">
            <div className="h-px flex-1" style={{ background: 'var(--color-border)' }} />
            <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: 'var(--color-text3)' }}>Demo access</span>
            <div className="h-px flex-1" style={{ background: 'var(--color-border)' }} />
          </div>

          <div className="space-y-2">
            {[
              { email: 'admin@gradeops.com', password: 'admin123', role: 'Instructor', initial: 'I', color: '#6366F1' },
              { email: 'ta@gradeops.com',    password: 'ta123',    role: 'Teaching Assistant', initial: 'T', color: '#8B5CF6' },
            ].map(({ email: e, password: p, role, initial, color }) => (
              <button key={e} type="button" onClick={() => { setEmail(e); setPassword(p); }}
                className="w-full p-3 rounded-xl flex items-center justify-between group transition-all"
                style={{
                  background: 'var(--color-surface)',
                  border: '1px solid var(--color-border)',
                }}
                onMouseEnter={el => { el.currentTarget.style.borderColor = 'var(--color-border2)'; el.currentTarget.style.background = 'var(--color-surface2)'; }}
                onMouseLeave={el => { el.currentTarget.style.borderColor = 'var(--color-border)'; el.currentTarget.style.background = 'var(--color-surface)'; }}
              >
                <div className="flex items-center gap-3">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center text-white text-xs font-bold"
                    style={{ background: color }}>
                    {initial}
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>{role}</div>
                    <div className="text-xs font-mono" style={{ color: 'var(--color-text3)' }}>{e}</div>
                  </div>
                </div>
                <ArrowRight size={14} style={{ color: 'var(--color-text3)' }} />
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
