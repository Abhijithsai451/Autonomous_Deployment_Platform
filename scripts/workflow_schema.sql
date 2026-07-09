-- Create and connect to the workflows database
CREATE DATABASE workflows;
\c workflows;

-- Create custom enums
CREATE TYPE instance_status AS ENUM ('PENDING', 'RUNNING', 'PAUSED', 'COMPLETED', 'FAILED');

-- Create tables
CREATE TABLE workflow_blueprints (
    temporal_workflow_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    temporal_run_id UUID,
    status VARCHAR(255) NOT NULL,
    current_task VARCHAR(255),
    inputs JSONB NOT NULL DEFAULT '{}'::jsonb,
    outputs JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blueprint_id UUID NOT NULL REFERENCES workflow_blueprints(temporal_workflow_id) ON DELETE CASCADE,
    status instance_status NOT NULL DEFAULT 'PENDING',
    input_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    current_step VARCHAR(100),
    started_by UUID NOT NULL -- Logical reference to Identity Service's users/agents
);

-- Indexes for high-throughput orchestration tracking
CREATE INDEX idx_instances_blueprint ON instances(blueprint_id);
CREATE INDEX idx_instances_status ON instances(status);