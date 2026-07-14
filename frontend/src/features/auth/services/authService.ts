import { apiClient } from '../../../services/apiClient';
import { LoginCredentials, TokenResponse, UserProfile } from '../types';

export const authService = {
  /**
   * Performs Keycloak-backed OAuth2 password grant authentication
   */
  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    const params = new URLSearchParams();
    params.append('grant_type', 'password');
    params.append('username', credentials.username);
    params.append('password', credentials.password);
    params.append('client_id', credentials.clientId);
    if (credentials.clientSecret) {
      params.append('client_secret', credentials.clientSecret);
    }

    const { data } = await apiClient.post<TokenResponse>('/auth/login', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return data;
  },

  /**
   * Retrieves active user data from token context
   */
  async getProfile(): Promise<UserProfile> {
    const { data } = await apiClient.get<UserProfile>('/auth/me');
    return data;
  }
};