# Database Schema: workflow

## Table: workflow_blueprints
- temporal_workflow_id: UUID (PK)
- temporal_run_id: UUID
- status: VARCHAR(255)
- current_task: VARCHAR(255)
- inputs: JSONB
- outputs: JSONB

## Table: instances
- id: UUID (PK)
- blueprint_id: UUID (FK)
- status: ENUM('PENDING', 'RUNNING', 'PAUSED', 'COMPLETED', 'FAILED')
- input_data: JSONB
- current_step: VARCHAR(100)
- started_by: UUID (User/Agent ID)