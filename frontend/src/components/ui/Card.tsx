import React from 'react';

export const Card: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => {
  return (
    <div className={`bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg ${className}`}>
      {children}
    </div>
  );
};