import { useAuth } from '../contexts/AuthContext';

export function Navbar({ activePage, setPage }) {
  const { user, logout } = useAuth();

  return (
    <nav className="h-[60px] bg-[#0a0a0f] border-b border-[#2a2a3a] flex items-center justify-between px-6 sticky top-0 z-50 shadow-sm">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-accent rounded flex items-center justify-center text-white font-bold text-lg shadow-[0_0_15px_rgba(124,106,247,0.4)]">G</div>
          <span className="text-white font-bold text-xl tracking-tight hidden sm:block">GradeOps<span className="text-accent">.</span></span>
        </div>

        <div className="h-6 w-[1px] bg-[#2a2a3a] hidden sm:block mx-2"></div>

        {user?.role === 'instructor' && (
          <div className="flex items-center gap-1">
            <button 
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-2 ${activePage === 'dashboard' ? 'bg-[#1a1a25] text-white border border-[#3a3a50]' : 'text-[#9898b8] hover:text-white hover:bg-[#111118]'}`} 
              onClick={() => setPage('dashboard')}
            >
              <span className="opacity-70">📊</span> Ops Center
            </button>
            <button 
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-2 ${activePage === 'upload' ? 'bg-[#1a1a25] text-white border border-[#3a3a50]' : 'text-[#9898b8] hover:text-white hover:bg-[#111118]'}`} 
              onClick={() => setPage('upload')}
            >
              <span className="opacity-70">➕</span> New Pipeline
            </button>
          </div>
        )}

        {user?.role === 'ta' && (
          <div className="flex items-center gap-1">
            <button 
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-2 ${activePage === 'dashboard' || activePage === 'review' ? 'bg-[#1a1a25] text-white border border-[#3a3a50]' : 'text-[#9898b8] hover:text-white hover:bg-[#111118]'}`} 
              onClick={() => setPage('dashboard')}
            >
              <span className="opacity-70">✅</span> Review Queue
            </button>
            <button 
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-2 ${activePage === 'plagiarism' ? 'bg-[#1a1a25] text-white border border-[#3a3a50]' : 'text-[#9898b8] hover:text-white hover:bg-[#111118]'}`} 
              onClick={() => setPage('plagiarism')}
            >
              <span className="opacity-70">🔍</span> Plagiarism
            </button>
          </div>
        )}
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="flex flex-col items-end hidden sm:flex">
            <span className="text-sm text-white font-medium">{user?.full_name}</span>
            <span className={`text-[10px] uppercase tracking-widest font-mono font-bold mt-0.5 ${user?.role === 'instructor' ? 'text-accent' : 'text-blue-400'}`}>
              {user?.role}
            </span>
          </div>
          <div className="w-8 h-8 rounded-full bg-[#1a1a25] border border-[#3a3a50] flex items-center justify-center text-white text-sm font-bold shadow-sm">
            {user?.full_name?.[0] ?? '?'}
          </div>
        </div>
        <div className="h-6 w-[1px] bg-[#2a2a3a]"></div>
        <button 
          className="text-[#5a5a78] hover:text-red-400 transition-colors p-1" 
          onClick={logout} 
          title="Sign out"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>
        </button>
      </div>
    </nav>
  );
}
