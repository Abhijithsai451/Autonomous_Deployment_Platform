import React from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const DashboardLayout: React.FC = () => {
  const { clearSession, user } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    clearSession();
    navigate('/login');
  };

  return (
    <div class="flex h-screen bg-slate-950 text-slate-100 font-sans">
      {/* Structural Left Sidebar */}
      <aside class="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between p-6">
        <div>
          <h2 class="text-xl font-extrabold text-blue-400 tracking-wider">CortexOps</h2>
          <nav class="mt-8 space-y-2">
            <a href="/dashboard" class="block px-4 py-2 bg-slate-800 rounded hover:text-blue-400 transition">Dashboard</a>
            <a href="/organizations" class="block px-4 py-2 hover:bg-slate-800 rounded hover:text-blue-400 transition">Organizations</a>
          </nav>
        </div>
        <div class="border-t border-slate-800 pt-4 flex justify-between items-center">
          <div class="text-xs">
            <p class="font-bold">{user?.username || 'Active Operator'}</p>
            <p class="text-slate-500">Local Environment</p>
          </div>
          <button onClick={handleLogout} class="text-xs text-red-400 hover:underline">Exit</button>
        </div>
      </aside>

      {/* Main Content Pane */}
      <main class="flex-1 flex flex-col overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  );
};