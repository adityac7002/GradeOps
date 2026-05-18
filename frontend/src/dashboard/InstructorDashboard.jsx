import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import {
  FileText, Activity, CheckCircle2, AlertCircle, Plus, ChevronRight,
  Clock, BarChart3, Cpu, ArrowUpRight, Layers, Zap
} from 'lucide-react';

const STATUS = {
  complete:   { label: 'Complete',   cls: 'badge-green',  dot: 'bg-green-500',  icon: CheckCircle2 },
  processing: { label: 'Processing', cls: 'badge-blue',   dot: 'bg-blue-500',   icon: Activity     },
  grading:    { label: 'Grading',    cls: 'badge-indigo', dot: 'bg-indigo-500', icon: Cpu          },
  pending:    { label: 'Pending',    cls: 'badge-gray',   dot: 'bg-gray-400',   icon: Clock        },
  failed:     { label: 'Failed',     cls: 'badge-red',    dot: 'bg-red-500',    icon: AlertCircle  },
};

function StatCard({ icon: Icon, label, value, sub, color }) {
  return (
    <div className="card card-hover p-5 flex items-start justify-between group cursor-default">
      <div>
        <p className="caption mb-1">{label}</p>
        <p className="text-3xl font-bold tracking-tight text-text">{value}</p>
        {sub && <p className="text-xs text-text3 mt-1.5">{sub}</p>}
      </div>
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color} shrink-0 group-hover:scale-110 transition-transform`}>
        <Icon size={18} />
      </div>
    </div>
  );
}

function PipelineRow({ exam, onReview, onAnalytics }) {
  const s = STATUS[exam.status] || STATUS.pending;
  const IconComp = s.icon;
  return (
    <tr className="hover:bg-surface2/40 transition-colors group cursor-pointer" onClick={() => onReview(exam)}>
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-accent-muted border border-indigo-100 flex items-center justify-center shrink-0">
            <FileText size={15} className="text-accent" />
          </div>
          <div>
            <div className="font-semibold text-text text-[13.5px]">{exam.title}</div>
            <div className="text-xs text-text3 mt-0.5 font-mono">ID #{exam.id}</div>
          </div>
        </div>
      </td>
      <td className="px-6 py-4">
        <span className={`badge ${s.cls}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${s.dot} ${exam.status === 'processing' ? 'animate-pulse-dot' : ''}`} />
          {s.label}
        </span>
      </td>
      <td className="px-6 py-4 text-sm text-text2">
        {new Date(exam.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
      </td>
      <td className="px-6 py-4 text-right">
        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          {exam.status === 'complete' && (
            <button className="btn btn-sm btn-ghost text-accent" onClick={e => { e.stopPropagation(); onAnalytics(exam); }}>
              <BarChart3 size={13} /> Analytics
            </button>
          )}
          <button className="btn btn-sm btn-outline" onClick={e => { e.stopPropagation(); onReview(exam); }}>
            {exam.status === 'complete' ? 'Results' : 'Inspect'}
            <ChevronRight size={13} />
          </button>
        </div>
      </td>
    </tr>
  );
}

export default function InstructorDashboard({ setPage, setSelectedExam }) {
  const { authFetch } = useAuth();
  const { addToast } = useToast();
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authFetch('/api/exams')
      .then(r => r.json())
      .then(data => setExams(Array.isArray(data) ? data : (data.items ?? [])))
      .catch(() => addToast('Failed to load exams', 'error'))
      .finally(() => setLoading(false));
  }, []);

  const go = (exam, page) => { setSelectedExam(exam); setPage(page); };
  const total = exams.length;
  const complete   = exams.filter(e => e.status === 'complete').length;
  const processing = exams.filter(e => ['processing','grading'].includes(e.status)).length;

  return (
    <div className="page-wrapper py-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-10 animate-in fade-in duration-300">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <Layers size={20} className="text-accent" />
            <h1 className="text-2xl font-bold tracking-tight text-text">Operations Center</h1>
          </div>
          <p className="text-sm text-text2 ml-7">Manage AI grading pipelines and monitor evaluation progress.</p>
        </div>
        <button onClick={() => setPage('upload')} className="btn btn-primary shrink-0"
          style={{ background: 'linear-gradient(135deg, #4F46E5, #7C3AED)' }}>
          <Plus size={15} /> New Pipeline
        </button>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8 animate-in slide-in-from-bottom-4 duration-300">
        <StatCard icon={Layers}       label="Total Pipelines"    value={total}      sub={`${complete} completed`}         color="bg-indigo-50 text-indigo-600" />
        <StatCard icon={Activity}     label="Active Processing"  value={processing} sub="Running AI grading jobs"         color="bg-blue-50 text-blue-600" />
        <StatCard icon={CheckCircle2} label="Fully Evaluated"    value={complete}   sub="Ready for TA review"             color="bg-emerald-50 text-emerald-600" />
      </div>

      {/* Pipeline table */}
      <div className="card overflow-hidden !p-0 animate-in slide-in-from-bottom-4 duration-500">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-surface">
          <div className="flex items-center gap-2.5">
            <Zap size={15} className="text-accent" />
            <h2 className="text-sm font-semibold text-text">Evaluation Pipelines</h2>
            <span className="badge badge-gray">{total}</span>
          </div>
          <button onClick={() => setPage('upload')} className="btn btn-sm btn-outline">
            <Plus size={12} /> New
          </button>
        </div>

        {loading ? (
          <div className="p-6 space-y-3">
            {[1,2,3].map(i => (
              <div key={i} className="h-14 rounded-lg animate-shimmer" />
            ))}
          </div>
        ) : exams.length === 0 ? (
          /* Empty state */
          <div className="py-20 flex flex-col items-center justify-center text-center px-6">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5 border border-indigo-100"
              style={{ background: 'linear-gradient(135deg, #EEF2FF, #E0E7FF)' }}>
              <FileText size={24} className="text-accent" />
            </div>
            <h3 className="text-base font-semibold text-text mb-2">No pipelines yet</h3>
            <p className="text-sm text-text2 max-w-xs mb-6">
              Upload a scanned exam PDF and define your grading rubric to start the AI evaluation pipeline.
            </p>
            <button onClick={() => setPage('upload')} className="btn btn-primary"
              style={{ background: 'linear-gradient(135deg, #4F46E5, #7C3AED)' }}>
              <Plus size={14} /> Create First Pipeline
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="table-header">Pipeline</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Created</th>
                  <th className="table-header text-right pr-6">Actions</th>
                </tr>
              </thead>
              <tbody>
                {exams.map(exam => (
                  <PipelineRow
                    key={exam.id}
                    exam={exam}
                    onReview={e => go(e, 'review')}
                    onAnalytics={e => go(e, 'analytics')}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quick tips footer */}
      {exams.length > 0 && (
        <div className="mt-6 p-4 rounded-xl border border-indigo-100 bg-indigo-50/60 flex items-center gap-3 animate-in fade-in duration-500">
          <Cpu size={16} className="text-accent shrink-0" />
          <p className="text-xs text-indigo-700">
            <span className="font-semibold">Tip:</span> Click any pipeline row to open the review queue. Use the Analytics button to see score distributions.
          </p>
          <button onClick={() => setPage('upload')} className="ml-auto btn btn-sm text-accent border-indigo-200 bg-white hover:bg-indigo-50 shrink-0">
            New <ArrowUpRight size={11} />
          </button>
        </div>
      )}
    </div>
  );
}
