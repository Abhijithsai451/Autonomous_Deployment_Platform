import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/authService';
import { useAuth } from '../../../context/AuthContext';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';
import { Card } from '../../../components/ui/Card';

export const LoginForm: React.FC = () => {
  const navigate = useNavigate();
  const { setSession } = useAuth();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('adminpassword');
  const [clientId, setClientId] = useState('cortexops-backend');
  const [clientSecret, setClientSecret] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const tokens = await authService.login({ username, password, clientId, clientSecret });
      setSession(tokens.access_token, { id: 'temp-id', username });

      // Attempt to load full profile
      try {
        const profile = await authService.getProfile();
        setSession(tokens.access_token, profile);
      } catch (profileError) {
        console.warn('Fallback profile loaded due to endpoint failure.', profileError);
      }

      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div class="min-h-screen flex items-center justify-center bg-slate-950 px-4">
      <Card class="w-full max-w-md">
        <div class="mb-8 text-center">
          <h1 class="text-3xl font-extrabold text-blue-400 tracking-wider">CORTEXOPS</h1>
          <p class="text-xs text-slate-400 mt-1">Enterprise SSO Orchestration Console</p>
        </div>

        {error && (
          <div class="mb-4 p-3 bg-red-950/50 border border-red-900 rounded text-xs text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} class="space-y-4">
          <Input label="Username" value={username} onChange={e => setUsername(e.target.value)} required />
          <Input label="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} required />

          <div class="grid grid-cols-2 gap-4">
            <Input label="Client ID" value={clientId} onChange={e => setClientId(e.target.value)} required />
            <Input label="Client Secret" type="password" value={clientSecret} onChange={e => setClientSecret(e.target.value)} placeholder="Optional" />
          </div>

          <Button type="submit" isLoading={loading} className="w-full mt-6">
            Authenticate Operator
          </Button>
        </form>
      </Card>
    </div>
  );
};