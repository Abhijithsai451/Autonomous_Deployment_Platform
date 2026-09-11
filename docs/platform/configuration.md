# Autonomous DevOps Platform Configuration Strategy

## 1. Configuration Philosophy
ADO Platform strictly enforces a centralized, typed configuration model powered by Pydantic and `packages/config`. Individual microservices are prohibited from implementing custom environment variable parsers, fallback mechanisms, or local settings files. 

The configuration layer enforces a **fail-fast** principle: any missing required variable, malformed URI, invalid port, or unknown environment immediately halts application startup with explicit error reporting.

---

## 2. Environment Hierarchy & Precedence

### Supported Environments (`CORTEXOPS_ENV`)
* **`local`**: Default mode for local development. Loads defaults and optional `.env` files.
* **`dev`**: Integrated development environment running in containerized/Kubernetes clusters.
* **`staging`**: Staging environment mirroring production configurations with isolated databases.
* **`prod`**: Production environment enforcing strict secret checks, disabled debug modes, and production telemetry.

### Variable Precedence Ordering (Highest to Lowest)
1. **Kubernetes Secrets / Runtime Secret Injection**
2. **Environment Variables / Kubernetes ConfigMaps**
3. **Local `.env` File** (Permitted in `local` environment only)
4. **Base Application Defaults** (Defined in `packages/config`)

---

## 3. Secret Classification & Security Rules

Secrets across CortexOps are categorized into five distinct tiers:

| Classification | Description | Examples |
| :--- | :--- | :--- |
| **`PUBLIC`** | Non-sensitive runtime variables and metadata. | `APP_NAME`, `LOG_LEVEL`, `HTTP_PORT` |
| **`INTERNAL`** | Cluster-internal network routes and identifiers. | `POSTGRES_HOST`, `NATS_STREAM_NAME` |
| **`SENSITIVE`** | Non-critical operational parameters and identifiers. | `POSTGRES_USER`, `DB_NAME` |
| **`SECRET`** | Sensitive authentication and system access vectors. | `POSTGRES_PASSWORD`, `NATS_CREDENTIALS` |
| **`HIGHLY_SENSITIVE`** | High-value API keys and cryptographic credentials. | `OPENAI_API_KEY`, `KEYCLOAK_CLIENT_SECRET` |

### Security Enforcement Contract
* **No Logging**: Secrets must never be output via `structlog` or standard print streams.
* **No Telemetry Leakage**: Telemetry processors automatically scrub trace attributes and spans for classified fields.
* **No Event Pollution**: NATS event envelopes and JSON payloads are strictly validated to prevent embedded credentials.
* **Redacted Representations**: Printing or serializing Pydantic configuration objects automatically redacts fields classified as `SECRET` or `HIGHLY_SENSITIVE`.

---

## 4. Standardized Service Configuration Blueprint

Every microservice extends the unified `ServiceConfiguration` base class provided by `packages/config`:

```text
ServiceConfiguration
├── application      # Service identity, environment, host, port, debug mode
├── database         # PostgreSQL connections, pool sizes, timeouts, SSL
├── messaging        # NATS JetStream URLs, connection timeouts, retry policy
├── redis            # Caching, lock providers, connection parameters
├── telemetry        # OTLP collector endpoints, sampling rates, trace flags
└── security         # Keycloak issuer URIs, token parameters, client secrets