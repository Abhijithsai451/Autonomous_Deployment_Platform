# Identity Service API

## Authentication (Bridge to Keycloak)
- `POST /auth/login` - Initiate session
- `POST /auth/logout` - Terminate session
- `POST /auth/refresh` - Refresh tokens
- `GET /auth/me` - Get profile of authenticated user

## Organizations
- `POST /organizations` - Create new tenant
- `GET /organizations/{id}` - Get details
- `PATCH /organizations/{id}` - Update settings

## Users
- `POST /users/invite` - Invite new user to organization
- `GET /users` - List users
- `PATCH /users/{id}/status` - Enable/Disable user

## Roles & Permissions
- `POST /roles` - Create custom role
- `GET /permissions` - List available system permissions
- `POST /users/{id}/roles` - Assign role to user
- `DELETE /users/{id}/roles/{roleId}` - Remove role assignment

## Service Accounts & API Keys
- `POST /service-accounts` - Create machine identity
- `POST /api-keys` - Generate new API key
- `DELETE /api-keys/{id}` - Revoke API key