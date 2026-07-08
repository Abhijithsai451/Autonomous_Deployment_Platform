# Database Schema: organization

## Table: organizations
- id: UUID (PK)
- name: VARCHAR(255)
- slug: VARCHAR(100) (Unique)
- status: ENUM('ACTIVE', 'SUSPENDED', 'ARCHIVED')
- plan: ENUM('FREE', 'PRO', 'ENTERPRISE')
- general_settings: JSON
- security_settings: JSON
- llm_settings: JSON
- notification_settings: JSON
- billing_settings: JSON
- created_at: TIMESTAMPTZ
- updated_at: TIMESTAMPTZ

## Table: projects
- id: UUID (PK)
- organization_id: UUID (FK)
- name: VARCHAR
- description: TEXT
- lifecycle: VARCHAR
- metadata: JSONB
- created_at: TIMESTAMPTZ
- updated_at: TIMESTAMPTZ

## Table: departments
- id: UUID (PK)
- organization_id: UUID (FK)
- name: VARCHAR(100)
- type: ENUM('SRE', 'SUPPORT', ...)
- description: TEXT
- metadata: JSONB
- created_at: TIMESTAMPTZ
- updated_at: TIMESTAMPTZ