-- ========================================================
-- DATABASE SETUP
-- ========================================================
CREATE DATABASE organization;
\c organization;

CREATE SCHEMA IF NOT EXISTS organization;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA organization;

-- ========================================================
-- ENUMS
-- ========================================================
CREATE TYPE organization.org_status AS ENUM ('ACTIVE', 'SUSPENDED','ARCHIVED');
CREATE TYPE organization.org_plan AS ENUM ('FREE', 'PRO','ENTERPRISE');
CREATE TYPE organization.department_type AS ENUM ('INTERNAL','EXTERNAL', 'SRE', 'SUPPORT');
CREATE TYPE organization.project_status AS ENUM ('CREATED', 'UPDATED', 'DELETED', 'ARCHIVED');
CREATE TYPE organization.department_status AS ENUM ('CREATED', 'UPDATED', 'DELETED', 'ARCHIVED');

CREATE TABLE IF NOT EXISTS organization.organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    status organization.org_status NOT NULL DEFAULT 'ACTIVE',
    plan organization.org_plan NOT NULL DEFAULT 'FREE',
    general_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    security_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    llm_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    notification_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    billing_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS organization.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organization.organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    lifecycle VARCHAR(255) NOT NULL DEFAULT 'ACTIVE',
    status organization.project_status NOT NULL DEFAULT 'CREATED',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS organization.departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organization.organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type organization.department_type NOT NULL DEFAULT 'INTERNAL',
    status organization.department_status NOT NULL DEFAULT 'CREATED',
    description TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- ========================================================
--  PERFORMANCE INDEXES
-- ========================================================

CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organization.organizations(slug);
CREATE INDEX IF NOT EXISTS idx_projects_organization_id ON organization.projects(organization_id);
CREATE INDEX IF NOT EXISTS idx_departments_organization_id ON organization.departments(organization_id);
CREATE INDEX IF NOT EXISTS idx_projects_lifecycle ON organization.projects(lifecycle);
CREATE INDEX IF NOT EXISTS idx_projects_status ON organization.projects(status);
CREATE INDEX IF NOT EXISTS idx_departments_status ON organization.departments(status);
CREATE INDEX IF NOT EXISTS idx_organizations_general_settings_gin ON organization.organizations USING gin(general_settings);
CREATE INDEX IF NOT EXISTS idx_projects_metadata_gin ON organization.projects USING gin(metadata);
CREATE INDEX IF NOT EXISTS idx_departments_metadata_gin ON organization.departments USING gin(metadata);

-- ========================================================
--  SEED DATA
-- ========================================================
BEGIN;

-- 1. Insert 15 more Organizations
INSERT INTO organization.organizations (name, slug, status, plan, general_settings, security_settings)
SELECT
    'Corp ' || i as name,
    'corp-' || i as slug,
    (ARRAY['ACTIVE', 'SUSPENDED', 'ARCHIVED'])[floor(random() * 3 + 1)]::organization.org_status,
    (ARRAY['FREE', 'PRO', 'ENTERPRISE'])[floor(random() * 3 + 1)]::organization.org_plan,
    jsonb_build_object('timezone', 'UTC', 'language', 'en'),
    jsonb_build_object('mfa_required', random() > 0.5)
FROM generate_series(1, 15) i;

-- 2. Insert 15 more Projects
-- We'll pick a random organization_id from the existing ones for each project
INSERT INTO organization.projects (organization_id, name, description, lifecycle, status, metadata)
SELECT
    (SELECT id FROM organization.organizations ORDER BY random() LIMIT 1),
    'Project ' || chr((65 + (i % 26))::int) || i,
    'Automated description for project ' || i,
    (ARRAY['ACTIVE', 'PLANNING', 'COMPLETED'])[floor(random() * 3 + 1)],
    (ARRAY['CREATED', 'UPDATED', 'ARCHIVED'])[floor(random() * 3 + 1)]::organization.project_status,
    jsonb_build_object('priority', floor(random() * 5 + 1), 'version', '1.' || i)
FROM generate_series(1, 15) i;

-- 3. Insert 15 more Departments
INSERT INTO organization.departments (organization_id, name, type, status, description, metadata)
SELECT
    (SELECT id FROM organization.organizations ORDER BY random() LIMIT 1),
    (ARRAY['Engineering', 'Marketing', 'Sales', 'HR', 'Legal', 'Product'])[floor(random() * 6 + 1)] || ' ' || i,
    (ARRAY['INTERNAL', 'EXTERNAL', 'SRE', 'SUPPORT'])[floor(random() * 4 + 1)]::organization.department_type,
    (ARRAY['CREATED', 'UPDATED'])[floor(random() * 2 + 1)]::organization.department_status,
    'Department focusing on scale and efficiency.',
    jsonb_build_object('budget_code', 'DEPT-' || (100 + i))
FROM generate_series(1, 15) i;

COMMIT;