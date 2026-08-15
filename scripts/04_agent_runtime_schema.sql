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
    completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
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
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_status ON agent_runtime.agents(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_created_at ON agent_runtime.agents(created_at);

-- ========================================================
-- SEED DATA
-- ========================================================




