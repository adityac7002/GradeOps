import { useAuth } from '../contexts/AuthContext';
import { LayoutDashboard, Plus, CheckSquare, ShieldAlert, LogOut, Cpu } from 'lucide-react';

export function Navbar({ activePage, setPage }) {
  const { user, logout } = useAuth();

  const NavItem = ({ id, icon: Icon, label }) => {
    const isActive = activePage === id;
    return (
      <button
        onClick={() => setPage(id)}
        className={`flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg transition-all duration-150 ${
          isActive
            ? 'bg-accent text-white shadow-sm'
            : 'text-text2 hover:text-text hover:bg-surface2'
        }`}
      >
        <Icon size={15} className={isActive ? 'text-white' : 'text-text3'} />
        {label}
      </button>
    );
  };

  return (
    <nav className="h-[58px] bg-surface/90 backdrop-blur-md border-b border-border flex items-center justify-between px-6 sticky top-0 z-50 shadow-xs">
      {/* Left — brand + nav */}
      <div className="flex items-center gap-6">
        <button onClick={() => setPage('dashboard')} className="flex items-center gap-2.5 group">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center text-white text-xs font-bold shadow-sm"
            style={{ background: 'linear-gradient(135deg, #4F46E5, #7C3AED)' }}>
            <Cpu size={14} />
          </div>
          <span className="font-semibold text-[15px] tracking-tight text-text hidden sm:block">GradeOps</span>
          <span className="badge badge-indigo hidden sm:flex">AI</span>
        </button>

        <div className="h-5 w-px bg-border hidden sm:block" />

        <div className="flex items-center gap-1">
          {user?.role === 'instructor' && (
            <>
              <NavItem id="dashboard" icon={LayoutDashboard} label="Overview" />
              <NavItem id="upload"    icon={Plus}            label="New Pipeline" />
            </>
          )}
          {user?.role === 'ta' && (
            <>
              <NavItem id="dashboard"  icon={CheckSquare}  label="Review Queue" />
              <NavItem id="plagiarism" icon={ShieldAlert}  label="Similarity" />
            </>
          )}
        </div>
      </div>

      {/* Right — user + logout */}
      <div className="flex items-center gap-3">
        <div className="hidden sm:flex flex-col items-end">
          <span className="text-[13px] font-semibold text-text leading-tight">
            {user?.full_name || user?.email?.split('@')[0]}
          </span>
          <span className="text-[10px] font-medium uppercase tracking-widest text-text3 mt-0.5">
            {user?.role === 'instructor' ? 'Instructor' : 'Teaching Assistant'}
          </span>
        </div>
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-sm"
          style={{ background: 'linear-gradient(135deg, #4F46E5, #7C3AED)' }}
        >
          {(user?.full_name || user?.email || '?')[0].toUpperCase()}
        </div>
        <div className="w-px h-5 bg-border" />
        <button
          onClick={logout}
          title="Sign out"
          className="btn btn-ghost btn-sm !px-2 text-text3 hover:text-danger hover:bg-red-50"
        >
          <LogOut size={15} />
        </button>
      </div>
    </nav>
  );
}
