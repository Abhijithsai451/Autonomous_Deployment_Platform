# Database Schema: workflow_svc

## Table: blueprints
- id: UUID (PK)
- department_id: UUID
- name: VARCHAR(255)
- definition: JSONB
- version: INT

## Table: instances
- id: UUID (PK)
- blueprint_id: UUID (FK)
- status: ENUM('PENDING', 'RUNNING', 'PAUSED', 'COMPLETED', 'FAILED')
- input_data: JSONB
- current_step: VARCHAR(100)
- started_by: UUID
- started_at: TIMESTAMPTZ

## Table: steps
- id: UUID (PK)
- instance_id: UUID (FK)
- action_type: VARCHAR(100)
- status: ENUM('PENDING', 'SUCCESS', 'FAILED')
- result: JSONB