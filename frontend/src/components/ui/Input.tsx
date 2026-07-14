import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input: React.FC<InputProps> = ({ label, error, className = '', ...props }) => {
  return (
    <div class="space-y-1 w-full">
      {label && <label class="block text-xs font-semibold text-slate-400">{label}</label>}
      <input
        className={`w-full bg-slate-900 border ${error ? 'border-red-500' : 'border-slate-800'} rounded px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500 placeholder-slate-600 transition-colors ${className}`}
        {...props}
      />
      {error && <p class="text-xs text-red-400 mt-1">{error}</p>}
    </div>
  );
};