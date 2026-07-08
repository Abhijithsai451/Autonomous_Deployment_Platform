-- Create and connect to the workflows database
CREATE DATABASE workflows;
\c workflows;

-- Create custom enums
CREATE TYPE instance_status AS ENUM ('PENDING', 'RUNNING', 'PAUSED', 'COMPLETED', 'FAILED');
CREATE TYPE step_status AS ENUM ('PENDING', 'SUCCESS', 'FAILED');

-- Create tables
CREATE TABLE blueprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_id UUID NOT NULL, -- Logical reference to Organization Service's departments
    name VARCHAR(255) NOT NULL,
    definition JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INT NOT NULL DEFAULT 1
);

CREATE TABLE instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blueprint_id UUID NOT NULL REFERENCES blueprints(id) ON DELETE CASCADE,
    status instance_status NOT NULL DEFAULT 'PENDING',
    input_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    current_step VARCHAR(100),
    started_by UUID NOT NULL, -- Logical reference to Identity Service's users
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instance_id UUID NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
    action_type VARCHAR(100) NOT NULL,
    status step_status NOT NULL DEFAULT 'PENDING',
    result JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Indexes for rapid tracking and history updates
CREATE INDEX idx_blueprints_dept ON blueprints(department_id);
CREATE INDEX idx_instances_blueprint ON instances(blueprint_id);
CREATE INDEX idx_instances_status ON instances(status);
CREATE INDEX idx_steps_instance ON steps(instance_id);