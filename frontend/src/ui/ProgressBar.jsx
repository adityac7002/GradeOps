export function ProgressBar({ value, max }) {
  const pct = max ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="w-full bg-[#1a1a25] border border-[#2a2a3a] h-2 rounded-full overflow-hidden">
      <div 
        className="h-full bg-accent transition-all duration-500 ease-in-out shadow-[0_0_10px_rgba(124,106,247,0.5)]" 
        style={{ width: `${pct}%` }} 
      />
    </div>
  );
}
