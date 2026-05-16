import { useState } from 'react';

export function useToast() {
  const [toasts, setToasts] = useState([]);
  
  const addToast = (msg, type = 'success') => {
    const id = Date.now();
    setToasts(ts => [...ts, { id, msg, type }]);
    setTimeout(() => setToasts(ts => ts.filter(t => t.id !== id)), 3000);
  };
  
  return { toasts, addToast };
}
