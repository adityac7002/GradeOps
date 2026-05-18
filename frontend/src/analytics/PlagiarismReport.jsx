import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import {
  Search, Play, AlertTriangle, CheckCircle2, ChevronDown,
  Loader2, Activity, ShieldAlert, FileText
} from 'lucide-react';

export default function PlagiarismReport() {
  const { authFetch } = useAuth();
  const { addToast } = useToast();
  const [exams, setExams] = useState([]);
  const [examId, setExamId] = useState('');
  const [pairs, setPairs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [examsLoading, setExamsLoading] = useState(true);

  useEffect(() => {
    authFetch('/api/exams')
      .then(r => r.json())
      .then(data => setExams(Array.isArray(data) ? data : (data.items ?? [])))
      .catch(() => addToast('Failed to load exams', 'error'))
      .finally(() => setExamsLoading(false));
  }, []);

  const loadReport = async (eid) => {
    if (!eid) return;
    setLoading(true);
    setPairs([]);
    try {
      const res = await authFetch(`/api/exams/${eid}/plagiarism`);
      const data = await res.json();
      setPairs(Array.isArray(data) ? data : []);
    } catch {
      addToast('Failed to load similarity report', 'error');
    } finally {
      setLoading(false);
    }
  };

  const runDetection = async () => {
    if (!examId) return;
    setRunning(true);
    try {
      await authFetch(`/api/exams/${examId}/plagiarism/run`, { method: 'POST' });
      addToast('Similarity scan complete', 'success');
      await loadReport(examId);
    } catch {
      addToast('Scan failed', 'error');
    } finally {
      setRunning(false);
    }
  };

  const selectExam = (eid) => {
    setExamId(eid);
    setPairs([]);
    if (eid) loadReport(eid);
  };

  const pct = (score) => Math.round(score * 100);

  const getSeverity = (score) => {
    if (score >= 0.9) return { label: 'Critical', bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', badge: 'bg-red-100 text-red-800 border-red-200' };
    if (score >= 0.8) return { label: 'High', bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', badge: 'bg-orange-100 text-orange-800 border-orange-200' };
    return { label: 'Medium', bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200', badge: 'bg-yellow-100 text-yellow-800 border-yellow-200' };
  };

  const criticalCount = pairs.filter(p => p.similarity_score >= 0.9).length;
  const highCount = pairs.filter(p => p.similarity_score >= 0.8 && p.similarity_score < 0.9).length;

  return (
    <div className="page-wrapper py-10 animate-in fade-in duration-500">
      <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-10">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <ShieldAlert size={22} className="text-accent" />
            <h1 className="text-3xl font-bold tracking-tight text-text">Similarity Analysis</h1>
          </div>
          <p className="text-text2 mt-1">
            Cross-reference student submissions via TF-IDF cosine similarity to surface potential collusion.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <select
              className="form-select appearance-none pr-8 min-w-[220px] cursor-pointer"
              value={examId}
              onChange={e => selectExam(e.target.value)}
              disabled={examsLoading}
            >
              <option value="">
                {examsLoading ? 'Loading pipelines...' : 'Select pipeline…'}
              </option>
              {exams.map(ex => (
                <option key={ex.id} value={ex.id}>{ex.title}</option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text3 pointer-events-none" />
          </div>

          <button
            className="btn btn-primary"
            onClick={runDetection}
            disabled={!examId || running}
          >
            {running
              ? <><Loader2 size={16} className="animate-spin" /> Scanning…</>
              : <><Play size={15} /> Execute Scan</>
            }
          </button>
        </div>
      </header>

      {/* Summary alert banner */}
      {!loading && pairs.length > 0 && (
        <div className="flex items-start gap-4 p-4 mb-8 bg-red-50 border border-red-200 rounded-xl animate-in fade-in duration-300">
          <AlertTriangle className="text-red-600 mt-0.5 shrink-0" size={20} />
          <div>
            <p className="text-sm font-semibold text-red-800">
              {pairs.length} similarity cluster{pairs.length !== 1 ? 's' : ''} detected
            </p>
            <p className="text-xs text-red-600 mt-0.5">
              {criticalCount > 0 && `${criticalCount} critical`}
              {criticalCount > 0 && highCount > 0 && ', '}
              {highCount > 0 && `${highCount} high-risk`}
              {' '}— manual verification recommended.
            </p>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="card py-24 flex flex-col items-center justify-center text-text3">
          <Activity className="animate-spin mb-4" size={32} />
          <p className="text-sm font-medium">Retrieving similarity matrices…</p>
        </div>
      )}

      {/* No exam selected */}
      {!loading && !examId && (
        <div className="card py-24 flex flex-col items-center justify-center text-center">
          <div className="w-16 h-16 bg-surface2 rounded-full flex items-center justify-center mx-auto mb-4 text-text3 border border-border">
            <Search size={28} />
          </div>
          <h3 className="text-lg font-semibold text-text mb-1">Select a Pipeline</h3>
          <p className="text-sm text-text2 max-w-sm">
            Choose an exam pipeline above to load or run a similarity scan across all student submissions.
          </p>
        </div>
      )}

      {/* Exam selected but empty results */}
      {!loading && examId && pairs.length === 0 && (
        <div className="card py-24 flex flex-col items-center justify-center text-center">
          <CheckCircle2 size={48} className="text-green-500 mb-4" />
          <h3 className="text-lg font-semibold text-text mb-1">No Collusion Detected</h3>
          <p className="text-sm text-text2 max-w-sm">
            All submissions are within normal variance thresholds. Run a scan to refresh results.
          </p>
        </div>
      )}

      {/* Results grid */}
      {!loading && pairs.length > 0 && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
          {pairs.map((pair, i) => {
            const severity = getSeverity(pair.similarity_score);
            return (
              <div
                key={i}
                className={`card !p-0 overflow-hidden border ${severity.border}`}
              >
                {/* Pair header */}
                <div className={`px-5 py-4 border-b ${severity.border} ${severity.bg} flex items-center justify-between`}>
                  <div className="flex items-center gap-3">
                    <span className="px-2 py-0.5 bg-accent text-white text-xs font-mono font-bold rounded">
                      Q{pair.question_number}
                    </span>
                    <span className="text-sm font-mono font-semibold text-text">
                      {pair.student_id_a}
                      <span className="text-text3 font-normal mx-2">vs</span>
                      {pair.student_id_b}
                    </span>
                  </div>
                  <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold border ${severity.badge}`}>
                    <AlertTriangle size={11} />
                    {pct(pair.similarity_score)}% · {severity.label}
                  </span>
                </div>

                {/* Answer comparison */}
                <div className="grid grid-cols-2 divide-x divide-border">
                  {[
                    { label: 'Submission A', text: pair.ocr_text_a },
                    { label: 'Submission B', text: pair.ocr_text_b },
                  ].map(({ label, text }) => (
                    <div key={label} className="p-4 flex flex-col">
                      <div className="flex items-center gap-1.5 mb-3">
                        <FileText size={12} className="text-text3" />
                        <h4 className="text-[10px] uppercase tracking-wider font-semibold text-text3">
                          {label}
                        </h4>
                      </div>
                      <div className="flex-1 bg-surface2 rounded-lg p-3 border border-border overflow-y-auto max-h-40">
                        {text
                          ? <p className="text-sm text-text font-mono whitespace-pre-wrap leading-relaxed">{text}</p>
                          : <p className="text-xs text-text3 italic">No OCR data extracted</p>
                        }
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
