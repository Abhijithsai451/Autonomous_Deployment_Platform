    ORGANIZATION ||--o{ USER : "has"
    ORGANIZATION ||--o{ SERVICE_ACCOUNT : "has"
    ORGANIZATION ||--o{ API_KEY : "has"
    ORGANIZATION ||--o{ ROLE : "has"
    
    USER ||--o{ SESSION : "has"
    USER ||--o{ USER_ROLES : "assigned"
    
    SERVICE_ACCOUNT ||--o{ USER_ROLES : "assigned"
    
    ROLE ||--o{ ROLE_PERMISSIONS : "contains"
    PERMISSION ||--o{ ROLE_PERMISSIONS : "granted_by"
    
    ROLE ||--o{ USER_ROLES : "assigned_to"

    ORGANIZATION {
        uuid id PK
        string name
        string slug
        enum status
        enum plan
        jsonb settings
    }

    USER {
        uuid id PK
        uuid organization_id FK
        uuid keycloak_user_id
        string email
        string display_name
        enum status
    }

    ROLE {
        uuid id PK
        uuid organization_id FK
        string name
        boolean system_role
    }

    PERMISSION {
        uuid id PK
        string name
        string resource
        string action
    }

    SERVICE_ACCOUNT {
        uuid id PK
        uuid organization_id FK
        string client_id
        string description
    }

    API_KEY {
        uuid id PK
        uuid organization_id FK
        uuid service_account_id FK
        string hashed_key
    }