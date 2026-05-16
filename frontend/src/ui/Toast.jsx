export function Toast({ toasts }) {
  return (
    <div className="fixed bottom-6 right-6 z-[200] flex flex-col gap-3 pointer-events-none">
      {toasts.map(t => {
        const isError = t.type === 'error';
        return (
          <div key={t.id} className={`flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg backdrop-blur-md animate-in slide-in-from-bottom-5 duration-300 pointer-events-auto ${
            isError ? 'bg-red-500/10 border-red-500/20 text-red-400' : 'bg-[#22c55e]/10 border-[#22c55e]/20 text-[#22c55e]'
          }`}>
            <span className="text-lg">{isError ? '⚠️' : '✓'}</span>
            <span className="text-sm font-medium">{t.msg}</span>
          </div>
        );
      })}
    </div>
  );
}
