    ORGANIZATION ||--|{ DEPARTMENT : contains
    ORGANIZATION ||--|{ SUBSCRIPTION_PLAN : has
    DEPARTMENT ||--o{ AGENT_GROUP : owns
    
    ORGANIZATION {
        uuid id PK
        string name
        string slug
        string status
        jsonb settings
    }

    DEPARTMENT {
        uuid id PK
        uuid organization_id FK
        string name
        string description
        string department_type
    }