# Database Schema: identity

## Table: organizations
- id: UUID (PK)
- name: VARCHAR(255)
- slug: VARCHAR(100) (Unique)
- status: ENUM('ACTIVE', 'SUSPENDED', 'ARCHIVED')
- plan: ENUM('FREE', 'PRO', 'ENTERPRISE')
- settings: JSONB
- created_at: TIMESTAMPTZ

## Table: users
- id: UUID (PK)
- organization_id: UUID (FK -> organizations)
- keycloak_user_id: UUID (Unique)
- email: VARCHAR(320)
- display_name: VARCHAR(255)
- status: ENUM('ACTIVE', 'INVITED', 'DISABLED')
- ... (timezone, locale, timestamps)

## Table: roles
- id: UUID (PK)
- organization_id: UUID (FK -> organizations)
- name: VARCHAR(100)
- system_role: BOOLEAN
- UNIQUE(organization_id, name)

## Table: permissions
- id: UUID (PK)
- name: VARCHAR(100) (e.g., 'workflow.execute')
- resource: VARCHAR(50)
- action: VARCHAR(50)

## Join Tables
- role_permissions: (role_id, permission_id)
- user_roles: (user_id, role_id)

## Security Tables
- sessions: (id, user_id, device_name, ip_address, metadata, ...)
- service_accounts: (id, organization_id, client_id, description)
- api_keys: (id, organization_id, service_account_id, hashed_key, expires_at)