-- ========================================================
-- DATABASE SETUP
-- ========================================================
CREATE DATABASE agent_runtime;

\c agent_runtime;

CREATE SCHEMA IF NOT EXISTS agent_runtime;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ========================================================
-- ENUMS
-- ========================================================
CREATE TYPE agent_runtime.agent_status AS ENUM ('ACTIVE', 'DISABLED');
CREATE TYPE agent_runtime.run_status AS ENUM ('READY', 'PROCESSING', 'FAILED', 'FINISHED');
CREATE TYPE agent_runtime.outbox_status AS ENUM ('PENDING', 'PROCESSING', 'PUBLISHED', 'FAILED', 'DEAD_LETTER');

-- ========================================================
-- TABLES
-- ========================================================
CREATE TABLE agent_runtime.agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    status agent_runtime.agent_status NOT NULL DEFAULT 'ACTIVE',
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE agent_runtime.agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agent_runtime.agents(id) ON DELETE CASCADE,
    task_id UUID NOT NULL UNIQUE,
    workflow_instance_id UUID NOT NULL,
    status agent_runtime.run_status NOT NULL DEFAULT 'READY',
    input_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_data JSONB,
    error JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE agent_runtime.outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    aggregate_id UUID,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status agent_runtime.outbox_status NOT NULL DEFAULT 'PENDING',
    retry_count INT NOT NULL DEFAULT 0,
    error_message TEXT,
    max_retries INT NOT NULL DEFAULT 5,
    last_error TEXT DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE agent_runtime.processed_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL,
    consumer_group VARCHAR(100) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_event_consumer UNIQUE (event_id, consumer_group)
);

-- ========================================================
-- PERFORMANCE INDEXES
-- ========================================================
CREATE UNIQUE INDEX IF NOT EXISTS idx_agents_slug
    ON agent_runtime.agents(slug);

CREATE INDEX IF NOT EXISTS idx_agents_name
    ON agent_runtime.agents(name);

CREATE INDEX IF NOT EXISTS idx_agents_status
    ON agent_runtime.agents(status);

CREATE INDEX IF NOT EXISTS idx_agents_created_at
    ON agent_runtime.agents(created_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_runs_task_id
    ON agent_runtime.agent_runs(task_id);

CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_id
    ON agent_runtime.agent_runs(agent_id);

CREATE INDEX IF NOT EXISTS idx_agent_runs_workflow_instance_id
    ON agent_runtime.agent_runs(workflow_instance_id);

CREATE INDEX IF NOT EXISTS idx_agent_runs_status
    ON agent_runtime.agent_runs(status);

CREATE INDEX IF NOT EXISTS idx_outbox_pending_poller
    ON agent_runtime.outbox_events(status, created_at)
    WHERE status = 'PENDING';

CREATE INDEX IF NOT EXISTS idx_outbox_aggregate
    ON agent_runtime.outbox_events(aggregate_type, aggregate_id);

CREATE INDEX IF NOT EXISTS idx_processed_events_event_id
    ON agent_runtime.processed_events(event_id);

-- ========================================================
-- SEED DATA
-- ========================================================
BEGIN;

-- 1. SEED AGENTS
WITH inserted_agents_raw AS (
    INSERT INTO agent_runtime.agents (
        name,
        slug,
        status,
        configuration,
        created_at,
        updated_at
    )
    SELECT
        'Test Agent ' || rn,
        'test-agent-' || rn,
        CASE
            WHEN rn IN (4, 8) THEN 'DISABLED'::agent_runtime.agent_status
            ELSE 'ACTIVE'::agent_runtime.agent_status
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
    RETURNING id, name, slug, status, configuration, created_at
),
inserted_agents AS (
    SELECT
        id,
        name,
        slug,
        status,
        configuration,
        row_number() OVER (ORDER BY created_at, id) AS rn
    FROM inserted_agents_raw
),
inserted_agent_runs AS (
    INSERT INTO agent_runtime.agent_runs (
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
        CASE
            WHEN rn IN (1, 5, 9) THEN 'READY'::agent_runtime.run_status
            WHEN rn IN (2, 6, 10) THEN 'PROCESSING'::agent_runtime.run_status
            WHEN rn IN (3, 7) THEN 'FAILED'::agent_runtime.run_status
            ELSE 'FINISHED'::agent_runtime.run_status
        END,
        jsonb_build_object(
            'task_name', 'Test Task for ' || name,
            'action_type', CASE
                WHEN rn IN (1, 5, 9) THEN 'prepare'
                WHEN rn IN (2, 6, 10) THEN 'execute'
                WHEN rn IN (3, 7) THEN 'retryable_operation'
                ELSE 'summarize'
            END,
            'input_reference', gen_random_uuid(),
            'payload', jsonb_build_object(
                'source', 'seed-script',
                'agent_name', name,
                'agent_slug', slug
            )
        ),
        CASE
            WHEN rn IN (4, 8) THEN jsonb_build_object(
                'result', 'completed',
                'message', 'Test workflow completed successfully',
                'records_processed', 100,
                'confidence', 0.95
            )
            WHEN rn IN (2, 6, 10) THEN jsonb_build_object(
                'result', 'in_progress',
                'progress_percent', 50,
                'current_step', 'processing test payload'
            )
            WHEN rn IN (1, 5, 9) THEN jsonb_build_object(
                'result', 'queued',
                'message', 'Run is ready for execution'
            )
            ELSE NULL
        END,
        CASE
            WHEN rn IN (3, 7) THEN jsonb_build_object(
                'code', 'TEST_AGENT_FAILURE',
                'message', 'Mock failure generated by seed data',
                'retryable', true
            )
            ELSE NULL
        END,
        NOW() - INTERVAL '45 minutes',
        CASE
            WHEN rn IN (3, 4, 7, 8)
            THEN NOW() - INTERVAL '10 minutes'
            ELSE NULL
        END,
        NOW() - INTERVAL '45 minutes'
    FROM inserted_agents
    RETURNING id, agent_id, task_id, workflow_instance_id, status, input_data, output_data, error, created_at
),
inserted_processed_events AS (
    INSERT INTO agent_runtime.processed_events (
        event_id,
        consumer_group,
        processed_at
    )
    SELECT
        gen_random_uuid(),
        'agent-runtime-test-consumer',
        NOW()
    FROM inserted_agent_runs
    RETURNING id
)

-- 4. SEED OUTBOX EVENTS
INSERT INTO agent_runtime.outbox_events (
    event_type,
    aggregate_type,
    aggregate_id,
    payload,
    status,
    retry_count,
    error_message,
    max_retries,
    last_error,
    created_at,
    processed_at
)
SELECT
    CASE
        WHEN rn = 1 THEN 'workflow.events.task.created'
        WHEN rn = 2 THEN 'workflow.events.task.ready'
        WHEN rn = 3 THEN 'workflow.events.task.started'
        WHEN rn = 4 THEN 'workflow.events.task.completed'
        WHEN rn = 5 THEN 'workflow.events.task.failed'
        WHEN rn = 6 THEN 'workflow.events.task.retry'
        WHEN rn = 7 THEN 'workflow.events.task.cancel'
        WHEN rn = 8 THEN 'agent_runtime.agent.ready'
        WHEN rn = 9 THEN 'agent_runtime.agent.processing'
        ELSE 'agent_runtime.agent.finished'
    END,
    CASE
        WHEN rn <= 7 THEN 'TASK'
        ELSE 'AGENT_RUN'
    END,
    CASE
        WHEN rn <= 7 THEN task_id
        ELSE id
    END,
    jsonb_build_object(
        'event_id', gen_random_uuid(),
        'task_id', task_id,
        'instance_id', workflow_instance_id,
        'workflow_instance_id', workflow_instance_id,
        'agent_run_id', id,
        'agent_id', agent_id,
        'status', status,
        'action_type', CASE
            WHEN rn = 1 THEN 'create'
            WHEN rn = 2 THEN 'prepare'
            WHEN rn = 3 THEN 'start'
            WHEN rn = 4 THEN 'complete'
            WHEN rn = 5 THEN 'fail'
            WHEN rn = 6 THEN 'retry'
            WHEN rn = 7 THEN 'cancel'
            WHEN rn = 8 THEN 'agent_ready'
            WHEN rn = 9 THEN 'agent_processing'
            ELSE 'agent_finished'
        END,
        'input_data', COALESCE(input_data, '{}'::jsonb),
        'output_data', COALESCE(output_data, '{}'::jsonb),
        'error', COALESCE(error, '{}'::jsonb),
        'metadata', jsonb_build_object(
            'source', 'agent-runtime-seed-script',
            'seed_row', rn,
            'published_by', 'test-data-loader'
        )
    ),
    CASE
        WHEN rn IN (1, 2, 3, 4, 8, 9, 10) THEN 'PENDING'::agent_runtime.outbox_status
        WHEN rn = 5 THEN 'FAILED'::agent_runtime.outbox_status
        WHEN rn = 6 THEN 'PROCESSING'::agent_runtime.outbox_status
        ELSE 'PUBLISHED'::agent_runtime.outbox_status
    END,
    CASE
        WHEN rn = 5 THEN 2
        WHEN rn = 6 THEN 1
        ELSE 0
    END,
    CASE
        WHEN rn = 5 THEN 'Mock outbox publish failure for test retry handling'
        ELSE NULL
    END,
    5,
    CASE
        WHEN rn = 5 THEN 'Temporary broker unavailable during seed simulation'
        ELSE NULL
    END,
    NOW() - (rn || ' minutes')::interval,
    CASE
        WHEN rn = 7 THEN NOW() - INTERVAL '3 minutes'
        ELSE NULL
    END
FROM (
    SELECT
        ar.id,
        ar.agent_id,
        ar.task_id,
        ar.workflow_instance_id,
        ar.status,
        ar.input_data,
        ar.output_data,
        ar.error,
        row_number() OVER (ORDER BY ar.created_at, ar.id) AS rn
    FROM agent_runtime.agent_runs ar
    LIMIT 10
) seeded_runs;

COMMIT;