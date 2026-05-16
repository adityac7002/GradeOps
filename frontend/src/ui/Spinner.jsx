export function Spinner({ large }) {
  const size = large ? 'w-8 h-8 border-4' : 'w-4 h-4 border-2';
  return (
    <div 
      className={`rounded-full border-t-transparent border-accent animate-spin ${size}`} 
      style={{ borderTopColor: 'transparent' }} 
    />
  );
}
