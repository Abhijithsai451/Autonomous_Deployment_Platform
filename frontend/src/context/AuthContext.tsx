import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { UserProfile } from '../features/auth/types';

interface AuthContextType {
  token: string | null;
  user: UserProfile | null;
  isAuthenticated: boolean;
  setSession: (token: string, user: UserProfile) => void;
  clearSession: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('cortex_token'));
  const [user, setUser] = useState<UserProfile | null>(null);

  useEffect(() => {
    const handleAuthExpiry = () => clearSession();
    window.addEventListener('auth_expired', handleAuthExpiry);
    return () => window.removeEventListener('auth_expired', handleAuthExpiry);
  }, []);

  const setSession = (newToken: string, newUser: UserProfile) => {
    localStorage.setItem('cortex_token', newToken);
    setToken(newToken);
    setUser(newUser);
  };

  const clearSession = () => {
    localStorage.removeItem('cortex_token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ token, user, isAuthenticated: !!token, setSession, clearSession }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};