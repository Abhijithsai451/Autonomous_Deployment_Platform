# Enterprise AI-Powered Autonomous Operations Platform

This platform is a high-performance, microservice-oriented platform designed for operational intelligence and workflow automation. It leverages a modern Python stack with a focus on scalability, distributed messaging, and robust identity management.

## Overview

Project is built using a modular "apps" architecture, separating concerns across identity, organization management, workflow execution, and agent runtimes. The project follows Domain-Driven Design (DDD) principles, with shared logic encapsulated in internal packages.

## Tech Stack

- **Language:** Python 3.10+
- **Frameworks:** FastAPI (API Layer), SQLAlchemy (ORM), Pydantic (Data Validation)
- **Infrastructure:** 
    - **Identity:** Keycloak
    - **Messaging:** NATS
    - **Caching:** Redis
    - **Database:** PostgreSQL
    - **Orchestration:** Docker, Kubernetes, Helm
    - **IaC:** Terraform
- **Observability:** Structured Logging, Telemetry, and Tracing.

## Project Structure

```plain text
CortexOps/
├── apps/                 # Core Microservices
│   ├── identity/         # Auth, RBAC, Keycloak integration
│   ├── organization/     # Org, Department, and Project management
│   ├── agent-runtime/    # Execution environment for agents
│   ├── gateway/          # API Gateway
│   └── workflow/         # Workflow orchestration
├── packages/             # Shared internal libraries
│   ├── auth/             # Shared authentication logic
│   ├── messaging/        # NATS publisher/subscriber wrappers
│   ├── database/         # SQLAlchemy clients and base models
│   └── tracing/          # OpenTelemetry/Tracing configuration
├── infrastructure/       # Deployment configurations
│   ├── docker/           # Dockerfiles & Compose files
│   ├── terraform/        # Cloud infrastructure as code
│   └── kubernetes/       # K8s manifests
└── scripts/              # Database migrations and utility scripts
```


## Getting Started

### Prerequisites

- **Python 3.10** (Managed via `conda` recommended)
- **Docker & Docker Compose**
- **NATS Server** (for messaging)

### Installation

1. **Clone the repository:**
```shell script
git clone <repository-url>
   cd ADD Platform
```


2. **Set up the environment:**
   This project uses `condavenv`. Ensure your environment is active:
```shell script
conda activate <your-env-name>
   pip install -r requirements.txt
```


3. **Database Initialization:**
   Run the schema scripts provided in the `scripts/` directory to initialize your PostgreSQL instance:
```shell script
psql -h localhost -U user -d cortexops -f scripts/01_identity_schema.sql
   # Repeat for organization and workflow schemas
```


### Running the Project

You can use the provided shell scripts to manage the application lifecycle:

- **Start all services:**
```shell script
./run.sh
```

- **Restart services:**
```shell script
./restart.sh
```


Alternatively, use **Docker Compose** for infrastructure:
```shell script
docker-compose -f infrastructure/docker/docker-compose.infra.yml up -d
```


## API Documentation

Once the services are running, you can access the interactive Swagger documentation:

- **Identity Service:** `http://localhost:<port>/docs`
- **Organization Service:** `http://localhost:<port>/docs`

## Testing

Run the test suite using `pytest`:
```shell script
pytest apps/identity/identity_test.py
pytest apps/organization/org_test.py
```


## Development Guidance

- **Adding new APIs:** Follow the structure in `apps/<service>/api/v1/`.
- **Shared Logic:** If code is used by more than one app, move it to the `packages/` directory.
- **Environment Variables:** Configuration is managed via `packages/config/settings.py` and service-specific `config/` folders.