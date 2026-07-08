    ORGANIZATION ||--|{ PROJECT : "owns"
    ORGANIZATION ||--|{ DEPARTMENT : "owns"
    
    ORGANIZATION {
        uuid id PK
        string name
        string slug
        enum status
        enum plan
        json general_settings
        json security_settings
        json llm_settings
        json notification_settings
        json billing_settings
    }

    PROJECT {
        uuid id PK
        uuid organization_id FK
        string name
        string description
        string lifecycle
        json metadata
    }

    DEPARTMENT {
        uuid id PK
        uuid organization_id FK
        string name
        enum type
        string description
        json metadata
    }