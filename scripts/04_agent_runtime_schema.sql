-- ========================================================
-- DATABASE SETUP
-- ========================================================
CREATE DATABASE agent_runtime;

\c agent_runtime;

CREATE SCHEMA IF NOT EXISTS agent_runtime;

-- ========================================================
-- ENUMS
-- ========================================================
CREATE TYPE agent_runtime.agent_type AS ENUM ('ACTIVE', 'DISABLED');
CREATE TYPE agent_runtime.agent_status AS ENUM ('READY', 'PROCESSING', 'FAILED', 'FINISHED');


-- ========================================================
-- TABLES
-- ========================================================
CREATE TABLE agent_runtime.agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) NOT NULL,
    type agent_runtime.agent_type NOT NULL DEFAULT 'ACTIVE',
    status agent_runtime.agent_status NOT NULL DEFAULT 'READY',
    configuration JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE agent_runtime.agent_run (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agent_runtime.agents(id) ON DELETE CASCADE,
    task_id UUID NOT NULL,
    workflow_instance_id UUID NOT NULL,
    status agent_runtime.agent_status NOT NULL,
    input_data JSONB,
    output_data JSONB,
    error JSONB,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE agent_runtime.processed_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL,
    consumer_group JSONB NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ========================================================
-- PERFORMANCE INDEXES
-- ========================================================

CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_id ON agent_runtime.agents(name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_task_id ON agent_runtime.agent_run(task_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_workflow_instance_id ON agent_runtime.agent_run(workflow_instance_id);
CREATE INDEX IF NOT EXISTS idx_agent_status ON agent_runtime.agents(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_created_at ON agent_runtime.agents(created_at);

-- ========================================================
-- SEED DATA
-- ========================================================
BEGIN;

-- 1. SEED AGENTS
WITH inserted_agents_raw AS (
    INSERT INTO agent_runtime.agents (
        name,
        type,
        status,
        configuration,
        created_at,
        updated_at
    )
    SELECT
        'Test Agent ' || rn,
        CASE
            WHEN rn IN (4, 8) THEN 'DISABLED'::agent_runtime.agent_type
            ELSE 'ACTIVE'::agent_runtime.agent_type
        END,
        CASE
            WHEN rn IN (1, 5, 9) THEN 'READY'::agent_runtime.agent_status
            WHEN rn IN (2, 6, 10) THEN 'PROCESSING'::agent_runtime.agent_status
            WHEN rn IN (3, 7) THEN 'FAILED'::agent_runtime.agent_status
            ELSE 'FINISHED'::agent_runtime.agent_status
        END,
        jsonb_build_object(
            'model', 'test-model-' || rn,
            'temperature', round((0.1 + (rn * 0.05))::numeric, 2),
            'max_tokens', 1024 + (rn * 128),
            'tools', jsonb_build_array(
                'task_reader',
                'event_processor',
                'json_transformer'
            ),
            'runtime', jsonb_build_object(
                'timeout_seconds', 120 + (rn * 30),
                'retry_count', rn % 4,
                'worker_pool', 'agent-runtime-test-pool'
            ),
            'metadata', jsonb_build_object(
                'seed_row', rn,
                'environment', 'test'
            )
        ),
        NOW() - (rn || ' hours')::interval,
        NOW() - ((rn * 30) || ' minutes')::interval
    FROM generate_series(1, 10) AS rn
    RETURNING id, name, type, status
),

-- 2. SEED AGENT RUNS
inserted_agent_runs AS (
    INSERT INTO agent_runtime.agent_run (
        agent_id,
        task_id,
        workflow_instance_id,
        status,
        input_data,
        output_data,
        error,
        started_at,
        completed_at,
        created_at
    )
    SELECT
        id,
        gen_random_uuid(),
        gen_random_uuid(),
        status,
        jsonb_build_object(
            'task_name', 'Test Task for ' || name,
            'action_type', CASE
                WHEN status = 'READY'::agent_runtime.agent_status THEN 'prepare'
                WHEN status = 'PROCESSING'::agent_runtime.agent_status THEN 'execute'
                WHEN status = 'FAILED'::agent_runtime.agent_status THEN 'retryable_operation'
                ELSE 'summarize'
            END,
            'input_reference', gen_random_uuid(),
            'payload', jsonb_build_object(
                'source', 'seed-script',
                'agent_name', name,
                'agent_type', type
            )
        ),
        CASE
            WHEN status = 'FINISHED'::agent_runtime.agent_status THEN jsonb_build_object(
                'result', 'completed',
                'message', 'Test workflow completed successfully',
                'records_processed', 100,
                'confidence', 0.95
            )
            WHEN status = 'PROCESSING'::agent_runtime.agent_status THEN jsonb_build_object(
                'result', 'in_progress',
                'progress_percent', 50,
                'current_step', 'processing test payload'
            )
            WHEN status = 'READY'::agent_runtime.agent_status THEN jsonb_build_object(
                'result', 'queued',
                'message', 'Run is ready for execution'
            )
            ELSE NULL
        END,
        CASE
            WHEN status = 'FAILED'::agent_runtime.agent_status THEN jsonb_build_object(
                'code', 'TEST_AGENT_FAILURE',
                'message', 'Mock failure generated by seed data',
                'retryable', true
            )
            ELSE NULL
        END,
        NOW() - INTERVAL '45 minutes',
        CASE
            WHEN status IN (
                'FINISHED'::agent_runtime.agent_status,
                'FAILED'::agent_runtime.agent_status
            )
            THEN NOW() - INTERVAL '10 minutes'
            ELSE NULL
        END,
        NOW() - INTERVAL '45 minutes'
    FROM inserted_agents_raw
    RETURNING id, agent_id, task_id, workflow_instance_id, status
)

-- 3. SEED PROCESSED EVENTS
INSERT INTO agent_runtime.processed_events (
    event_id,
    consumer_group,
    processed_at
)
SELECT
    gen_random_uuid(),
    jsonb_build_object(
        'name', 'agent-runtime-test-consumer',
        'version', 'v1',
        'source_run_id', id,
        'agent_id', agent_id,
        'task_id', task_id,
        'workflow_instance_id', workflow_instance_id,
        'status', status
    ),
    NOW()
FROM inserted_agent_runs;

COMMIT;