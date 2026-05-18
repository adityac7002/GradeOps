import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import { useHotkeys } from 'react-hotkeys-hook';
import { useToast } from '../hooks/useToast';
import { 
  CheckCircle2, 
  ArrowRight, 
  Save, 
  Activity, 
  FileText, 
  AlertCircle,
  MousePointer2,
  Cpu,
  UserCheck
} from 'lucide-react';

export default function ReviewDashboard({ exam, onBack }) {
  const { authFetch } = useAuth();
  const { addToast } = useToast();
  
  const [answers, setAnswers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Load answers that are ready for review
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
      
      addToast(`Answer ${currentAnswer.id} reviewed successfully`, 'success');
      
      if (currentIndex < answers.length - 1) {
        setCurrentIndex(i => i + 1);
      } else {
        addToast('Queue complete! All answers reviewed.', 'success');
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
    <div className="h-screen flex items-center justify-center bg-zinc-950">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-2xl flex items-center justify-center bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/20 animate-pulse">
          <Activity className="text-white animate-spin-slow" size={24} />
        </div>
        <p className="text-sm font-medium text-zinc-400 tracking-wide">Initializing Pipeline...</p>
      </div>
    </div>
  );

  if (!answers.length) return (
    <div className="h-screen flex flex-col items-center justify-center bg-zinc-950 gap-6">
      <div className="w-20 h-20 rounded-3xl flex items-center justify-center bg-emerald-500/10 border border-emerald-500/20">
        <CheckCircle2 size={40} className="text-emerald-400" />
      </div>
      <div className="text-center">
        <h2 className="text-2xl font-bold text-zinc-100 mb-2">Inbox Zero</h2>
        <p className="text-sm text-zinc-400">All automated grades have been reviewed and approved.</p>
      </div>
      <button 
        className="mt-4 px-6 py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-sm font-medium transition-all flex items-center gap-2 border border-zinc-700" 
        onClick={onBack}
      >
        <ArrowRight size={16} className="rotate-180" /> Back to Dashboard
      </button>
    </div>
  );

  return (
    <div className="h-[calc(100vh-64px)] bg-zinc-950 text-zinc-200 flex overflow-hidden font-sans">
      
      {/* LEFT PANE: Image Viewer */}
      <div className="flex-[2] bg-zinc-900/50 border-r border-zinc-800 flex flex-col relative">
        <div className="h-14 border-b border-zinc-800/50 flex items-center justify-between px-6 z-10 backdrop-blur-sm bg-zinc-900/80">
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
              <FileText size={16} className="text-indigo-400"/>
              Student Submission
            </h2>
            <span className="px-2.5 py-0.5 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-mono">
              ID: {currentAnswer.id}
            </span>
          </div>
          <div className="flex items-center gap-4 text-xs font-medium text-zinc-500">
            <span className="flex items-center gap-1.5"><MousePointer2 size={14}/> Scroll to zoom</span>
            <span className="flex items-center gap-1.5"><MousePointer2 size={14} className="rotate-90"/> Drag to pan</span>
          </div>
        </div>
        
        <div className="flex-1 overflow-hidden relative bg-zinc-950/50 flex items-center justify-center p-8">
          {currentAnswer.crop_path ? (
             <TransformWrapper initialScale={1} minScale={0.5} maxScale={4} centerOnInit>
               <TransformComponent wrapperStyle={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                 <img 
                   src={`${import.meta.env.VITE_API_URL || ''}/${currentAnswer.crop_path}`} 
                   alt="Student Answer Crop" 
                   className="object-contain shadow-2xl rounded-lg border border-zinc-800 bg-zinc-900 max-h-[85vh] max-w-[90vw]"
                 />
               </TransformComponent>
             </TransformWrapper>
          ) : (
            <div className="flex flex-col items-center justify-center text-zinc-600">
              <FileText size={48} className="opacity-20 mb-4" />
              <p>Source image not available</p>
            </div>
          )}
        </div>
      </div>

      {/* CENTER PANE: Context & AI Justification */}
      <div className="flex-[1.5] bg-zinc-900/30 border-r border-zinc-800 flex flex-col min-w-[380px]">
        <div className="h-14 border-b border-zinc-800/50 flex items-center px-6 z-10 bg-zinc-900/80">
           <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-500 flex items-center gap-2">
             <Cpu size={14} /> AI Analysis
           </h2>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
          
          <section>
            <h3 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-3">Extracted Text</h3>
            <div className="p-4 bg-zinc-950/50 rounded-xl border border-zinc-800/50 text-sm font-mono text-zinc-300 leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto shadow-inner">
              {currentAnswer.transcribed_text || "No text extracted."}
            </div>
          </section>

          <section>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest">Reasoning Summary</h3>
              <span className="px-2.5 py-1 rounded-md bg-indigo-500/20 text-indigo-300 font-bold text-xs">
                Score: {currentAnswer.grade?.ai_score}
              </span>
            </div>
            <div className="p-4 bg-indigo-950/20 rounded-xl border border-indigo-900/30 text-sm text-zinc-300 leading-relaxed">
              {currentAnswer.grade?.ai_justification || "No justification provided."}
            </div>
          </section>

          {currentAnswer.grade?.ai_breakdown_json?.criteria_evals && (
            <section>
              <h3 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-3">Rubric Breakdown</h3>
              <div className="space-y-3">
                {currentAnswer.grade.ai_breakdown_json.criteria_evals.map((e, i) => (
                  <div key={i} className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800 hover:border-zinc-700 transition-colors">
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-sm font-semibold text-zinc-200">{e.criterion_id}</span>
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        e.status === 'met' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 
                        e.status === 'partial' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 
                        'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}>
                        {e.marks_awarded} pts
                      </span>
                    </div>
                    <p className="text-xs text-zinc-400 leading-relaxed">{e.reasoning}</p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>

      {/* RIGHT PANE: Human Decision */}
      <div className="w-[360px] bg-zinc-900 flex flex-col shadow-2xl z-20">
        <div className="h-14 border-b border-zinc-800 flex items-center px-6">
           <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-500 flex items-center gap-2">
             <UserCheck size={14} /> Human Override
           </h2>
        </div>
        
        <div className="p-6 flex-1 flex flex-col">
          
          <div className="mb-8">
            <label className="block text-xs font-bold text-zinc-500 uppercase tracking-widest mb-3 text-center">Final Awarded Score</label>
            <div className="relative flex items-center justify-center">
              <input 
                type="number" 
                className="w-32 h-24 text-5xl font-black text-center text-zinc-100 bg-zinc-950 border-2 border-zinc-800 focus:border-indigo-500 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/20 transition-all"
                value={finalScore}
                onChange={e => setFinalScore(e.target.value)}
                step="0.5"
              />
            </div>
          </div>

          <div className="mb-8">
            <label className="block text-xs font-bold text-zinc-500 uppercase tracking-widest mb-3">Auditor Notes</label>
            <textarea 
              id="notes_input"
              className="w-full h-32 p-4 bg-zinc-950 border border-zinc-800 focus:border-indigo-500 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 resize-none text-sm text-zinc-300 placeholder:text-zinc-700 transition-all"
              placeholder="Leave blank to implicitly agree with AI. Add notes if overriding."
              value={taNotes}
              onChange={e => setTaNotes(e.target.value)}
            />
          </div>

          <div className="mt-auto space-y-3">
            <button
              className="w-full py-4 rounded-xl text-white font-bold tracking-wide flex items-center justify-center gap-2 shadow-lg hover:-translate-y-0.5 transition-all focus:outline-none focus:ring-4"
              style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', boxShadow: '0 4px 20px -2px rgba(16,185,129,0.3)' }}
              onClick={() => submitReview(true)}
            >
              <CheckCircle2 size={20} /> Approve & Next
            </button>
            <button
              className="w-full py-4 rounded-xl text-rose-400 font-bold bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 flex items-center justify-center gap-2 transition-all"
              onClick={() => submitReview(false)}
            >
              <AlertCircle size={20} /> Save Override
            </button>
          </div>

          <div className="mt-8 pt-6 border-t border-zinc-800">
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs font-semibold text-zinc-500 uppercase tracking-widest">Queue Progress</span>
              <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded">
                {currentIndex + 1} / {answers.length}
              </span>
            </div>
            <div className="w-full bg-zinc-950 rounded-full h-1.5 overflow-hidden">
              <div 
                className="bg-indigo-500 h-1.5 rounded-full transition-all duration-500 ease-out" 
                style={{ width: `${((currentIndex + 1) / answers.length) * 100}%` }} 
              />
            </div>
          </div>
          
          <div className="mt-6 flex flex-wrap justify-center gap-4 border-t border-zinc-800/50 pt-4">
             <div className="flex items-center gap-1.5"><kbd className="px-1.5 py-0.5 bg-zinc-800 border border-zinc-700 rounded text-[10px] font-mono text-zinc-400">A</kbd> <span className="text-[10px] text-zinc-500 font-semibold uppercase">Approve</span></div>
             <div className="flex items-center gap-1.5"><kbd className="px-1.5 py-0.5 bg-zinc-800 border border-zinc-700 rounded text-[10px] font-mono text-zinc-400">R</kbd> <span className="text-[10px] text-zinc-500 font-semibold uppercase">Note</span></div>
             <div className="flex items-center gap-1.5"><kbd className="px-1.5 py-0.5 bg-zinc-800 border border-zinc-700 rounded text-[10px] font-mono text-zinc-400">J/K</kbd> <span className="text-[10px] text-zinc-500 font-semibold uppercase">Nav</span></div>
          </div>

        </div>
      </div>
    </div>
  );
}
