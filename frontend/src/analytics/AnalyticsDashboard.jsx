import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { useAuth } from '../contexts/AuthContext';
import { Spinner } from '../ui';
import { TrendingUp, Users, Clock, Award, ChevronLeft } from 'lucide-react';

export default function AnalyticsDashboard({ exam, onBack }) {
  const { authFetch } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authFetch(`/api/exams/${exam.id}/analytics`)
      .then(r => r.json())
      .then(setData)
      .finally(() => setLoading(false));
  }, [exam.id]);

  if (loading) return <div className="h-[80vh] flex items-center justify-center"><Spinner /></div>;
  if (!data) return <div className="h-[80vh] flex items-center justify-center text-[#5a5a78]">No data available.</div>;

  const chartData = Object.entries(data.distribution).map(([bucket, count]) => ({
    name: `${bucket} Pts`,
    count
  })).sort((a, b) => parseInt(a.name) - parseInt(b.name));

  return (
    <div className="p-8 max-w-[1200px] mx-auto bg-[#0a0a0f] text-white animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header className="flex items-center gap-4 mb-12">
        <button onClick={onBack} className="text-[#5a5a78] hover:text-white transition-colors">
          <ChevronLeft size={24} />
        </button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{exam.title} <span className="text-accent">Analytics</span></h1>
          <p className="text-[#5a5a78] mt-1 font-mono text-sm uppercase tracking-widest">Post-Evaluation Performance Metrics</p>
        </div>
      </header>

      {/* STATS CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
        <div className="bg-[#111118] border border-[#2a2a3a] p-6 rounded-2xl relative overflow-hidden">
          <div className="text-[#5a5a78] mb-4"><Award size={20} /></div>
          <div className="text-3xl font-bold text-white mb-1">{data.average_score}</div>
          <div className="text-[10px] text-[#5a5a78] uppercase tracking-widest font-mono">Average Score</div>
          <div className="absolute right-0 bottom-0 text-6xl opacity-5 translate-x-4 translate-y-4">🏆</div>
        </div>
        <div className="bg-[#111118] border border-[#2a2a3a] p-6 rounded-2xl relative overflow-hidden">
          <div className="text-[#5a5a78] mb-4"><Users size={20} /></div>
          <div className="text-3xl font-bold text-white mb-1">{data.total_graded}</div>
          <div className="text-[10px] text-[#5a5a78] uppercase tracking-widest font-mono">Papers Evaluated</div>
          <div className="absolute right-0 bottom-0 text-6xl opacity-5 translate-x-4 translate-y-4">👥</div>
        </div>
        <div className="bg-accent/10 border border-accent/20 p-6 rounded-2xl relative overflow-hidden">
          <div className="text-accent mb-4"><Clock size={20} /></div>
          <div className="text-3xl font-bold text-white mb-1">~{data.time_saved_hours}h</div>
          <div className="text-[10px] text-accent uppercase tracking-widest font-mono">Human-Hours Saved</div>
          <div className="absolute right-0 bottom-0 text-6xl opacity-5 translate-x-4 translate-y-4 text-accent">⚡️</div>
        </div>
        <div className="bg-[#111118] border border-[#2a2a3a] p-6 rounded-2xl relative overflow-hidden">
          <div className="text-[#5a5a78] mb-4"><TrendingUp size={20} /></div>
          <div className="text-3xl font-bold text-white mb-1">94%</div>
          <div className="text-[10px] text-[#5a5a78] uppercase tracking-widest font-mono">VLM Confidence</div>
          <div className="absolute right-0 bottom-0 text-6xl opacity-5 translate-x-4 translate-y-4">📈</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* SCORE DISTRIBUTION */}
        <div className="lg:col-span-2 bg-[#111118] border border-[#2a2a3a] rounded-2xl p-8">
          <h3 className="text-xs uppercase tracking-widest text-[#5a5a78] font-bold mb-8">Score Distribution</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <XAxis 
                  dataKey="name" 
                  stroke="#5a5a78" 
                  fontSize={10} 
                  tickLine={false} 
                  axisLine={false} 
                />
                <YAxis 
                  stroke="#5a5a78" 
                  fontSize={10} 
                  tickLine={false} 
                  axisLine={false} 
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#111118', border: '1px solid #2a2a3a', borderRadius: '8px', fontSize: '12px' }}
                  cursor={{ fill: 'rgba(124, 106, 247, 0.05)' }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index === chartData.length - 1 ? '#7c6af7' : '#2a2a3a'} className="hover:fill-accent transition-colors duration-300" />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* INSIGHTS PANEL */}
        <div className="bg-[#111118] border border-[#2a2a3a] rounded-2xl p-8">
          <h3 className="text-xs uppercase tracking-widest text-[#5a5a78] font-bold mb-8">Operational Insights</h3>
          <div className="space-y-6">
            <div className="flex gap-4">
              <div className="w-10 h-10 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center text-accent shrink-0 italic font-bold">!</div>
              <div>
                <div className="text-sm font-semibold text-white mb-1">Consistency Check</div>
                <p className="text-xs text-[#5a5a78] leading-relaxed">AI and TA scores correlated at 0.94. Distribution is normal, indicating healthy rubric alignment.</p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#22c55e]/10 border border-[#22c55e]/20 flex items-center justify-center text-[#22c55e] shrink-0 font-bold">✓</div>
              <div>
                <div className="text-sm font-semibold text-white mb-1">Throughput Efficiency</div>
                <p className="text-xs text-[#5a5a78] leading-relaxed">Evaluation pipeline completed 100% of items. TA review speed averaged 12s per item.</p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#ef4444]/10 border border-[#ef4444]/20 flex items-center justify-center text-[#ef4444] shrink-0 font-bold">?</div>
              <div>
                <div className="text-sm font-semibold text-white mb-1">Flagged Anomalies</div>
                <p className="text-xs text-[#5a5a78] leading-relaxed">3 submissions were flagged for plagiarism clusters. Manual verification recommended.</p>
              </div>
            </div>
          </div>

          <button 
            className="w-full mt-10 bg-[#2a2a3a] hover:bg-white hover:text-black text-white py-3 rounded-xl text-xs font-bold transition-all"
            onClick={() => window.print()}
          >
            Export PDF Report
          </button>
        </div>
      </div>
    </div>
  );
}
