import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Spinner } from '../ui';

export default function Login() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [form, setForm] = useState({ email: '', password: '', full_name: '', role: 'ta' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async e => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      if (mode === 'login') {
        await login(form.email, form.password);
      } else {
        await register({ email: form.email, password: form.password, full_name: form.full_name, role: form.role });
        await login(form.email, form.password);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-[#0a0a0f] font-sans selection:bg-accent-glow">
      
      {/* LEFT PANE - MARKETING / BRANDING */}
      <div className="hidden lg:flex w-1/2 bg-[#111118] border-r border-[#2a2a3a] flex-col justify-between p-12 relative overflow-hidden">
        {/* Animated Background Gradients */}
        <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
          <div className="absolute -top-[20%] -left-[10%] w-[70%] h-[70%] rounded-full bg-accent/10 blur-[120px] mix-blend-screen" />
          <div className="absolute top-[40%] -right-[20%] w-[60%] h-[60%] rounded-full bg-[#22c55e]/5 blur-[120px] mix-blend-screen" />
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTTAgNDBoNDBWMEgwem0zOS0zOUgxVjM5aDM4eiIgZmlsbD0iIzFBMUEyNSIgZmlsbC1vcGFjaXR5PSIwLjUiLz48L3BhdHRlcm4+PC9kZWZzPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9InVybCgjZ3JpZCkiLz48L3N2Zz4=')] opacity-20 mask-image:linear-gradient(to_bottom,white,transparent)" />
        </div>

        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-16">
            <div className="w-10 h-10 bg-accent rounded-lg flex items-center justify-center text-white font-bold text-xl shadow-[0_0_20px_rgba(124,106,247,0.5)]">G</div>
            <span className="text-white font-bold text-2xl tracking-tight">GradeOps<span className="text-accent">.</span></span>
          </div>
          
          <h1 className="text-5xl font-bold text-white leading-[1.1] tracking-tight mb-6">
            Institutional-grade <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent to-[#a78bfa]">AI evaluation.</span>
          </h1>
          <p className="text-[#9898b8] text-lg max-w-md leading-relaxed mb-12">
            Accelerate grading workflows with precision Vision AI, human-in-the-loop oversight, and structured rubric pipelines.
          </p>

          <div className="flex flex-col gap-8">
            <div className="flex gap-4 items-start">
              <div className="w-8 h-8 rounded bg-[#1a1a25] border border-[#2a2a3a] flex items-center justify-center text-accent shrink-0 mt-1">🤖</div>
              <div>
                <h3 className="text-white font-semibold mb-1">AI-Powered Grading Pipeline</h3>
                <p className="text-[#5a5a78] text-sm leading-relaxed">Automate OCR and apply intelligent partial credit using state-of-the-art vision models.</p>
              </div>
            </div>
            <div className="flex gap-4 items-start">
              <div className="w-8 h-8 rounded bg-[#1a1a25] border border-[#2a2a3a] flex items-center justify-center text-accent shrink-0 mt-1">👁</div>
              <div>
                <h3 className="text-white font-semibold mb-1">Human-in-the-Loop Review</h3>
                <p className="text-[#5a5a78] text-sm leading-relaxed">Keyboard-first TA dashboard for high-speed overrides, approvals, and confidence checks.</p>
              </div>
            </div>
            <div className="flex gap-4 items-start">
              <div className="w-8 h-8 rounded bg-[#1a1a25] border border-[#2a2a3a] flex items-center justify-center text-accent shrink-0 mt-1">📊</div>
              <div>
                <h3 className="text-white font-semibold mb-1">Analytics & Plagiarism Ops</h3>
                <p className="text-[#5a5a78] text-sm leading-relaxed">Dense operational dashboards to track queue progress and flag high-similarity submissions.</p>
              </div>
            </div>
          </div>
        </div>

        <div className="relative z-10 flex items-center justify-between text-xs text-[#5a5a78] font-mono">
          <span>© 2026 GradeOps Infrastructure</span>
          <span>v2.0.0-enterprise</span>
        </div>
      </div>

      {/* RIGHT PANE - AUTH FORM */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 relative">
        {/* Mobile Logo */}
        <div className="absolute top-8 left-8 lg:hidden flex items-center gap-2">
          <div className="w-8 h-8 bg-accent rounded-md flex items-center justify-center text-white font-bold">G</div>
          <span className="text-white font-bold text-xl tracking-tight">GradeOps</span>
        </div>

        <div className="w-full max-w-md">
          <div className="mb-10 text-center lg:text-left">
            <h2 className="text-3xl font-bold text-white tracking-tight mb-2">
              {mode === 'login' ? 'Welcome back' : 'Create an account'}
            </h2>
            <p className="text-[#9898b8]">
              {mode === 'login' ? 'Enter your credentials to access your dashboard.' : 'Join the operational evaluation platform.'}
            </p>
          </div>

          <div className="flex bg-[#111118] border border-[#2a2a3a] rounded-lg p-1 mb-8">
            <button 
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${mode === 'login' ? 'bg-[#2a2a3a] text-white shadow-sm' : 'text-[#5a5a78] hover:text-white'}`} 
              onClick={() => { setMode('login'); setError(''); }}
            >
              Sign In
            </button>
            <button 
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${mode === 'register' ? 'bg-[#2a2a3a] text-white shadow-sm' : 'text-[#5a5a78] hover:text-white'}`} 
              onClick={() => { setMode('register'); setError(''); }}
            >
              Register
            </button>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            {mode === 'register' && (
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#9898b8] mb-2 font-semibold">Full Name</label>
                <input 
                  className="w-full bg-[#111118] border border-[#2a2a3a] rounded-md px-4 py-3 text-white text-sm focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all placeholder-[#5a5a78]" 
                  type="text" placeholder="Dr. Jane Smith" value={form.full_name} onChange={set('full_name')} required 
                />
              </div>
            )}

            <div>
              <label className="block text-xs uppercase tracking-wider text-[#9898b8] mb-2 font-semibold">Institutional Email</label>
              <input 
                className="w-full bg-[#111118] border border-[#2a2a3a] rounded-md px-4 py-3 text-white text-sm focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all placeholder-[#5a5a78]" 
                type="email" placeholder="you@university.edu" value={form.email} onChange={set('email')} required 
              />
            </div>

            <div>
              <label className="block text-xs uppercase tracking-wider text-[#9898b8] mb-2 font-semibold">Password</label>
              <input 
                className="w-full bg-[#111118] border border-[#2a2a3a] rounded-md px-4 py-3 text-white text-sm focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all placeholder-[#5a5a78] tracking-widest" 
                type="password" placeholder="••••••••" value={form.password} onChange={set('password')} required 
              />
            </div>

            {mode === 'register' && (
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#9898b8] mb-2 font-semibold">System Role</label>
                <select 
                  className="w-full bg-[#111118] border border-[#2a2a3a] rounded-md px-4 py-3 text-white text-sm focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all appearance-none cursor-pointer" 
                  value={form.role} onChange={set('role')}
                >
                  <option value="ta">Teaching Assistant (Reviewer)</option>
                  <option value="instructor">Instructor (Admin)</option>
                </select>
              </div>
            )}

            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-500 text-sm rounded-md font-mono flex items-start gap-2">
                <span className="text-red-500 mt-0.5">🚨</span> {error}
              </div>
            )}

            <button 
              type="submit" 
              className="mt-4 w-full bg-white text-black font-semibold py-3 rounded-md hover:bg-gray-200 transition-all shadow-[0_0_20px_rgba(255,255,255,0.1)] flex justify-center items-center h-[48px]" 
              disabled={loading}
            >
              {loading ? <Spinner /> : (mode === 'login' ? 'Authenticate' : 'Provision Account')}
            </button>
          </form>

          {mode === 'login' && (
            <div className="mt-8 text-center text-sm text-[#5a5a78]">
              <a href="#" className="hover:text-white transition-colors underline underline-offset-4 decoration-[#2a2a3a]">Forgot your password?</a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
