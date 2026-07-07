# Database Schema: organization_svc

## Table: organizations
- id: UUID (PK)
- name: VARCHAR(255)
- slug: VARCHAR(100) (Unique)
- status: ENUM('ACTIVE', 'SUSPENDED', 'ARCHIVED')
- settings: JSONB (Store tenant-level config)
- created_at: TIMESTAMPTZ

## Table: departments
- id: UUID (PK)
- organization_id: UUID (FK -> organizations)
- name: VARCHAR(100)
- description: TEXT
- department_type: VARCHAR(50) (e.g., 'SRE', 'FINANCE')
- created_at: TIMESTAMPTZ

## Table: org_settings
- organization_id: UUID (FK)
- key: VARCHAR(50)
- value: JSONB
- PRIMARY KEY(organization_id, key)