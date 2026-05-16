import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Badge, Spinner } from '../ui';

export default function InstructorDashboard({ setPage, setSelectedExam }) {
  const { authFetch } = useAuth();
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadExams = () => {
    authFetch('/api/exams')
      .then(r => r.json())
      .then(setExams)
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadExams(); }, []);

  const openReview = (exam) => {
    setSelectedExam(exam);
    setPage('review');
  };

  if (loading) return (
    <div className="flex-1 flex items-center justify-center text-[#5a5a78] gap-3 h-[80vh]">
      <Spinner />
      <span className="font-mono text-xs uppercase tracking-widest">Loading Pipelines...</span>
    </div>
  );

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <header className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Operation Control</h1>
          <p className="text-[#9898b8] mt-1">Institutional-grade evaluation pipelines and VLM queues.</p>
        </div>
        <button 
          className="bg-white text-black px-6 py-3 rounded-xl font-bold hover:bg-gray-200 transition-all shadow-xl flex items-center gap-2"
          onClick={() => setPage('upload')}
        >
          <span className="text-xl">+</span> New Pipeline
        </button>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <div className="bg-[#111118] border border-[#2a2a3a] p-6 rounded-2xl">
          <div className="text-xs font-mono text-accent uppercase tracking-widest mb-2">Active Exams</div>
          <div className="text-4xl font-bold text-white">{exams.length}</div>
        </div>
        <div className="bg-[#111118] border border-[#2a2a3a] p-6 rounded-2xl">
          <div className="text-xs font-mono text-[#22c55e] uppercase tracking-widest mb-2">Queue Status</div>
          <div className="text-4xl font-bold text-white">
            {exams.filter(e => e.status === 'processing').length > 0 ? 'Busy' : 'Idle'}
          </div>
        </div>
        <div className="bg-accent/10 border border-accent/20 p-6 rounded-2xl relative overflow-hidden group cursor-pointer" onClick={() => setPage('upload')}>
          <div className="text-xs font-mono text-accent uppercase tracking-widest mb-2">Next Step</div>
          <div className="text-xl font-bold text-white">Initialize Upload →</div>
          <div className="absolute right-0 bottom-0 text-6xl opacity-5 group-hover:opacity-10 transition-opacity translate-y-4">📄</div>
        </div>
      </div>

      <section className="bg-[#111118] border border-[#2a2a3a] rounded-2xl overflow-hidden shadow-2xl">
        <div className="px-8 py-5 border-b border-[#2a2a3a] bg-[#1a1a25]/50 flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-widest text-[#5a5a78]">Pipeline Registry</h2>
        </div>

        {exams.length === 0 ? (
          <div className="py-24 flex flex-col items-center justify-center text-[#5a5a78] gap-4">
            <span className="text-6xl">📥</span>
            <div className="text-center">
              <p className="text-white font-medium">No pipelines configured</p>
              <p className="text-sm">Upload a bulk PDF scan to begin automated evaluation.</p>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-[#0a0a0f] text-[#5a5a78] text-[10px] uppercase tracking-widest font-mono">
                  <th className="px-8 py-4">Status</th>
                  <th className="px-8 py-4">Title</th>
                  <th className="px-8 py-4">Created</th>
                  <th className="px-8 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#2a2a3a]">
                {exams.map(exam => (
                  <tr key={exam.id} className="hover:bg-[#1a1a25]/30 transition-colors group">
                    <td className="px-8 py-6">
                      <Badge status={exam.status} />
                    </td>
                    <td className="px-8 py-6">
                      <div className="font-bold text-white text-lg">{exam.title}</div>
                      <div className="text-xs text-[#5a5a78] font-mono mt-1">ID: {exam.id.toString().padStart(4, '0')}</div>
                    </td>
                    <td className="px-8 py-6 text-[#9898b8] text-sm font-mono">
                      {new Date(exam.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-8 py-6 text-right">
                      <div className="flex items-center justify-end gap-3 opacity-0 group-hover:opacity-100 transition-all">
                        {exam.status === 'complete' && (
                          <button 
                            className="bg-[#111118] border border-[#2a2a3a] text-accent px-4 py-2 rounded-lg text-sm font-bold hover:bg-accent hover:text-white transition-all"
                            onClick={() => { setSelectedExam(exam); setPage('analytics'); }}
                          >
                            Analytics
                          </button>
                        )}
                        <button 
                          className="bg-[#2a2a3a] text-white px-4 py-2 rounded-lg text-sm font-bold hover:bg-accent transition-all"
                          onClick={() => openReview(exam)}
                        >
                          {exam.status === 'complete' ? 'View Results' : 'Inspect Queue'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
