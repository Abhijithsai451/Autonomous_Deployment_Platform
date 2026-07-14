export interface LoginCredentials {
  username: string;
  password: string;
  clientId: string;
  clientSecret?: string;
}

export interface TokenResponse {
  access_token: string;
  expires_in: number;
  refresh_token?: string;
  token_type: string;
}

export interface UserProfile {
  id: string;
  username: string;
  email?: string;
  firstName?: string;
  lastName?: string;
}