export function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-[#0a0a0f]/80 backdrop-blur-sm flex items-center justify-center z-[100] p-4" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="bg-[#111118] border border-[#2a2a3a] rounded-xl shadow-2xl flex flex-col w-full max-w-4xl max-h-[90vh] overflow-hidden animate-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a2a3a] bg-[#1a1a25]">
          <h3 className="text-white font-semibold">{title}</h3>
          <button className="text-[#5a5a78] hover:text-white transition-colors bg-[#0a0a0f] border border-[#3a3a50] rounded px-2 py-1 text-sm font-mono" onClick={onClose}>ESC / ✕</button>
        </div>
        <div className="overflow-y-auto custom-scrollbar p-6">
          {children}
        </div>
      </div>
    </div>
  );
}
