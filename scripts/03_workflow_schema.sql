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

CREATE TYPE workflow.outbox_status AS ENUM (
            'PENDING',
            'PROCESSING',
            'PROCESSED',
            'FAILED'
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
    triggered_by VARCHAR(255),
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

CREATE TABLE IF NOT EXISTS workflow.outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    aggregate_id UUID NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status workflow.outbox_status NOT NULL DEFAULT 'PENDING',
    retry_count INT NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_instances_blueprint ON workflow.workflow_instances(blueprint_id);
CREATE INDEX IF NOT EXISTS idx_instances_status ON workflow.workflow_instances(status);
CREATE INDEX IF NOT EXISTS idx_tasks_instance ON workflow.tasks(workflow_instance_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON workflow.tasks(status);
CREATE INDEX IF NOT EXISTS idx_events_instance ON workflow.workflow_events(workflow_instance_id);
CREATE INDEX IF NOT EXISTS idx_outbox_status ON workflow.outbox_events(status);
CREATE INDEX IF NOT EXISTS idx_outbox_event_type ON workflow.outbox_events(event_type);
CREATE INDEX IF NOT EXISTS idx_outbox_aggregate ON workflow.outbox_events(aggregate_type, aggregate_id);
-- ========================================================
-- SEED DATA
-- ========================================================
BEGIN;

INSERT INTO workflow.workflow_blueprints (name, description, version, definition)
VALUES
('Document Processing', 'Extracts text and metadata from PDFs', 1, '{"steps": ["upload", "ocr", "extract", "validate"]}'::jsonb),
('User Onboarding', 'Handles new user registration and setup', 1, '{"steps": ["create_account", "verify_email", "provision_resources"]}'::jsonb),
('Cloud Provisioning', 'Spins up AWS/GCP infrastructure', 1, '{"steps": ["plan", "apply", "output"]}'::jsonb),
('Model Training', 'ML Pipeline for training classifiers', 2, '{"steps": ["data_fetch", "preprocess", "train", "eval"]}'::jsonb),
('Approval Chain', 'Standard multi-step approval workflow', 1, '{"steps": ["submit", "manager_review", "exec_review"]}'::jsonb);

INSERT INTO workflow.workflow_instances (blueprint_id, status, current_step, started_by, triggered_by, input_data)
SELECT
    (SELECT id FROM workflow.workflow_blueprints ORDER BY random() LIMIT 1),
    (ARRAY['PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'WAITING_FOR_APPROVAL'])[floor(random() * 5 + 1)]::workflow.workflow_status,
    'step_' || floor(random() * 5 + 1),
    gen_random_uuid(),
    (ARRAY['user:admin@cortex.ops', 'system:github-actions', 'api_key:service-account-ci', 'user:developer@cortex.ops'])[floor(random() * 4 + 1)],
    jsonb_build_object('request_id', 'REQ-' || i, 'priority', floor(random() * 3))
FROM generate_series(1, 20) i;

INSERT INTO workflow.tasks (workflow_instance_id, task_definition_id, name, action_type, status, input_data)
SELECT
    id as workflow_instance_id,
    'task_def_' || floor(random() * 100),
    'Task for ' || status,
    (ARRAY['HTTP', 'LAMBDA', 'GRPC', 'MANUAL'])[floor(random() * 4 + 1)],
    (ARRAY['PENDING', 'READY', 'RUNNING', 'COMPLETED'])[floor(random() * 4 + 1)]::workflow.task_status,
    jsonb_build_object('retry_allowed', true)
FROM workflow.workflow_instances, generate_series(1, 3);

INSERT INTO workflow.task_dependencies (task_id, depends_on_task_id)
SELECT
    t1.id,
    t2.id
FROM workflow.tasks t1
JOIN workflow.tasks t2 ON t1.workflow_instance_id = t2.workflow_instance_id
WHERE t1.id <> t2.id
  AND random() > 0.8
ON CONFLICT DO NOTHING;

INSERT INTO workflow.workflow_events (workflow_instance_id, task_id, event_type, payload)
SELECT
    workflow_instance_id,
    id,
    (ARRAY['TaskStarted', 'TaskCompleted', 'TaskRetried'])[floor(random() * 3 + 1)],
    jsonb_build_object('timestamp', NOW(), 'message', 'Event generated for task ' || name)
FROM workflow.tasks
WHERE random() > 0.5;

INSERT INTO workflow.outbox_events (event_type, aggregate_type, aggregate_id, payload, status, processed_at)
SELECT
    'WorkflowStarted',
    'WorkflowInstance',
    id,
    jsonb_build_object(
        'instance_id', id,
        'blueprint_id', blueprint_id,
        'status', status
    ),
    (ARRAY['PENDING', 'PROCESSED'])[floor(random() * 2 + 1)]::workflow.outbox_status,
    CASE WHEN random() > 0.5 THEN NOW() ELSE NULL END
FROM workflow.workflow_instances
WHERE random() > 0.4;

-- Seed Outbox Events for Tasks
INSERT INTO workflow.outbox_events (event_type, aggregate_type, aggregate_id, payload, status, processed_at)
SELECT
    'TaskCompleted',
    'Task',
    id,
    jsonb_build_object(
        'task_id', id,
        'instance_id', workflow_instance_id,
        'action_type', action_type,
        'status', status
    ),
    (ARRAY['PENDING', 'PROCESSED', 'FAILED'])[floor(random() * 3 + 1)]::workflow.outbox_status,
    CASE WHEN random() > 0.5 THEN NOW() ELSE NULL END
FROM workflow.tasks
WHERE status = 'COMPLETED';

COMMIT;