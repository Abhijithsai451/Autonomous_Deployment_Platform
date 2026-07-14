import React, { useEffect, useState } from 'react';
import { organizationService, Organization } from '../services/organizationService';
import { Card } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';

export const OrganizationList: React.FC = () => {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchOrgs = async () => {
    try {
      const data = await organizationService.list();
      setOrganizations(data);
    } catch (err: any) {
      setError('Failed to query organization domain registries.');
    }
  };

  useEffect(() => {
    fetchOrgs();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await organizationService.create({ name, slug });
      setName('');
      setSlug('');
      fetchOrgs();
    } catch (err: any) {
      setError('Registration transaction failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div class="space-y-6">
      <header>
        <h1 class="text-2xl font-extrabold tracking-tight">Organization Registries</h1>
        <p class="text-sm text-slate-400">View and scale registered global environments.</p>
      </header>

      {error && (
        <div class="p-3 bg-red-950/50 border border-red-900 rounded text-xs text-red-400">
          {error}
        </div>
      )}

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card class="lg:col-span-1 h-fit">
          <h2 class="text-sm font-bold text-slate-300 mb-4">Register Workspace</h2>
          <form onSubmit={handleCreate} class="space-y-4">
            <Input label="Name" placeholder="Cortex West" value={name} onChange={e => setName(e.target.value)} required />
            <Input label="Domain Identifier (Slug)" placeholder="cortex-west" value={slug} onChange={e => setSlug(e.target.value)} required />
            <Button type="submit" isLoading={loading} className="w-full">Initialize Node</Button>
          </form>
        </Card>

        <Card class="lg:col-span-2">
          <h2 class="text-sm font-bold text-slate-300 mb-4">Active Directories</h2>
          {organizations.length === 0 ? (
            <p class="text-sm text-slate-500">No organizational structures found on active cluster.</p>
          ) : (
            <div class="divide-y divide-slate-800">
              {organizations.map(org => (
                <div key={org.id} class="py-3 flex justify-between items-center">
                  <div>
                    <h3 class="font-bold text-sm text-slate-100">{org.name}</h3>
                    <p class="text-xs text-slate-400 font-mono">/{org.slug}</p>
                  </div>
                  <span class="text-xs text-slate-500 font-mono">
                    {new Date(org.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};