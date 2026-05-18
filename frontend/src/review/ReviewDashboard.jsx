import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import { useHotkeys } from 'react-hotkeys-hook';
import { useToast } from '../hooks/useToast';
import { CheckCircle2, XCircle, ArrowRight, Save, Activity, ZoomIn, Search, FileText } from 'lucide-react';

export default function ReviewDashboard({ exam, onBack }) {
  const { authFetch } = useAuth();
  const { addToast } = useToast();
  
  const [answers, setAnswers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Load answers that are ready for review (i.e. have grades)
  useEffect(() => {
    authFetch(`/api/exams/${exam.id}/answers?page_size=200`)
      .then(r => r.json())
      .then(data => {
        const all = Array.isArray(data) ? data : (data.items ?? []);
        const graded = all.filter(a => a.grade && a.grade.status !== 'reviewed');
        setAnswers(graded);
      })
      .finally(() => setLoading(false));
  }, [exam.id]);

  const currentAnswer = answers[currentIndex];
  
  // Local state for the current review decision
  const [finalScore, setFinalScore] = useState('');
  const [taNotes, setTaNotes] = useState('');

  // Sync state when current answer changes
  useEffect(() => {
    if (currentAnswer) {
      setFinalScore(currentAnswer.grade?.ai_score ?? '');
      setTaNotes('');
    }
  }, [currentAnswer]);

  const submitReview = async (approved) => {
    if (!currentAnswer) return;
    try {
      const payload = {
        final_score: parseFloat(finalScore),
        ta_notes: taNotes || (approved ? "Approved AI grading" : "Modified AI grading"),
        status: "reviewed"
      };

      await authFetch(`/api/exams/answers/${currentAnswer.id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      addToast(`Answer ${currentAnswer.id} reviewed`, 'success');
      
      if (currentIndex < answers.length - 1) {
        setCurrentIndex(i => i + 1);
      } else {
        addToast('All answers reviewed!', 'success');
        onBack();
      }
    } catch (e) {
      addToast(e.message, 'error');
    }
  };

  // Keyboard shortcuts
  useHotkeys('a', () => submitReview(true), [currentAnswer, finalScore, taNotes]);
  useHotkeys('r', () => document.getElementById('notes_input')?.focus(), [currentAnswer]);
  useHotkeys('j', () => { if(currentIndex > 0) setCurrentIndex(i=>i-1) }, [currentIndex]);
  useHotkeys('k', () => { if(currentIndex < answers.length-1) setCurrentIndex(i=>i+1) }, [currentIndex, answers.length]);

  if (loading) return (
    <div className="h-screen flex items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #4F46E5, #7C3AED)' }}>
          <Activity className="animate-spin text-white" size={20} />
        </div>
        <p className="text-sm text-text3">Loading review queue…</p>
      </div>
    </div>
  );
  if (!answers.length) return (
    <div className="h-screen flex flex-col items-center justify-center bg-background gap-4">
      <div className="w-16 h-16 rounded-2xl flex items-center justify-center bg-emerald-50 border border-emerald-100">
        <CheckCircle2 size={32} className="text-emerald-500" />
      </div>
      <div className="text-center">
        <h2 className="text-xl font-bold text-text mb-1">All Caught Up</h2>
        <p className="text-sm text-text2">No answers require review for this pipeline.</p>
      </div>
      <button className="btn btn-outline" onClick={onBack}>← Operations Center</button>
    </div>
  );

  return (
    <div className="h-[calc(100vh-64px)] bg-surface2 flex overflow-hidden">
      
      {/* LEFT PANE: Image Viewer */}
      <div className="flex-[2] bg-surface border-r border-border flex flex-col relative">
        <div className="h-12 border-b border-border bg-surface flex items-center justify-between px-4 z-10">
          <div className="flex items-center gap-3">
            <span className="label">Answer Image</span>
            <span className="badge badge-indigo font-mono">#{currentAnswer.id}</span>
          </div>
          <div className="flex items-center gap-3 text-xs text-text3">
            <span className="kbd">Scroll</span><span>zoom</span>
            <span className="kbd">Drag</span><span>pan</span>
          </div>
        </div>
        
        <div className="flex-1 overflow-hidden relative bg-[#F8F9FA] flex items-center justify-center">
          {currentAnswer.crop_path ? (
             <TransformWrapper initialScale={1} minScale={0.5} maxScale={4} centerOnInit>
               <TransformComponent wrapperStyle={{ width: '100%', height: '100%' }}>
                 <img 
                   src={`${import.meta.env.VITE_API_URL || ''}/${currentAnswer.crop_path}`} 
                   alt="Student Answer Crop" 
                   className="object-contain shadow-md rounded border border-border/50 bg-white"
                   style={{ maxHeight: '80vh', maxWidth: '90vw' }}
                 />
               </TransformComponent>
             </TransformWrapper>
          ) : (
            <div className="flex flex-col items-center justify-center text-text3">
              <FileText size={48} className="opacity-20 mb-4" />
              <p>Image not available</p>
            </div>
          )}
        </div>
      </div>

      {/* CENTER PANE: Context & AI Justification */}
      <div className="flex-1 bg-surface border-r border-border flex flex-col min-w-[320px]">
        <div className="h-12 border-b border-border bg-surface flex items-center px-6 z-10 shadow-sm">
           <span className="text-xs font-semibold uppercase tracking-wider text-text3">Evaluation Context</span>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <section>
            <h3 className="text-xs font-bold text-text3 uppercase tracking-wider mb-3">Extracted Text</h3>
            <div className="p-4 bg-surface2 rounded-xl border border-border/50 text-sm font-mono text-text leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto">
              {currentAnswer.transcribed_text || "No text extracted."}
            </div>
          </section>

          <section>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold text-text3 uppercase tracking-wider">AI Reasoning</h3>
              <span className="badge badge-indigo">AI Score: {currentAnswer.grade?.ai_score}</span>
            </div>
            <div className="p-4 bg-blue-50/50 rounded-xl border border-blue-100 text-sm text-text leading-relaxed">
              {currentAnswer.grade?.ai_justification || "No justification provided."}
            </div>
          </section>

          {currentAnswer.grade?.ai_breakdown_json?.criteria_evals && (
            <section>
              <h3 className="text-xs font-bold text-text3 uppercase tracking-wider mb-3">Criteria Breakdown</h3>
              <div className="space-y-2">
                {currentAnswer.grade.ai_breakdown_json.criteria_evals.map((e, i) => (
                  <div key={i} className="p-3 bg-surface rounded-xl border border-border text-xs">
                    <div className="flex justify-between font-bold mb-1">
                      <span className="text-text">{e.criterion_id}</span>
                      <span className={e.status === 'met' ? 'text-green-600' : e.status === 'partial' ? 'text-yellow-600' : 'text-red-600'}>
                        {e.marks_awarded} pts
                      </span>
                    </div>
                    <p className="text-text2 leading-snug">{e.reasoning}</p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>

      {/* RIGHT PANE: Human Decision */}
      <div className="w-[340px] bg-surface flex flex-col shadow-[-4px_0_24px_rgba(0,0,0,0.02)] z-20">
        <div className="h-12 border-b border-border bg-surface flex items-center px-6">
           <span className="text-xs font-semibold uppercase tracking-wider text-text3">Final Adjudication</span>
        </div>
        
        <div className="p-6 flex-1 flex flex-col">
          
          <div className="mb-6">
            <label className="block text-sm font-semibold text-text mb-2">Final Score</label>
            <input 
              type="number" 
              className="w-full text-3xl font-bold p-4 bg-surface2 border-2 border-border focus:border-accent rounded-xl focus:outline-none transition-colors"
              value={finalScore}
              onChange={e => setFinalScore(e.target.value)}
              step="0.5"
            />
          </div>

          <div className="mb-8">
            <label className="block text-sm font-semibold text-text mb-2">Auditor Notes</label>
            <textarea 
              id="notes_input"
              className="w-full h-32 p-3 bg-surface2 border border-border focus:border-accent rounded-xl focus:outline-none resize-none text-sm"
              placeholder="Add justification for overrides..."
              value={taNotes}
              onChange={e => setTaNotes(e.target.value)}
            />
          </div>

          <div className="mt-auto space-y-2.5">
            <button
              className="w-full btn btn-lg text-white border-transparent shadow-md"
              style={{ background: 'linear-gradient(135deg, #10B981, #059669)' }}
              onClick={() => submitReview(true)}
            >
              <CheckCircle2 size={17} /> Approve & Advance
            </button>
            <button
              className="w-full btn btn-lg btn-danger"
              onClick={() => submitReview(false)}
            >
              <Save size={16} /> Save Override
            </button>
          </div>

          <div className="mt-8 pt-6 border-t border-border">
            <div className="flex justify-between items-center mb-2.5">
              <span className="label">Review Progress</span>
              <span className="text-xs font-mono font-bold text-accent">{currentIndex + 1} / {answers.length}</span>
            </div>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${((currentIndex + 1) / answers.length) * 100}%` }} />
            </div>
          </div>
          
          <div className="mt-6 flex flex-wrap gap-2">
             <kbd className="kbd">A</kbd> <span className="text-[10px] text-text3 mr-2">Approve</span>
             <kbd className="kbd">R</kbd> <span className="text-[10px] text-text3 mr-2">Note</span>
             <kbd className="kbd">J/K</kbd> <span className="text-[10px] text-text3">Nav</span>
          </div>

        </div>
      </div>
    </div>
  );
}
