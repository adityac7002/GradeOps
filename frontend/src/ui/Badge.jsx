const STATUS_BADGE = {
  uploaded:   'text-blue-400 bg-blue-400/10 border-blue-400/20',
  processing: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20',
  graded:     'text-[#a78bfa] bg-[#a78bfa]/10 border-[#a78bfa]/20',
  reviewing:  'text-orange-400 bg-orange-400/10 border-orange-400/20',
  complete:   'text-[#22c55e] bg-[#22c55e]/10 border-[#22c55e]/20',
};

export function Badge({ status }) {
  const cls = STATUS_BADGE[status] ?? 'text-blue-400 bg-blue-400/10 border-blue-400/20';
  return (
    <span className={`px-2 py-0.5 rounded border text-[10px] uppercase tracking-wider font-mono font-semibold ${cls}`}>
      {status}
    </span>
  );
}
