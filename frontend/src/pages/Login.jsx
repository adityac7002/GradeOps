import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Spinner } from '../ui';

export default function Login() {
  const { login } = useAuth();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async e => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      await login(form.email, form.password);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const quickLogin = (email, pass) => {
    setForm({ email, password: pass });
  };

  return (
    <div className="min-h-screen flex bg-[#0a0a0f] font-sans selection:bg-accent-glow">
      
      {/* LEFT PANE - MARKETING / BRANDING */}
      <div className="hidden lg:flex w-1/2 bg-[#111118] border-r border-[#2a2a3a] flex-col justify-between p-12 relative overflow-hidden">
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
                <p className="text-[#5a5a78] text-sm leading-relaxed">Automate evaluation using Gemini 2.5 Flash Vision models directly on scanned images.</p>
              </div>
            </div>
            <div className="flex gap-4 items-start">
              <div className="w-8 h-8 rounded bg-[#1a1a25] border border-[#2a2a3a] flex items-center justify-center text-accent shrink-0 mt-1">👁</div>
              <div>
                <h3 className="text-white font-semibold mb-1">Human-in-the-Loop Review</h3>
                <p className="text-[#5a5a78] text-sm leading-relaxed">Keyboard-first TA dashboard for high-speed overrides, approvals, and confidence checks.</p>
              </div>
            </div>
          </div>
        </div>

        <div className="relative z-10 flex items-center justify-between text-xs text-[#5a5a78] font-mono">
          <span>© 2026 GradeOps Infrastructure</span>
          <span>v2.0.0-hackathon</span>
        </div>
      </div>

      {/* RIGHT PANE - AUTH FORM */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 relative">
        <div className="w-full max-w-md">
          <div className="mb-10 text-center lg:text-left">
            <h2 className="text-3xl font-bold text-white tracking-tight mb-2">Welcome back</h2>
            <p className="text-[#9898b8]">Enter your institutional credentials to access your dashboard.</p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
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
              {loading ? <Spinner /> : 'Authenticate'}
            </button>
          </form>

          {/* QUICK ACCESS PANEL FOR DEMO */}
          <div className="mt-12 p-6 bg-[#111118] border border-[#2a2a3a] rounded-xl">
            <h4 className="text-xs uppercase tracking-widest text-accent font-mono mb-4">Quick Access (Demo Seed)</h4>
            <div className="flex flex-col gap-3">
              <button 
                onClick={() => quickLogin('admin@gradeops.com', 'admin123')}
                className="flex items-center justify-between p-3 bg-[#1a1a25] border border-[#2a2a3a] rounded-lg hover:border-accent transition-all group"
              >
                <div className="text-left">
                  <div className="text-sm font-medium text-white">Instructor Access</div>
                  <div className="text-[10px] text-[#5a5a78] font-mono mt-0.5">admin@gradeops.com / admin123</div>
                </div>
                <span className="text-lg opacity-0 group-hover:opacity-100 transition-opacity">→</span>
              </button>
              <button 
                onClick={() => quickLogin('ta@gradeops.com', 'ta123')}
                className="flex items-center justify-between p-3 bg-[#1a1a25] border border-[#2a2a3a] rounded-lg hover:border-accent transition-all group"
              >
                <div className="text-left">
                  <div className="text-sm font-medium text-white">TA Reviewer Access</div>
                  <div className="text-[10px] text-[#5a5a78] font-mono mt-0.5">ta@gradeops.com / ta123</div>
                </div>
                <span className="text-lg opacity-0 group-hover:opacity-100 transition-opacity">→</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
