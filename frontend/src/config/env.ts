export const env = {
  API_URL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  KEYCLOAK_URL: import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8080',
};