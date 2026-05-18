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
      <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-3">
        {toasts.map(t => (
          <div 
            key={t.id} 
            className={`px-5 py-3 rounded-lg shadow-elevated border flex items-center gap-3 animate-in slide-in-from-right-8 duration-300 bg-white ${
              t.type === 'error' ? 'border-red-200 text-red-900' : 
              t.type === 'success' ? 'border-green-200 text-green-900' : 
              'border-border text-text'
            }`}
          >
            <span className="text-base">
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
