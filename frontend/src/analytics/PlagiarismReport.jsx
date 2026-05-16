import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Spinner } from '../ui';

export default function PlagiarismReport() {
  const { authFetch } = useAuth();
  const [exams, setExams] = useState([]);
  const [examId, setExamId] = useState('');
  const [pairs, setPairs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    authFetch('/api/exams').then(r => r.json()).then(setExams);
  }, []);

  const loadReport = async (eid) => {
    if (!eid) return;
    setLoading(true);
    const res = await authFetch(`/api/exams/${eid}/plagiarism`);
    const data = await res.json();
    setPairs(data);
    setLoading(false);
  };

  const runDetection = async () => {
    if (!examId) return;
    setRunning(true);
    await authFetch(`/api/exams/${examId}/plagiarism/run`, { method: 'POST' });
    await loadReport(examId);
    setRunning(false);
  };

  const selectExam = eid => {
    setExamId(eid);
    setPairs([]);
    if (eid) loadReport(eid);
  };

  const pct = score => Math.round(score * 100);
  const severityClass = score => score >= 0.9 ? 'high' : score >= 0.8 ? 'med' : 'low';
  
  const getSeverityStyle = (score) => {
    if (score >= 0.9) return 'text-[#ef4444] bg-[#ef4444]/10 border-[#ef4444]/20';
    if (score >= 0.8) return 'text-orange-400 bg-orange-400/10 border-orange-400/20';
    return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20';
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-[#e2e2f0] p-8 font-sans selection:bg-accent-glow">
      <div className="max-w-[1400px] mx-auto flex flex-col gap-8">
        
        {/* HEADER */}
        <header className="flex flex-col gap-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
                <span className="text-accent">🚨</span> Similarity Analysis
              </h1>
              <p className="text-[#9898b8] text-sm mt-1">Cross-reference all extracted student answers via TF-IDF cosine similarity.</p>
            </div>
            
            <div className="flex items-center gap-3 bg-[#111118] border border-[#2a2a3a] rounded-lg p-2 shadow-sm">
              <select 
                className="bg-[#1a1a25] border border-[#3a3a50] rounded px-4 py-2 text-sm text-white focus:outline-none focus:border-accent transition-colors min-w-[250px] appearance-none"
                value={examId} 
                onChange={e => selectExam(e.target.value)}
              >
                <option value="">Select pipeline...</option>
                {exams.map(ex => <option key={ex.id} value={ex.id}>{ex.title}</option>)}
              </select>
              <button 
                className="px-5 py-2 bg-accent text-white hover:bg-accent2 rounded text-sm font-semibold transition-all disabled:opacity-50 flex items-center gap-2 shadow-[0_0_15px_rgba(124,106,247,0.2)]"
                onClick={runDetection} 
                disabled={!examId || running}
              >
                {running ? <><Spinner /> Analyzing...</> : 'Execute Scan'}
              </button>
            </div>
          </div>
        </header>

        {/* LOADING STATE */}
        {loading && (
          <div className="flex-1 flex flex-col items-center justify-center text-[#5a5a78] gap-4 py-24 bg-[#111118] border border-[#2a2a3a] rounded-xl">
            <Spinner large />
            <span className="font-mono text-sm uppercase tracking-wider">Retrieving Similarity Matrices...</span>
          </div>
        )}

        {/* EMPTY STATE */}
        {!loading && examId && pairs.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center text-[#5a5a78] gap-2 py-24 bg-[#111118] border border-[#2a2a3a] rounded-xl border-dashed">
            <div className="text-4xl mb-2 opacity-50 text-[#22c55e]">✓</div>
            <h2 className="text-lg font-medium text-[#9898b8]">No Collusion Detected</h2>
            <p className="text-sm">All submissions within normal variance thresholds.</p>
          </div>
        )}

        {/* RESULTS GRID */}
        {!loading && pairs.length > 0 && (
          <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            
            <div className="bg-[#ef4444]/10 border border-[#ef4444]/20 rounded-lg p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-xl">⚠️</span>
                <div>
                  <h3 className="text-[#ef4444] font-semibold text-sm">Action Required</h3>
                  <p className="text-[#ef4444]/80 text-xs mt-0.5">Identified {pairs.length} high-confidence similarity cluster{pairs.length !== 1 ? 's' : ''}.</p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              {pairs.map((pair, i) => (
                <div key={i} className="bg-[#111118] border border-[#2a2a3a] rounded-xl overflow-hidden shadow-sm flex flex-col hover:border-[#3a3a50] transition-colors">
                  
                  {/* Pair Header */}
                  <div className="bg-[#1a1a25] border-b border-[#2a2a3a] px-5 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="bg-[#2a2a3a] text-white font-mono text-xs px-2 py-1 rounded font-semibold">Q{pair.question_number}</div>
                      <div className="flex items-center gap-3 text-sm font-mono font-medium">
                        <span className="text-white">{pair.student_id_a}</span>
                        <span className="text-[#5a5a78]">vs</span>
                        <span className="text-white">{pair.student_id_b}</span>
                      </div>
                    </div>
                    
                    <div className={`px-3 py-1 rounded border font-mono text-xs font-bold ${getSeverityStyle(pair.similarity_score)}`}>
                      {pct(pair.similarity_score)}% MATCH
                    </div>
                  </div>

                  {/* Pair Content Comparison */}
                  <div className="flex-1 grid grid-cols-2 divide-x divide-[#2a2a3a]">
                    
                    <div className="p-5 flex flex-col bg-[#0a0a0f]">
                      <h4 className="text-[10px] uppercase tracking-wider text-[#5a5a78] mb-3 font-semibold font-mono">Submission A</h4>
                      <div className="flex-1 bg-[#111118] border border-[#2a2a3a] rounded-md p-4 overflow-y-auto">
                        <p className="text-sm text-[#e2e2f0] font-mono whitespace-pre-wrap leading-relaxed">{pair.ocr_text_a || <span className="italic opacity-50">No OCR data extracted</span>}</p>
                      </div>
                    </div>

                    <div className="p-5 flex flex-col bg-[#0a0a0f]">
                      <h4 className="text-[10px] uppercase tracking-wider text-[#5a5a78] mb-3 font-semibold font-mono">Submission B</h4>
                      <div className="flex-1 bg-[#111118] border border-[#2a2a3a] rounded-md p-4 overflow-y-auto">
                        <p className="text-sm text-[#e2e2f0] font-mono whitespace-pre-wrap leading-relaxed">{pair.ocr_text_b || <span className="italic opacity-50">No OCR data extracted</span>}</p>
                      </div>
                    </div>

                  </div>
                </div>
              ))}
            </div>
            
          </div>
        )}
      </div>
    </div>
  );
}
