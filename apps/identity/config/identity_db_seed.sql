\c identity

BEGIN;

-- 1. SEED ORGANIZATIONS
WITH inserted_orgs_raw AS (
    INSERT INTO organizations (name, slug, status, plan, settings) VALUES
    ('Enterprise Corp 1', 'enterprise-corp-1', 'ACTIVE', 'FREE', '{}'),
    ('Enterprise Corp 2', 'enterprise-corp-2', 'ACTIVE', 'FREE', '{}'),
    ('Enterprise Corp 3', 'enterprise-corp-3', 'ACTIVE', 'PRO', '{}'),
    ('Enterprise Corp 4', 'enterprise-corp-4', 'ACTIVE', 'FREE', '{}'),
    ('Enterprise Corp 5', 'enterprise-corp-5', 'ACTIVE', 'ENTERPRISE', '{}'),
    ('Enterprise Corp 6', 'enterprise-corp-6', 'ACTIVE', 'FREE', '{}'),
    ('Enterprise Corp 7', 'enterprise-corp-7', 'ACTIVE', 'FREE', '{}'),
    ('Enterprise Corp 8', 'enterprise-corp-8', 'ACTIVE', 'PRO', '{}'),
    ('Enterprise Corp 9', 'enterprise-corp-9', 'ACTIVE', 'FREE', '{}'),
    ('Enterprise Corp 10', 'enterprise-corp-10', 'ACTIVE', 'ENTERPRISE', '{}')
    RETURNING id
),
inserted_orgs AS (
    SELECT id, row_number() OVER (ORDER BY id) as rn FROM inserted_orgs_raw
),

-- 2. SEED USERS (Linked to Orgs)
inserted_users_raw AS (
    INSERT INTO users (organization_id, keycloak_user_id, email, display_name, status)
    SELECT
        id,
        gen_random_uuid(),
        'user.' || rn || '@enterprisecorp.com',
        'Developer User ' || rn,
        'ACTIVE'::user_status
    FROM inserted_orgs
    RETURNING id, organization_id
),
inserted_users AS (
    SELECT id, organization_id, row_number() OVER (ORDER BY id) as rn FROM inserted_users_raw
),

-- 3. SEED ROLES (Linked to Orgs)
inserted_roles_raw AS (
    INSERT INTO roles (organization_id, name, system_role)
    SELECT id, 'AdminRole', true FROM inserted_orgs
    UNION ALL
    SELECT id, 'DeveloperRole', false FROM inserted_orgs
    RETURNING id, organization_id, name
),
inserted_roles AS (
    SELECT id, organization_id, name, row_number() OVER (ORDER BY id) as rn FROM inserted_roles_raw
),

-- 4. SEED PERMISSIONS (10 Global Records)
inserted_permissions_raw AS (
    INSERT INTO permissions (name, resource, action) VALUES
    ('identity.read', 'identity', 'read'),
    ('identity.write', 'identity', 'write'),
    ('workflow.execute', 'workflow', 'execute'),
    ('workflow.read', 'workflow', 'read'),
    ('org.manage', 'organization', 'manage'),
    ('org.view', 'organization', 'view'),
    ('billing.manage', 'billing', 'manage'),
    ('audit.view', 'audit', 'view'),
    ('secrets.manage', 'secrets', 'manage'),
    ('secrets.read', 'secrets', 'read')
    RETURNING id, name
),
inserted_permissions AS (
    SELECT id, name, row_number() OVER (ORDER BY id) as rn FROM inserted_permissions_raw
),

-- 5. SEED ROLE_PERMISSIONS (Join Table)
inserted_role_perms AS (
    INSERT INTO role_permissions (role_id, permission_id)
    SELECT r.id, p.id
    FROM inserted_roles r
    CROSS JOIN inserted_permissions p
    WHERE (r.name = 'AdminRole') OR (r.name = 'DeveloperRole' AND p.name LIKE '%.read')
    RETURNING role_id
),

-- 6. SEED USER_ROLES (Join Table)
inserted_user_roles AS (
    INSERT INTO user_roles (user_id, role_id)
    SELECT u.id, r.id
    FROM inserted_users u
    JOIN inserted_roles r ON r.organization_id = u.organization_id
    WHERE r.name = 'AdminRole'
    RETURNING user_id
),

-- 7. SEED SESSIONS (Security Table)
inserted_sessions AS (
    INSERT INTO sessions (user_id, device_name, ip_address, metadata, expires_at)
    SELECT
        id,
        'Chrome Mac / Dev Instance',
        '127.0.0.1'::inet,
        '{"agent": "seed-script"}'::jsonb,
        NOW() + INTERVAL '24 hours'
    FROM inserted_users
    RETURNING id
),

-- 8. SEED SERVICE_ACCOUNTS (Security Table)
inserted_service_accounts AS (
    INSERT INTO service_accounts (organization_id, client_id, description)
    SELECT
        id,
        'sa-client-id-00' || rn,
        'Automated CI/CD account for organization'
    FROM inserted_orgs
    RETURNING id, organization_id
)

-- 9. SEED API_KEYS (Security Table)
INSERT INTO api_keys (organization_id, service_account_id, hashed_key, expires_at)
SELECT
    organization_id,
    id,
    'mocked_argon2_or_sha256_hash_value_string_' || row_number() OVER (),
    NOW() + INTERVAL '365 days'
FROM inserted_service_accounts;

COMMIT;