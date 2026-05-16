import { useState, useEffect, useRef } from 'react';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import { useHotkeys } from 'react-hotkeys-hook';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import { Spinner, Badge } from '../ui';
import { ChevronLeft, ChevronRight, CheckCircle, XCircle, AlertCircle, Info, Keyboard } from 'lucide-react';

export default function ReviewDashboard({ exam, onBack }) {
  const { authFetch } = useAuth();
  const { addToast } = useToast();
  
  const [answers, setAnswers] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Local override state
  const [overrideScore, setOverrideScore] = useState('');
  const [taNotes, setTaNotes] = useState('');
  
  const scoreInputRef = useRef(null);

  const fetchAnswers = async () => {
    try {
      const res = await authFetch(`/api/exams/${exam.id}/answers`);
      const data = await res.json();
      setAnswers(data);
    } catch (err) {
      addToast("Failed to load answers", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAnswers(); }, [exam.id]);

  const currentAnswer = answers[currentIndex];
  const grade = currentAnswer?.grade || {};

  // Reset local state when answer changes
  useEffect(() => {
    if (currentAnswer) {
      setOverrideScore(currentAnswer.grade?.final_score ?? '');
      setTaNotes(currentAnswer.grade?.ta_notes ?? '');
    }
  }, [currentIndex, currentAnswer]);

  const handleNext = () => {
    if (currentIndex < answers.length - 1) setCurrentIndex(prev => prev + 1);
  };

  const handlePrev = () => {
    if (currentIndex > 0) setCurrentIndex(prev => prev - 1);
  };

  const saveReview = async (isApprove = true) => {
    if (!currentAnswer) return;
    setSaving(true);
    try {
      const payload = {
        final_score: isApprove ? (grade.ai_score ?? 0) : parseFloat(overrideScore),
        ta_notes: taNotes,
        status: isApprove ? 'reviewed' : 'flagged'
      };
      
      const res = await authFetch(`/api/answers/${currentAnswer.id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) throw new Error("Failed to save review");
      
      addToast(isApprove ? "Approved" : "Flagged", "success");
      handleNext();
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setSaving(false);
    }
  };

  // Keyboard Shortcuts
  useHotkeys('a', () => saveReview(true), [currentAnswer, grade]);
  useHotkeys('r', () => saveReview(false), [currentAnswer, overrideScore, taNotes]);
  useHotkeys('j', handleNext, [currentIndex, answers]);
  useHotkeys('k', handlePrev, [currentIndex]);
  useHotkeys('o', (e) => { e.preventDefault(); scoreInputRef.current?.focus(); });
  useHotkeys('shift+?', () => alert("Shortcuts: A (Approve), R (Reject/Flag), J (Next), K (Prev), O (Focus Score)"));

  if (loading) return <div className="h-[80vh] flex items-center justify-center"><Spinner /></div>;
  if (!currentAnswer) return <div className="h-[80vh] flex items-center justify-center text-[#5a5a78]">No answers found for this exam.</div>;

  return (
    <div className="fixed inset-0 top-20 bg-[#0a0a0f] flex flex-col overflow-hidden">
      {/* TOP BAR */}
      <div className="h-14 border-b border-[#2a2a3a] bg-[#111118] px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-[#5a5a78] hover:text-white transition-colors">
            <ChevronLeft size={20} />
          </button>
          <div className="h-4 w-[1px] bg-[#2a2a3a]" />
          <div>
            <span className="text-white font-semibold">{exam.title}</span>
            <span className="text-[#5a5a78] text-xs font-mono ml-3">ITEM {currentIndex + 1} / {answers.length}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Badge status={currentAnswer.extraction_status === 'completed' ? 'ready' : 'pending'}>
            {currentAnswer.extraction_status.toUpperCase()}
          </Badge>
          <div className="flex bg-[#0a0a0f] rounded-lg border border-[#2a2a3a] p-1">
            <button onClick={handlePrev} className="p-1 hover:bg-[#2a2a3a] rounded text-[#5a5a78] hover:text-white"><ChevronLeft size={18} /></button>
            <button onClick={handleNext} className="p-1 hover:bg-[#2a2a3a] rounded text-[#5a5a78] hover:text-white"><ChevronRight size={18} /></button>
          </div>
        </div>
      </div>

      {/* THREE PANE CONTENT */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* PANE 1: IMAGE (40%) */}
        <div className="w-[40%] border-r border-[#2a2a3a] bg-[#050508] relative overflow-hidden flex flex-col">
          <div className="absolute top-4 left-4 z-10 px-2 py-1 bg-black/60 backdrop-blur-md rounded text-[10px] font-mono text-[#5a5a78] border border-white/5">
            ORIGINAL_SCAN_200DPI
          </div>
          <TransformWrapper centerOnInit initialScale={0.8} minScale={0.1} maxScale={4}>
            <TransformComponent wrapperClass="!w-full !h-full" contentClass="!w-full !h-full flex items-center justify-center">
              <img 
                src={`/api/storage/${currentAnswer.crop_path.replace('storage/', '')}`} 
                alt="Student Answer" 
                className="max-w-none shadow-2xl"
              />
            </TransformComponent>
          </TransformWrapper>
        </div>

        {/* PANE 2: RUBRIC (30%) */}
        <div className="w-[30%] border-r border-[#2a2a3a] flex flex-col bg-[#0a0a0f]">
          <div className="px-6 py-4 border-b border-[#2a2a3a] bg-[#111118]/50">
            <h3 className="text-xs uppercase tracking-widest text-[#5a5a78] font-bold">Rubric Evaluation</h3>
          </div>
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {grade.ai_breakdown_json?.criteria_evals?.map((ev, i) => (
              <div key={i} className="flex gap-4 group">
                <div className="shrink-0 mt-1">
                  {ev.status === 'met' ? <CheckCircle size={18} className="text-[#22c55e]" /> : 
                   ev.status === 'partial' ? <AlertCircle size={18} className="text-accent" /> : 
                   <XCircle size={18} className="text-[#ef4444]" />}
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono text-white/80">{ev.criterion_id}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${
                      ev.status === 'met' ? 'bg-[#22c55e]/10 text-[#22c55e]' : 
                      ev.status === 'partial' ? 'bg-accent/10 text-accent' : 
                      'bg-[#ef4444]/10 text-[#ef4444]'
                    }`}>
                      {ev.marks_awarded} PTS
                    </span>
                  </div>
                  <p className="text-sm text-[#e2e2f0] leading-relaxed mb-2">{ev.reasoning}</p>
                  <div className="text-[10px] font-mono text-[#5a5a78] bg-[#111118] p-2 rounded italic">
                    "{ev.evidence}"
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* PANE 3: DECISION (30%) */}
        <div className="w-[30%] flex flex-col bg-[#111118]">
          <div className="px-6 py-4 border-b border-[#2a2a3a] bg-[#1a1a25]">
            <h3 className="text-xs uppercase tracking-widest text-accent font-bold">AI Decision Insight</h3>
          </div>
          
          <div className="flex-1 overflow-y-auto p-8 flex flex-col">
            <div className="mb-8">
              <div className="text-[10px] uppercase tracking-widest text-[#5a5a78] mb-3">AI Justification</div>
              <p className="text-white text-lg font-medium leading-relaxed italic">
                "{grade.ai_justification}"
              </p>
            </div>

            <div className="h-[1px] bg-[#2a2a3a] mb-8" />

            <div className="space-y-6">
              <div>
                <label className="block text-[10px] uppercase tracking-widest text-[#5a5a78] mb-3">Score Adjustment <span className="text-accent ml-2 font-mono">(O)</span></label>
                <div className="flex items-end gap-3">
                  <input 
                    ref={scoreInputRef}
                    type="number"
                    step="0.5"
                    className="w-24 bg-[#0a0a0f] border border-[#2a2a3a] rounded-lg px-4 py-3 text-2xl font-bold text-white focus:border-accent outline-none"
                    value={overrideScore}
                    onChange={e => setOverrideScore(e.target.value)}
                  />
                  <div className="text-xl text-[#5a5a78] mb-2">/ {currentAnswer.question?.max_marks}</div>
                </div>
              </div>

              <div>
                <label className="block text-[10px] uppercase tracking-widest text-[#5a5a78] mb-3">Internal TA Notes</label>
                <textarea 
                  className="w-full h-32 bg-[#0a0a0f] border border-[#2a2a3a] rounded-lg p-4 text-sm text-white focus:border-accent outline-none resize-none"
                  placeholder="Reason for override or flags..."
                  value={taNotes}
                  onChange={e => setTaNotes(e.target.value)}
                />
              </div>
            </div>

            <div className="mt-auto pt-8 flex flex-col gap-3">
              <div className="flex gap-3">
                <button 
                  onClick={() => saveReview(true)}
                  disabled={saving}
                  className="flex-1 bg-white text-black font-bold py-4 rounded-xl hover:bg-gray-200 transition-all shadow-xl flex items-center justify-center gap-2"
                >
                  {saving ? <Spinner /> : <><CheckCircle size={18} /> Approve (A)</>}
                </button>
                <button 
                  onClick={() => saveReview(false)}
                  disabled={saving}
                  className="w-16 bg-[#1a1a25] border border-[#2a2a3a] text-[#ef4444] rounded-xl hover:bg-[#ef4444]/10 transition-all flex items-center justify-center"
                  title="Flag for Review (R)"
                >
                  <AlertCircle size={20} />
                </button>
              </div>
              <div className="flex items-center justify-center gap-6 text-[10px] font-mono text-[#5a5a78] mt-2">
                <span className="flex items-center gap-1"><Keyboard size={12} /> J/K: Navigate</span>
                <span className="flex items-center gap-1"><Keyboard size={12} /> SHIFT + ?: Help</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
