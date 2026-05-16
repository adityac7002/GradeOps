import { useState, useEffect, useCallback } from 'react';
import { useAuth, API } from '../contexts/AuthContext';
import { Spinner, Badge } from '../ui';

export default function ReviewDashboard({ selectedExam }) {
  const { authFetch, token } = useAuth();
  const [exams, setExams] = useState([]);
  const [examId, setExamId] = useState(selectedExam?.id ?? null);
  const [answers, setAnswers] = useState([]);
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState(null);
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [overrideGrade, setOverrideGrade] = useState('');
  const [overrideReason, setOverrideReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [filterStatus, setFilterStatus] = useState('graded');
  const [toast, setToast] = useState(null);
  
  // OCR editable state (local only, for TA reference/correction before grading)
  const [editableOcr, setEditableOcr] = useState('');

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 2500);
  };

  useEffect(() => {
    authFetch('/api/exams').then(r => r.json()).then(setExams);
  }, []);

  const loadAnswers = useCallback(async (eid, status = filterStatus) => {
    if (!eid) return;
    setLoading(true);
    try {
      const res = await authFetch(`/api/exams/${eid}/dashboard?status=${status}&limit=100`);
      const data = await res.json();
      setAnswers(data.items || []);
      setTotal(data.total || 0);
      setIndex(0);
      const sRes = await authFetch(`/api/exams/${eid}/stats`);
      setStats(await sRes.json());
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

  useEffect(() => {
    if (examId) loadAnswers(examId);
  }, [examId]);

  const current = answers[index];
  
  // Reset editable OCR when answer changes
  useEffect(() => {
    if (current) setEditableOcr(current.ocr_text || '');
  }, [current]);

  useEffect(() => {
    const onKey = e => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'a' || e.key === 'A') handleApprove();
      if (e.key === 'o' || e.key === 'O') setOverrideOpen(true);
      if (e.key === 'n' || e.key === 'ArrowRight') handleNext();
      if (e.key === 'p' || e.key === 'ArrowLeft') handlePrev();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [answers, index, current, submitting]);

  const handleNext = () => setIndex(i => Math.min(i + 1, answers.length - 1));
  const handlePrev = () => setIndex(i => Math.max(i - 0, 0)); // keep 0 if 0

  const handleApprove = async () => {
    if (!current || submitting) return;
    setSubmitting(true);
    try {
      await authFetch(`/api/answers/${current.id}/review`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'approve' }),
      });
      showToast('✅ Approved!');
      setAnswers(prev => prev.filter(a => a.id !== current.id));
      setStats(s => s ? { ...s, approved: s.approved + 1, graded: s.graded - 1 } : s);
    } finally {
      setSubmitting(false);
    }
  };

  const handleOverride = async () => {
    if (!current || !overrideGrade || submitting) return;
    setSubmitting(true);
    try {
      await authFetch(`/api/answers/${current.id}/review`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'override', ta_grade: parseFloat(overrideGrade), ta_override_reason: overrideReason }),
      });
      showToast('✏️ Override saved!', 'success');
      setAnswers(prev => prev.filter(a => a.id !== current.id));
      setStats(s => s ? { ...s, overridden: s.overridden + 1, graded: s.graded - 1 } : s);
      setOverrideOpen(false); setOverrideGrade(''); setOverrideReason('');
    } finally {
      setSubmitting(false);
    }
  };

  const changeFilter = s => {
    setFilterStatus(s);
    loadAnswers(examId, s);
  };

  return (
    <div className="h-screen w-full bg-[#0a0a0f] text-[#e2e2f0] flex flex-col font-sans text-sm overflow-hidden selection:bg-accent-glow">
      {/* TOP BAR */}
      <header className="h-14 border-b border-[#2a2a3a] bg-[#111118] flex items-center justify-between px-4 shrink-0 z-10 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="font-semibold text-white tracking-wide text-base">TA Review Queue</div>
          <select 
            className="bg-[#1a1a25] border border-[#3a3a50] rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-accent hover:border-[#4a4a60] transition-colors appearance-none pr-8 cursor-pointer relative"
            value={examId ?? ''} 
            onChange={e => setExamId(Number(e.target.value))}
          >
            <option value="">Select exam...</option>
            {exams.map(ex => <option key={ex.id} value={ex.id}>{ex.title}</option>)}
          </select>
          {examId && (
            <div className="flex bg-[#1a1a25] rounded-md border border-[#2a2a3a] overflow-hidden ml-2 p-0.5">
              {['graded', 'approved', 'overridden', 'pending'].map(s => (
                <button 
                  key={s} 
                  className={`px-3 py-1 text-xs uppercase tracking-wider font-medium rounded-sm transition-all ${filterStatus === s ? 'bg-[#3a3a50] text-white shadow-sm' : 'text-[#9898b8] hover:text-[#e2e2f0] hover:bg-[#22222f]'}`} 
                  onClick={() => changeFilter(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>

        {current && (
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <span className="text-[#9898b8] uppercase tracking-wider text-xs">Student ID</span>
              <span className="font-mono text-white bg-[#1a1a25] px-2 py-0.5 rounded border border-[#2a2a3a]">{current.student_name || current.student_id}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-[#9898b8] uppercase tracking-wider text-xs">Question</span>
              <span className="font-mono text-white bg-[#1a1a25] px-2 py-0.5 rounded border border-[#2a2a3a]">Q{current.question_number}</span>
            </div>
            <Badge status={current.status} />
          </div>
        )}

        <div className="flex items-center gap-3 text-xs text-[#5a5a78]">
          <div className="flex items-center gap-1"><kbd className="bg-[#1a1a25] border border-[#2a2a3a] rounded px-1.5 py-0.5 font-mono text-white">A</kbd> Approve</div>
          <div className="flex items-center gap-1"><kbd className="bg-[#1a1a25] border border-[#2a2a3a] rounded px-1.5 py-0.5 font-mono text-white">O</kbd> Override</div>
        </div>
      </header>

      {/* MAIN CONTENT */}
      <main className="flex-1 flex overflow-hidden bg-[#0a0a0f]">
        {!examId ? (
          <div className="flex-1 flex items-center justify-center flex-col text-[#5a5a78]">
            <div className="text-4xl mb-4 opacity-50">📋</div>
            <h2 className="text-lg font-medium text-[#9898b8]">Select an exam to start reviewing</h2>
          </div>
        ) : loading ? (
          <div className="flex-1 flex items-center justify-center text-[#9898b8] gap-3">
            <Spinner large /> Loading queue...
          </div>
        ) : answers.length === 0 ? (
          <div className="flex-1 flex items-center justify-center flex-col text-[#5a5a78]">
            <div className="text-4xl mb-4 opacity-50">🎉</div>
            <h2 className="text-lg font-medium text-[#9898b8]">Queue is empty</h2>
            <p className="mt-2">No answers matching the current filter.</p>
          </div>
        ) : (
          <>
            {/* LEFT PANEL: Original Image */}
            <section className="w-[35%] border-r border-[#2a2a3a] bg-[#111118] flex flex-col relative">
              <div className="h-10 border-b border-[#2a2a3a] flex items-center justify-between px-4 bg-[#1a1a25] shrink-0">
                <h3 className="font-mono text-xs uppercase tracking-widest text-[#9898b8]">Source Document</h3>
                <div className="flex gap-2">
                  <button className="text-[#5a5a78] hover:text-white transition-colors" title="Zoom Out">🔍-</button>
                  <button className="text-[#5a5a78] hover:text-white transition-colors" title="Zoom In">🔍+</button>
                </div>
              </div>
              <div className="flex-1 overflow-auto p-4 flex justify-center bg-[#0a0a0f]">
                {current.image_path ? (
                  <img 
                    src={`${API}/${current.image_path}`} 
                    alt="Student Answer" 
                    className="max-w-full h-auto object-contain shadow-md rounded border border-[#2a2a3a] bg-white filter contrast-[1.05]"
                  />
                ) : (
                  <div className="m-auto text-[#5a5a78] font-mono text-xs border border-dashed border-[#3a3a50] p-8 rounded-md">
                    NO IMAGE AVAILABLE
                  </div>
                )}
              </div>
            </section>

            {/* CENTER PANEL: OCR & Transcription */}
            <section className="w-[30%] border-r border-[#2a2a3a] bg-[#111118] flex flex-col">
              <div className="h-10 border-b border-[#2a2a3a] flex items-center px-4 bg-[#1a1a25] shrink-0">
                <h3 className="font-mono text-xs uppercase tracking-widest text-[#9898b8]">Extracted Text</h3>
              </div>
              <div className="flex-1 p-4 flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-[#5a5a78] uppercase tracking-wider">Editable Transcription</span>
                </div>
                <textarea 
                  className="flex-1 w-full bg-[#1a1a25] border border-[#2a2a3a] rounded-md p-4 text-[#e2e2f0] font-mono text-sm leading-relaxed focus:border-accent focus:ring-1 focus:ring-accent outline-none resize-none transition-all"
                  value={editableOcr}
                  onChange={e => setEditableOcr(e.target.value)}
                  placeholder="OCR text will appear here..."
                />
              </div>
            </section>

            {/* RIGHT PANEL: Rubric, AI Grade, Action */}
            <section className="w-[35%] bg-[#111118] flex flex-col relative overflow-hidden">
              <div className="h-10 border-b border-[#2a2a3a] flex items-center px-4 bg-[#1a1a25] shrink-0">
                <h3 className="font-mono text-xs uppercase tracking-widest text-[#9898b8]">Evaluation Dashboard</h3>
              </div>
              
              <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-5">
                
                {/* AI Score Card */}
                <div className="bg-[#1a1a25] border border-[#2a2a3a] rounded-lg p-5 shadow-sm relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-3 opacity-10">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                  </div>
                  <h4 className="text-xs uppercase tracking-wider text-[#9898b8] mb-3">AI Evaluation Score</h4>
                  <div className="flex items-baseline gap-2 mb-4">
                    <span className="text-5xl font-bold text-white tracking-tight">{current.ai_grade ?? '-'}</span>
                    <span className="text-xl text-[#5a5a78]">/ {current.max_points} pts</span>
                  </div>
                  <div className="text-sm text-[#e2e2f0] leading-relaxed bg-[#111118] p-3 rounded border border-[#2a2a3a]">
                    <span className="block text-xs uppercase text-[#5a5a78] mb-1 font-mono">Justification</span>
                    {current.ai_justification || 'No detailed justification provided.'}
                  </div>
                </div>

                {/* Plagiarism Alert */}
                {current.plagiarism_flag && (
                  <div className="bg-[#ef4444]/10 border border-[#ef4444]/30 rounded-lg p-4 flex items-start gap-3">
                    <div className="text-[#ef4444] text-xl">🚨</div>
                    <div>
                      <h4 className="text-[#ef4444] font-medium text-sm">Plagiarism Flagged</h4>
                      <p className="text-[#ef4444]/80 text-xs mt-1">Similarity score: {(current.plagiarism_score * 100).toFixed(1)}%. Review carefully before approving.</p>
                    </div>
                  </div>
                )}

                {/* Rubric Breakdown */}
                <div className="flex flex-col gap-3 flex-1">
                  <h4 className="text-xs uppercase tracking-wider text-[#9898b8] border-b border-[#2a2a3a] pb-2">Rubric Criteria</h4>
                  <div className="flex flex-col gap-2">
                    {current.rubric_items?.length ? current.rubric_items.map((ri, i) => (
                      <div key={i} className="flex justify-between items-center bg-[#1a1a25] p-3 rounded-md border border-[#2a2a3a] group hover:border-[#4a4a60] transition-colors">
                        <span className="text-sm text-[#e2e2f0] pr-4">{ri.description}</span>
                        <span className="font-mono text-xs font-medium text-[#7c6af7] bg-[#7c6af7]/10 px-2 py-1 rounded shrink-0">{ri.points} pts</span>
                      </div>
                    )) : (
                      <div className="text-[#5a5a78] italic text-sm py-2">No rubric items assigned.</div>
                    )}
                  </div>
                </div>
              </div>
            </section>
          </>
        )}
      </main>

      {/* BOTTOM ACTION BAR */}
      {current && !loading && (
        <footer className="h-16 border-t border-[#2a2a3a] bg-[#111118] flex items-center justify-between px-6 shrink-0 shadow-[0_-4px_24px_rgba(0,0,0,0.2)] z-20">
          <div className="flex items-center gap-4">
            <span className="font-mono text-sm text-[#9898b8] bg-[#1a1a25] px-3 py-1 rounded border border-[#2a2a3a]">
              {index + 1} <span className="text-[#5a5a78]">of</span> {answers.length}
            </span>
            <div className="w-48 h-1.5 bg-[#1a1a25] rounded-full overflow-hidden border border-[#2a2a3a]">
              <div 
                className="h-full bg-accent transition-all duration-300" 
                style={{ width: `${((index + 1) / answers.length) * 100}%` }}
              />
            </div>
            {stats && (
              <span className="text-xs text-[#5a5a78]">
                {stats.total_answers ? Math.round(((stats.approved + stats.overridden) / stats.total_answers) * 100) : 0}% Queue Reviewed
              </span>
            )}
          </div>

          <div className="flex items-center gap-4">
            <div className="flex rounded-md overflow-hidden border border-[#3a3a50] mr-4 shadow-sm">
              <button className="px-4 py-2 bg-[#1a1a25] text-white hover:bg-[#2a2a3a] transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium border-r border-[#3a3a50]" onClick={() => setIndex(i => Math.max(i - 1, 0))} disabled={index === 0}>
                Prev
              </button>
              <button className="px-4 py-2 bg-[#1a1a25] text-white hover:bg-[#2a2a3a] transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium" onClick={() => setIndex(i => Math.min(i + 1, answers.length - 1))} disabled={index === answers.length - 1}>
                Next
              </button>
            </div>

            <button
              className="px-6 py-2 bg-[#ef4444]/10 text-[#ef4444] border border-[#ef4444]/30 rounded-md text-sm font-medium hover:bg-[#ef4444] hover:text-white transition-all focus:ring-2 focus:ring-[#ef4444]/50 disabled:opacity-50 flex items-center gap-2"
              onClick={() => { setOverrideGrade(String(current.ai_grade ?? '')); setOverrideOpen(true); }}
              disabled={submitting}
            >
              Override <span className="text-xs opacity-60 font-mono tracking-tighter">[O]</span>
            </button>
            <button
              className="px-8 py-2 bg-[#22c55e] text-[#052e14] border border-[#22c55e] rounded-md text-sm font-semibold hover:bg-[#16a34a] hover:border-[#16a34a] hover:text-white transition-all shadow-[0_0_15px_rgba(34,197,94,0.3)] focus:ring-2 focus:ring-[#22c55e]/50 disabled:opacity-50 flex items-center gap-2"
              onClick={handleApprove}
              disabled={submitting}
            >
              {submitting ? <Spinner /> : 'Approve'} <span className="text-xs opacity-70 font-mono tracking-tighter bg-black/10 px-1 rounded">[A]</span>
            </button>
          </div>
        </footer>
      )}

      {/* OVERRIDE MODAL */}
      {overrideOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in duration-200" onClick={e => e.target === e.currentTarget && setOverrideOpen(false)}>
          <div className="bg-[#111118] border border-[#2a2a3a] rounded-xl p-6 w-full max-w-md shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-white">Override AI Grade</h3>
              <button className="text-[#5a5a78] hover:text-white transition-colors" onClick={() => setOverrideOpen(false)}>✕</button>
            </div>
            
            <div className="flex flex-col gap-4">
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#9898b8] mb-2 font-medium">New Grade (Max: {current?.max_points})</label>
                <div className="relative">
                  <input
                    className="w-full bg-[#1a1a25] border border-[#3a3a50] rounded-md px-4 py-3 text-white text-lg focus:border-accent focus:ring-1 focus:ring-accent outline-none transition-all font-mono"
                    type="number" min={0} max={current?.max_points} step={0.5}
                    value={overrideGrade}
                    onChange={e => setOverrideGrade(e.target.value)}
                    autoFocus
                  />
                  <div className="absolute right-4 top-1/2 -translate-y-1/2 text-[#5a5a78] font-mono pointer-events-none">/ {current?.max_points}</div>
                </div>
              </div>
              
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#9898b8] mb-2 font-medium">Reason for Override (Optional)</label>
                <textarea
                  className="w-full bg-[#1a1a25] border border-[#3a3a50] rounded-md px-4 py-3 text-white text-sm focus:border-accent focus:ring-1 focus:ring-accent outline-none resize-none transition-all h-24"
                  placeholder="Explain why you're changing the AI's grade..."
                  value={overrideReason}
                  onChange={e => setOverrideReason(e.target.value)}
                />
              </div>
            </div>

            <div className="flex gap-3 mt-8">
              <button className="flex-1 px-4 py-2.5 bg-transparent border border-[#3a3a50] text-[#e2e2f0] rounded-md text-sm font-medium hover:bg-[#1a1a25] transition-colors" onClick={() => setOverrideOpen(false)}>
                Cancel
              </button>
              <button className="flex-[2] px-4 py-2.5 bg-accent text-white rounded-md text-sm font-medium hover:bg-accent2 transition-colors disabled:opacity-50 shadow-[0_0_15px_rgba(124,106,247,0.3)] flex justify-center" onClick={handleOverride} disabled={!overrideGrade || submitting}>
                {submitting ? <Spinner /> : 'Save Override'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TOAST NOTIFICATION */}
      {toast && (
        <div className="fixed bottom-20 right-6 z-50 flex items-center gap-3 bg-[#1a1a25] border border-[#2a2a3a] px-5 py-3 rounded-lg shadow-xl animate-in slide-in-from-right-4 duration-300">
          <span className="text-white text-sm font-medium">{toast.msg}</span>
        </div>
      )}
    </div>
  );
}
