import { apiClient } from '../../../services/apiClient';

export interface Organization {
  id: string;
  name: string;
  slug: string;
  created_at: string;
}

export const organizationService = {
  async list(): Promise<Organization[]> {
    const { data } = await apiClient.get<Organization[]>('/organizations');
    return data;
  },

  async create(payload: { name: string; slug: string }): Promise<Organization> {
    const { data } = await apiClient.post<Organization>('/organizations', payload);
    return data;
  }
};