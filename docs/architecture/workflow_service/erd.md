    BLUEPRINT ||--o{ INSTANCE : "spawns"
    INSTANCE ||--o{ STEP : "executes"
    
    BLUEPRINT {
        uuid id PK
        uuid department_id
        string name
        jsonb definition
    }

    INSTANCE {
        uuid id PK
        uuid blueprint_id FK
        enum status
        jsonb input_data
        timestamp started_at
    }

    STEP {
        uuid id PK
        uuid instance_id FK
        string action_type
        enum status
        jsonb result
    }