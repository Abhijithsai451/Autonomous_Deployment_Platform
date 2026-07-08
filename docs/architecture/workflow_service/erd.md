    BLUEPRINT ||--|{ INSTANCE : "spawns"
    INSTANCE ||--|{ TASK : "contains"
    INSTANCE ||--|{ EVENT : "logs"
    TASK ||--|{ TASK_DEPENDENCY : "has"

    BLUEPRINT {
        uuid temporal_workflow_id PK
        uuid temporal_run_id
        string status
        string current_task
        json inputs
        json outputs
    }

    INSTANCE {
        uuid id PK
        uuid blueprint_id FK
        enum status
        jsonb input_data
        string current_step
        uuid started_by
    }

    TASK {
        uuid id PK
        uuid instance_id FK
        string action_type
        enum status
    }