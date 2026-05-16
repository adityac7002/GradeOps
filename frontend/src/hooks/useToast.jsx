import { createContext, useContext, useState } from 'react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = (message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 3000);
  };

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <div className="fixed bottom-8 right-8 z-[100] flex flex-col gap-3">
        {toasts.map(t => (
          <div 
            key={t.id} 
            className={`px-6 py-4 rounded-xl shadow-2xl border flex items-center gap-3 animate-in slide-in-from-right-8 duration-300 ${
              t.type === 'error' ? 'bg-[#ef4444] border-red-400 text-white' : 
              t.type === 'success' ? 'bg-[#22c55e] border-green-400 text-white' : 
              'bg-[#111118] border-[#2a2a3a] text-white'
            }`}
          >
            <span className="text-lg">
              {t.type === 'error' ? '🚨' : t.type === 'success' ? '✅' : 'ℹ️'}
            </span>
            <span className="text-sm font-medium">{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
