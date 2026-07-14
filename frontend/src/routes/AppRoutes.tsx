import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from './ProtectedRoute';
import { DashboardLayout } from '../layouts/DashboardLayout';
import { LoginForm } from '../features/auth/components/LoginForm';
import { OrganizationList } from '../features/organizations/components/OrganizationList';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Open Routes */}
      <Route path="/login" element={<LoginForm />} />

      {/* Authenticated Application Shell */}
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={
            <div class="space-y-4">
              <h1 class="text-2xl font-extrabold">Control Center</h1>
              <p class="text-slate-400 text-sm">System nodes operational. Monitor transactions directly in active registries.</p>
            </div>
          } />
          <Route path="/organizations" element={<OrganizationList />} />
        </Route>
      </Route>

      {/* Navigation Fallback */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};