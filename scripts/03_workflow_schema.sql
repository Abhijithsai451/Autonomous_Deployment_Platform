-- ========================================================
-- ENTITY RELATIONSHIP DIAGRAM
-- ========================================================
-- [ workflow_blueprints ] (1)
--       │
--       └── (N) [ workflow_instances ] (1)
--                       │
--                       ├── (N) [ tasks ] (1)
--                       │           │
--                       │           └── (N) [ task_dependencies ] (Self-Referencing DAG)
--                       │
--                       └── (N) [ workflow_events ]


-- ========================================================
-- DATABASE SETUP
-- ========================================================
CREATE DATABASE workflow;
\c workflow;

CREATE SCHEMA IF NOT EXISTS workflow;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA workflow;

-- ========================================================
-- ENUMS
-- ========================================================

CREATE TYPE workflow.workflow_status AS ENUM (
            'PENDING',
            'RUNNING',
            'WAITING_FOR_APPROVAL',
            'PAUSED',
            'COMPLETED',
            'FAILED',
            'CANCELLED'
        );

CREATE TYPE workflow.task_status AS ENUM (
            'PENDING',
            'READY',
            'RUNNING',
            'COMPLETED',
            'FAILED',
            'CANCELLED'
        );

CREATE TABLE IF NOT EXISTS workflow.workflow_blueprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version INT NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    definition JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_blueprint_name_version UNIQUE (name, version)
);

CREATE TABLE IF NOT EXISTS workflow.workflow_instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blueprint_id UUID NOT NULL REFERENCES workflow.workflow_blueprints(id) ON DELETE RESTRICT,
    status workflow.workflow_status NOT NULL DEFAULT 'PENDING',
    current_step VARCHAR(100),
    started_by UUID,
    temporal_workflow_id VARCHAR(255),
    temporal_run_id VARCHAR(255),
    input_data JSONB DEFAULT '{}'::jsonb,
    output_data JSONB DEFAULT '{}'::jsonb,
    error_details JSONB,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow.tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_instance_id UUID NOT NULL REFERENCES workflow.workflow_instances(id) ON DELETE CASCADE,
    task_definition_id VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    action_type VARCHAR(100) NOT NULL,
    status workflow.task_status NOT NULL DEFAULT 'PENDING',
    assigned_agent_id UUID,
    input_data JSONB DEFAULT '{}'::jsonb,
    output_data JSONB DEFAULT '{}'::jsonb,
    error_details JSONB,
    retry_count INT NOT NULL DEFAULT 0,
    max_retries INT NOT NULL DEFAULT 3,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow.task_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES workflow.tasks(id) ON DELETE CASCADE,
    depends_on_task_id UUID NOT NULL REFERENCES workflow.tasks(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_task_dependency UNIQUE (task_id, depends_on_task_id),
    CONSTRAINT chk_no_self_dependency CHECK (task_id <> depends_on_task_id)
);

CREATE TABLE IF NOT EXISTS workflow.workflow_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_instance_id UUID NOT NULL REFERENCES workflow.workflow_instances(id) ON DELETE CASCADE,
    task_id UUID REFERENCES workflow.tasks(id) ON DELETE SET NULL,
    event_type VARCHAR(100) NOT NULL, -- e.g. "WorkflowStarted", "TaskCompleted"
    payload JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_instances_blueprint ON workflow.workflow_instances(blueprint_id);
CREATE INDEX IF NOT EXISTS idx_instances_status ON workflow.workflow_instances(status);
CREATE INDEX IF NOT EXISTS idx_tasks_instance ON workflow.tasks(workflow_instance_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON workflow.tasks(status);
CREATE INDEX IF NOT EXISTS idx_events_instance ON workflow.workflow_events(workflow_instance_id);