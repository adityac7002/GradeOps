import { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Badge, Spinner } from '../ui';

export default function InstructorDashboard({ setPage, setSelectedExam }) {
  const { authFetch } = useAuth();
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [gradingId, setGradingId] = useState(null);
  const [rubricModal, setRubricModal] = useState(null); // exam id
  const [rubricText, setRubricText] = useState('');
  const [rubricError, setRubricError] = useState('');

  const loadExams = () => {
    authFetch('/api/exams')
      .then(r => r.json())
      .then(setExams)
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadExams(); }, []);

  const triggerGrading = async (examId) => {
    setGradingId(examId);
    try {
      const res = await authFetch(`/api/exams/${examId}/grade`, { method: 'POST' });
      if (!res.ok) {
        const e = await res.json();
        alert(e.detail || 'Failed to start grading');
      } else {
        // Poll status
        const poll = setInterval(async () => {
          const r = await authFetch('/api/exams');
          const list = await r.json();
          setExams(list);
          const exam = list.find(e => e.id === examId);
          if (exam?.status !== 'processing') { clearInterval(poll); setGradingId(null); }
        }, 3000);
      }
    } catch { setGradingId(null); }
  };

  const saveRubric = async () => {
    setRubricError('');
    try {
      const questions = JSON.parse(rubricText);
      const res = await authFetch(`/api/exams/${rubricModal}/rubric`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(questions),
      });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      setRubricModal(null);
    } catch (e) {
      setRubricError(e.message || 'Invalid JSON format');
    }
  };

  const openRubric = async (examId) => {
    setRubricModal(examId);
    const res = await authFetch(`/api/exams/${examId}/rubric`);
    const data = await res.json();
    setRubricText(JSON.stringify(data.length ? data : RUBRIC_TEMPLATE, null, 2));
  };

  const openReview = (exam) => {
    setSelectedExam(exam);
    setPage('review');
  };

  const deleteExam = async (examId) => {
    if (!confirm('Are you sure you want to delete this exam and all its grading data? This action cannot be undone.')) return;
    await authFetch(`/api/exams/${examId}`, { method: 'DELETE' });
    loadExams();
  };

  // Derived stats
  const totalPapers = exams.reduce((acc, e) => acc + (e.paper_count || 0), 0);
  const totalGraded = exams.reduce((acc, e) => acc + (e.graded_count || 0), 0);
  const processingCount = exams.filter(e => e.status === 'processing').length;

  if (loading) return (
    <div className="flex-1 flex items-center justify-center text-[#5a5a78] gap-3 h-screen bg-[#0a0a0f]">
      <Spinner large />
      <span className="font-mono text-sm uppercase tracking-wider">Loading Operations...</span>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-[#e2e2f0] p-8 font-sans selection:bg-accent-glow">
      <div className="max-w-[1400px] mx-auto flex flex-col gap-8">
        
        {/* HEADER */}
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Exam Operations</h1>
            <p className="text-[#9898b8] text-sm mt-1">Manage processing queues, evaluation pipelines, and rubrics</p>
          </div>
          <button 
            className="flex items-center gap-2 px-5 py-2.5 bg-white text-black text-sm font-semibold rounded-md hover:bg-gray-200 transition-colors shadow-sm"
            onClick={() => setPage('upload')}
          >
            <span className="text-lg leading-none">+</span> New Pipeline
          </button>
        </header>

        {/* STATS ROW */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg p-5">
            <h3 className="text-xs uppercase tracking-widest text-[#5a5a78] font-mono mb-1">Total Exams</h3>
            <p className="text-3xl font-semibold text-white">{exams.length}</p>
          </div>
          <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg p-5">
            <h3 className="text-xs uppercase tracking-widest text-[#5a5a78] font-mono mb-1">Papers Processed</h3>
            <p className="text-3xl font-semibold text-white">{totalGraded} <span className="text-lg text-[#5a5a78] font-normal">/ {totalPapers}</span></p>
          </div>
          <div className="bg-[#111118] border border-[#2a2a3a] rounded-lg p-5">
            <h3 className="text-xs uppercase tracking-widest text-[#5a5a78] font-mono mb-1">Active Processing</h3>
            <div className="flex items-center gap-3">
              <p className="text-3xl font-semibold text-white">{processingCount}</p>
              {processingCount > 0 && <Spinner />}
            </div>
          </div>
          <div className="bg-[#1a1a25] border border-[#2a2a3a] rounded-lg p-5 relative overflow-hidden group hover:border-[#3a3a50] transition-colors cursor-pointer" onClick={() => setPage('upload')}>
            <div className="absolute right-0 bottom-0 text-[100px] leading-none opacity-5 group-hover:opacity-10 transition-opacity translate-x-4 translate-y-6">⬆</div>
            <h3 className="text-xs uppercase tracking-widest text-accent font-mono mb-1">Quick Action</h3>
            <p className="text-lg font-medium text-white mt-2">Upload new scans</p>
          </div>
        </div>

        {/* PROCESSING QUEUE */}
        <section className="bg-[#111118] border border-[#2a2a3a] rounded-xl overflow-hidden shadow-lg flex flex-col">
          <div className="px-6 py-4 border-b border-[#2a2a3a] bg-[#1a1a25] flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Evaluation Queue</h2>
          </div>
          
          {exams.length === 0 ? (
            <div className="py-16 flex flex-col items-center justify-center text-[#5a5a78]">
              <div className="text-4xl mb-4 opacity-40">📥</div>
              <p className="text-sm font-medium text-[#9898b8]">No pipelines active</p>
              <p className="text-xs mt-1">Upload a scanned exam bundle to begin processing.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-[#0a0a0f] text-[#5a5a78] text-xs uppercase tracking-widest font-mono">
                  <tr>
                    <th className="px-6 py-3 font-medium border-b border-[#2a2a3a]">ID / Course</th>
                    <th className="px-6 py-3 font-medium border-b border-[#2a2a3a]">Pipeline</th>
                    <th className="px-6 py-3 font-medium border-b border-[#2a2a3a]">Status</th>
                    <th className="px-6 py-3 font-medium border-b border-[#2a2a3a] w-48">Progress</th>
                    <th className="px-6 py-3 font-medium border-b border-[#2a2a3a]">Created</th>
                    <th className="px-6 py-3 font-medium border-b border-[#2a2a3a] text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#2a2a3a]">
                  {exams.map(exam => {
                    const percent = exam.paper_count ? Math.round((exam.graded_count / exam.paper_count) * 100) : 0;
                    return (
                      <tr key={exam.id} className="hover:bg-[#1a1a25] transition-colors group">
                        <td className="px-6 py-4">
                          <div className="font-semibold text-white">{exam.course}</div>
                          <div className="text-xs text-[#5a5a78] mt-0.5 font-mono">ID: {exam.id}</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-[#e2e2f0]">{exam.title}</div>
                        </td>
                        <td className="px-6 py-4">
                          <Badge status={exam.status} />
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex flex-col gap-1.5">
                            <div className="flex justify-between text-xs text-[#9898b8]">
                              <span>{exam.graded_count} / {exam.paper_count}</span>
                              <span>{percent}%</span>
                            </div>
                            <div className="w-full h-1.5 bg-[#0a0a0f] rounded-full overflow-hidden border border-[#2a2a3a]">
                              <div 
                                className={`h-full ${exam.status === 'processing' ? 'bg-accent animate-pulse' : 'bg-[#22c55e]'}`} 
                                style={{ width: `${percent}%` }} 
                              />
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-[#9898b8] text-xs font-mono">
                          {new Date(exam.created_at).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex items-center justify-end gap-2 opacity-80 group-hover:opacity-100 transition-opacity">
                            <button className="px-3 py-1.5 bg-[#1a1a25] border border-[#3a3a50] hover:border-accent hover:text-white rounded text-xs transition-all" onClick={() => openRubric(exam.id)}>
                              📐 Config
                            </button>
                            <button 
                              className="px-3 py-1.5 bg-accent text-white hover:bg-accent2 rounded text-xs font-medium transition-all disabled:opacity-50 flex items-center gap-1 min-w-[70px] justify-center" 
                              onClick={() => triggerGrading(exam.id)}
                              disabled={gradingId === exam.id || exam.status === 'processing'}
                            >
                              {gradingId === exam.id ? <Spinner /> : 'Run Pipeline'}
                            </button>
                            <button className="px-3 py-1.5 bg-[#1a1a25] border border-[#3a3a50] hover:border-white hover:text-white rounded text-xs transition-all" onClick={() => openReview(exam)}>
                              👁 Inspect
                            </button>
                            <button className="px-2 py-1.5 text-[#ef4444] hover:bg-[#ef4444]/10 rounded text-xs transition-all ml-2" onClick={() => deleteExam(exam.id)} title="Delete Pipeline">
                              ✕
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      {/* RUBRIC BUILDER MODAL */}
      {rubricModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in duration-200" onClick={e => e.target === e.currentTarget && setRubricModal(null)}>
          <div className="bg-[#111118] border border-[#2a2a3a] rounded-xl w-full max-w-4xl max-h-[90vh] shadow-2xl flex flex-col animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a2a3a] bg-[#1a1a25] rounded-t-xl">
              <div>
                <h3 className="text-lg font-semibold text-white">Pipeline Rubric Configuration</h3>
                <p className="text-xs text-[#5a5a78] mt-0.5 font-mono">Exam ID: {rubricModal} • JSON Editor</p>
              </div>
              <button className="text-[#5a5a78] hover:text-white transition-colors text-xl" onClick={() => setRubricModal(null)}>✕</button>
            </div>
            
            <div className="flex-1 overflow-hidden flex flex-col p-6 bg-[#0a0a0f]">
              <p className="text-sm text-[#9898b8] mb-4">
                Define the grading criteria schema. The AI evaluation engine uses this JSON to dynamically assess answers and assign partial credit.
              </p>
              
              <div className="flex-1 relative rounded-lg overflow-hidden border border-[#2a2a3a] focus-within:border-accent transition-colors">
                {/* Fake line numbers for IDE look */}
                <div className="absolute left-0 top-0 bottom-0 w-12 bg-[#111118] border-r border-[#2a2a3a] flex flex-col items-end py-4 px-2 text-xs font-mono text-[#5a5a78] select-none pointer-events-none opacity-50">
                  {Array.from({length: 25}).map((_, i) => <div key={i}>{i + 1}</div>)}
                </div>
                <textarea
                  className="w-full h-full bg-[#0a0a0f] text-[#a78bfa] font-mono text-sm p-4 pl-16 outline-none resize-none leading-relaxed"
                  value={rubricText}
                  onChange={e => setRubricText(e.target.value)}
                  spellCheck={false}
                />
              </div>
              
              {rubricError && (
                <div className="mt-4 p-3 bg-[#ef4444]/10 border border-[#ef4444]/30 rounded text-[#ef4444] text-sm flex items-center gap-2 font-mono">
                  <span>🚨</span> {rubricError}
                </div>
              )}
            </div>

            <div className="px-6 py-4 border-t border-[#2a2a3a] bg-[#1a1a25] flex justify-between items-center rounded-b-xl">
              <a href="#" className="text-xs text-[#5a5a78] hover:text-accent transition-colors font-mono underline decoration-[#2a2a3a] underline-offset-4">View Schema Documentation</a>
              <div className="flex gap-3">
                <button className="px-5 py-2 text-sm text-[#e2e2f0] hover:text-white font-medium transition-colors" onClick={() => setRubricModal(null)}>Cancel</button>
                <button className="px-6 py-2 bg-white text-black text-sm font-semibold rounded hover:bg-gray-200 transition-all shadow-[0_0_15px_rgba(255,255,255,0.1)]" onClick={saveRubric}>Deploy Configuration</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const RUBRIC_TEMPLATE = [
  {
    number: 1,
    prompt: "Define Machine Learning and describe its main paradigms.",
    max_points: 10,
    rubric_items: [
      { description: "Correctly defines Machine Learning", points: 4, keywords: ["algorithm", "data", "learn"] },
      { description: "Identifies supervised learning", points: 2, keywords: ["supervised", "labels"] },
      { description: "Identifies unsupervised learning", points: 2, keywords: ["unsupervised", "clusters"] },
      { description: "Identifies reinforcement learning", points: 2, keywords: ["reinforcement", "reward"] }
    ]
  }
];
