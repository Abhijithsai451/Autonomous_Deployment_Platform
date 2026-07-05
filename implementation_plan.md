# CortexOps — Implementation Plan

**What**, **How**, and **Acceptance Criteria (AC)**.

---

# EPIC 0 — Project Governance

### CORTEX-001: Write Project Charter
- **What:** One-page charter: vision, scope, non-goals, success criteria.
- **How:** Create `docs/charter.md`. Define measurable success criteria (e.g., "an agent can resolve a support ticket end-to-end with human approval in < 5 min").
- **AC:** Charter merged to `main`; reviewed by all maintainers.

### CORTEX-002: ADR Template & Log
- **What:** Architecture Decision Record process.
- **How:** Create `docs/adr/0000-template.md` (Context / Decision / Consequences / Status). Write ADR-0001 ("Use Temporal for durable workflows") and ADR-0002 ("Use Dishka for DI") as the first real records.
- **AC:** Template + 2 ADRs merged; ADR index in `docs/adr/README.md`.

### CORTEX-003: Coding Standards & Contribution Guide
- **What:** `CONTRIBUTING.md` + coding standards.
- **How:** Document: Python 3.10+, type hints mandatory, Ruff config, mypy strict on `app/core`, commit convention (Conventional Commits), PR template in `.github/PULL_REQUEST_TEMPLATE.md`.
- **AC:** Docs merged; PR template renders on GitHub.

### CORTEX-004: Branching & Release Policy
- **What:** Trunk-based development + SemVer.
- **How:** `main` protected, short-lived feature branches, squash merges. Releases tagged `vX.Y.Z`, changelog generated via `git-cliff` or Release Drafter.
- **AC:** Branch protection enabled; release workflow documented.

### CORTEX-005: Issue Labels & Milestones
- **What:** Label taxonomy mapped to epics.
- **How:** Labels: `phase:0..15`, `type:feature|bug|chore|adr`, `prio:p0..p3`. Milestones M1–M7 created matching the master plan.
- **AC:** Labels + milestones exist; this plan's tickets imported.

---

# EPIC 1 — Architecture

### CORTEX-101: Domain Context Map
- **What:** Bounded contexts: Identity, Workflow, Agents, Memory, Tool Gateway, Approval, Audit, Notifications.
- **How:** Create `docs/architecture/context-map.md` with a Mermaid diagram. For each domain define: owned entities, published events, consumed events, exposed APIs. This map dictates the `app/modules/<domain>/` package layout.
- **AC:** All 8 domains documented; each has an events + API contract table.

### CORTEX-102: Sequence Diagrams for Golden Paths
- **What:** Sequence diagrams for the 3 core flows.
- **How:** Mermaid diagrams for: (1) "User request → Planner → Tasks → Agent execution → Result", (2) "Agent requests tool call requiring approval → human approves → resume", (3) "Workflow failure → compensation → notification".
- **AC:** 3 diagrams merged in `docs/architecture/sequences/`.

### CORTEX-103: Component & Deployment Diagrams
- **What:** C4 level 2/3 diagrams.
- **How:** Component diagram: FastAPI API, Temporal workers, NATS, agent runtime, Postgres/Redis/Qdrant, Keycloak, Vault, LiteLLM/Ollama. Deployment diagram: Kubernetes namespaces (`cortex-core`, `cortex-agents`, `cortex-data`, `cortex-observability`).
- **AC:** Diagrams merged; reviewed against Phase 12 namespace plan.

### CORTEX-104: Data Flow & Threat Model
- **What:** STRIDE threat model.
- **How:** Enumerate trust boundaries (user→API, API→LLM, agent→tools). Document mitigations: OIDC at edge, Vault for secrets, approval gates for destructive tools, prompt-injection defenses at the Tool Gateway.
- **AC:** Threat model doc with ≥ 10 identified threats + mitigations, each mapped to a Phase 13 ticket.

---

# EPIC 2 — Developer Platform

### CORTEX-201: Repository Layout & Package Management
- **What:** Formalize monorepo layout; migrate off bare `requirements.txt`.
- **How:** Adopt `uv` with `pyproject.toml` at repo root. Layout:
  ```
  app/
    core/        # config, db, DI providers, security
    api/         # routers (per domain)
    modules/     # domain packages: models, repositories, services, schemas
    events/      # NATS publishers/consumers
    workflows/   # Temporal workflows + activities
    agents/      # LangGraph runtime (Phase 6)
  tests/
  deploy/        # docker-compose, helm
  docs/
  ```
  Pin deps: fastapi, sqlalchemy[asyncio], asyncpg, dishka, alembic, pydantic-settings, temporalio, nats-py, redis, qdrant-client.
- **AC:** `uv sync` produces a working env; `python -m app.main` starts.

### CORTEX-202: Lint / Type / Test Tooling
- **What:** Ruff, mypy, pytest, pre-commit.
- **How:** Configure in `pyproject.toml`: Ruff (lint+format, `select = ["E","F","I","UP","B"]`), mypy (strict for `app/core`, gradual elsewhere), pytest with `pytest-asyncio` and `anyio` mode. `.pre-commit-config.yaml` runs ruff + mypy + trailing whitespace.
- **AC:** `pre-commit run --all-files` passes; CI job (GitHub Actions) enforces it on PRs.

### CORTEX-203: Docker Compose Local Platform
- **What:** One-command local stack.
- **How:** `deploy/compose/docker-compose.yaml` with: PostgreSQL 16, Redis 7, NATS (JetStream enabled), Temporal (auto-setup image + UI), Qdrant, MinIO, Keycloak (dev realm import), Vault (dev mode), Ollama. Healthchecks on every service. Add `Makefile` targets: `make up`, `make down`, `make logs`, `make db-shell`.
- **AC:** `make up` from a clean clone brings all services healthy in < 3 min; app connects to all of them.

### CORTEX-204: Seed & Bootstrap Scripts
- **What:** Deterministic local bootstrap.
- **How:** `scripts/bootstrap.py`: create Keycloak realm/clients/test users, Vault KV mounts + dev secrets, NATS streams, Qdrant collections, MinIO buckets. Idempotent (safe to re-run).
- **AC:** Running bootstrap twice produces no errors; login with test user works.

---

# EPIC 3 — Core Backend

### CORTEX-301: FastAPI Application Factory + Dishka Wiring
- **What:** Production-grade app bootstrap.
- **How:** In `app/main.py`: app factory pattern, lifespan context manager (init DB engine, NATS, Temporal client; dispose on shutdown). Integrate `dishka.integrations.fastapi.setup_dishka`. Providers in `app/core/providers.py`: `AsyncEngine` (APP scope), `AsyncSession` (REQUEST scope), repositories/services (REQUEST scope).
- **AC:** `/healthz` (liveness) and `/readyz` (checks DB + NATS) endpoints return 200; DI resolves a repository in a route.

### CORTEX-302: Typed Config Management
- **What:** 12-factor config.
- **How:** `app/core/config.py` with `pydantic-settings`: nested settings classes (`DatabaseSettings`, `NatsSettings`, `TemporalSettings`, `AuthSettings`, `LLMSettings`), loaded from env with `CORTEX_` prefix. Provide config via Dishka APP-scope provider. `.env.example` committed.
- **AC:** App fails fast with a clear error on missing required config; no `os.environ` calls outside config module.

### CORTEX-303: Fix & Harden SQLAlchemy Models
- **What:** Correct existing model bugs and add base conventions.
- **How:** In `app/modules/platform/models.py`:
  - Fix invalid `datetime.timezone.utcnow` defaults → use `datetime.now(timezone.utc)` via a lambda, or better `server_default=func.now()` with `DateTime(timezone=True)`.
  - Use `sqlalchemy.Uuid` (or `postgresql.UUID(as_uuid=True)`) explicitly for UUID PKs.
  - Make `TaskModel.depends_on` a self-referential `ForeignKey("tasks.id")`.
  - Store `StatusEnum` as a native PG enum or `String` with a check constraint (decide via mini-ADR).
  - Add indexes: `tasks.workflow_id`, `agent_steps.task_id`, `workflows.status`.
  - Extract shared `TimestampMixin` into `app/core/models.py`.
- **AC:** `Base.metadata.create_all` succeeds on Postgres; mypy passes; unit test creates a workflow→task→step graph.

### CORTEX-304: Alembic Migrations
- **What:** Migration pipeline.
- **How:** `alembic init` with async template; wire `target_metadata = Base.metadata`; env reads DSN from settings. Generate initial migration. Add `make migrate` / `make makemigration m="..."`. CI check: autogenerate produces empty diff (models and migrations in sync).
- **AC:** Fresh DB migrates from zero; CI drift check green.

### CORTEX-305: Repository & Service Layers
- **What:** Complete the repository pattern started in `repositories.py`.
- **How:** Generic `BaseRepository[T]` (get, list with pagination, add, delete) + concrete `WorkflowRepository`, `TaskRepository`, `AgentStepRepository` with domain queries (`get_with_tasks`, `list_by_status`). Services own transactions (unit-of-work: one session per request, commit in service). No session access from routers.
- **AC:** Repos covered by integration tests against Postgres (testcontainers); services enforce status transitions (e.g., cannot go COMPLETED→RUNNING).

### CORTEX-306: Authentication (OIDC via Keycloak)
- **What:** JWT validation middleware.
- **How:** FastAPI dependency that validates Bearer tokens against Keycloak JWKS (cache keys, verify `iss`, `aud`, `exp`). Map token → `CurrentUser` model (sub, email, roles). Provide `CurrentUser` through Dishka request scope.
- **AC:** Protected route returns 401 without token, 200 with valid Keycloak token; JWKS refreshed on key rotation.

### CORTEX-307: Authorization (RBAC)
- **What:** Role/permission checks.
- **How:** Roles from Keycloak realm roles (`admin`, `operator`, `approver`, `viewer`). Decorator/dependency `require_permission("workflow:create")` with a static role→permission map in `app/core/authz.py`. Enforce object-level checks in services (e.g., only creator or admin can cancel a workflow).
- **AC:** Matrix test: each role × each endpoint returns expected 200/403.

### CORTEX-308: Audit Logging
- **What:** Immutable audit trail.
- **How:** `AuditLogModel` (id, actor, action, resource_type, resource_id, payload JSON, ip, created_at; no updates/deletes allowed). Middleware records all mutating requests; services record domain actions (approval granted, workflow cancelled). Also publish `audit.recorded` event to NATS (Phase 4).
- **AC:** Every POST/PUT/DELETE produces exactly one audit row; audit rows are append-only (DB-level: revoke UPDATE/DELETE).

### CORTEX-309: REST API v1
- **What:** Public API for workflow domain.
- **How:** `app/api/v1/`: `POST /workflows`, `GET /workflows`, `GET /workflows/{id}` (with tasks), `POST /workflows/{id}/cancel`, `GET /tasks/{id}/steps`. Pydantic request/response schemas in `modules/platform/schemas.py` (never expose ORM models). Cursor pagination, RFC 7807 `problem+json` errors, global exception handlers.
- **AC:** OpenAPI docs complete with examples; contract tests via `schemathesis` pass.

### CORTEX-310: WebSocket Support
- **What:** Live workflow/agent updates.
- **How:** `GET /ws/workflows/{id}`: authenticate via token query param or first message; subscribe to NATS subject `workflow.{id}.>` and forward events as JSON. Heartbeat ping every 30s; clean unsubscribe on disconnect.
- **AC:** Two browser clients receive the same task-status event < 500ms after publish.

---

# EPIC 4 — Event Platform

### CORTEX-401: Event Schema & Envelope
- **What:** Versioned event contract.
- **How:** Pydantic `EventEnvelope`: `event_id (uuid)`, `event_type` (e.g., `workflow.task.completed`), `version`, `occurred_at`, `correlation_id`, `causation_id`, `actor`, `payload`. Registry module maps event_type → payload schema. Document naming convention `domain.entity.action`.
- **AC:** Publishing an unregistered event type raises at dev time; schema docs autogenerated.

### CORTEX-402: NATS JetStream Publisher
- **What:** Reliable publisher.
- **How:** `app/events/publisher.py`: JetStream publish with `Nats-Msg-Id = event_id` (dedup), stream config as code (`CORTEX` stream, subjects `cortex.>`, retention limits). Outbox pattern: write event to `outbox` table in the same DB transaction as the domain change; background relay publishes and marks sent.
- **AC:** Killing the app between DB commit and publish loses no events (verified by test).

### CORTEX-403: NATS Consumers Framework
- **What:** Declarative consumer runtime.
- **How:** Decorator-based registration: `@consumer("cortex.workflow.>", durable="audit-writer")`. Runner starts pull consumers with explicit ack, per-consumer concurrency, exponential backoff via `nak(delay)`.
- **AC:** Sample consumer processes 1k events with zero loss under app restart.

### CORTEX-404: Dead-Letter Handling
- **What:** DLQ for poison messages.
- **How:** After `max_deliver` (5), messages route to `cortex.dlq.<original-subject>` via JetStream advisory listener. DLQ browser endpoint `GET /admin/dlq` + `POST /admin/dlq/{id}/replay`.
- **AC:** A consumer that always throws lands the message in DLQ after 5 tries; replay works.

### CORTEX-405: Idempotency
- **What:** Exactly-once side effects.
- **How:** `processed_events` table keyed `(consumer_name, event_id)`; consumers check-insert within their DB transaction. Helper decorator `@idempotent`.
- **AC:** Redelivering the same event 10× yields exactly one side effect.

### CORTEX-406: Event Replay
- **What:** Rebuild/repair via replay.
- **How:** Admin CLI `python -m app.events.replay --subject cortex.workflow.> --from 2026-01-01 --consumer audit-writer` using JetStream `DeliverByStartTime` on an ephemeral consumer.
- **AC:** Replaying a day of events repopulates a wiped read model correctly (idempotency prevents duplicates).

---

# EPIC 5 — Workflow Engine (Temporal)

### CORTEX-501: Temporal Client & Worker Bootstrap
- **What:** Temporal SDK integration.
- **How:** `app/workflows/worker.py` entrypoint: connect via `TemporalSettings`, task queue `cortex-main`, register workflows/activities. Dedicated process (own Compose service / K8s Deployment). Pydantic data converter for payloads.
- **AC:** `make worker` starts a worker visible in Temporal UI; sample workflow completes.

### CORTEX-502: Master Workflow Definition
- **What:** `WorkflowOrchestrator` — the durable spine.
- **How:** Workflow input: `workflow_id` (DB UUID). Steps: activity `load_plan` → for each task (respecting `depends_on` DAG) run activity `execute_agent_task` → activity `persist_result` → publish events. DB status updates happen only in activities (never in workflow code). Use `workflow.execute_activity` with typed params.
- **AC:** Creating a workflow via REST starts a Temporal execution; DB `temporal_workflow_id` is set; statuses progress PENDING→RUNNING→COMPLETED.

### CORTEX-503: Retry & Timeout Policies
- **What:** Standardized resilience.
- **How:** Policy presets in `app/workflows/policies.py`: `FAST_IO` (3 retries, 1s backoff), `LLM_CALL` (5 retries, 10s→5m backoff, non-retryable on 4xx), `HUMAN_SCALE` (long start-to-close). Every activity must use a preset (lint rule / code review checklist).
- **AC:** Simulated flaky activity (fails 2×) completes without workflow failure.

### CORTEX-504: Compensation (Saga)
- **What:** Undo on partial failure.
- **How:** Compensation stack pattern: each completed step pushes an `undo` activity; on unrecoverable failure, pop and execute in reverse. First real use: "provision resource" demo saga. Mark workflow FAILED with failure reason persisted.
- **AC:** Injected failure at step 3 of 4 triggers undo of steps 1–2; audit trail shows compensation.

### CORTEX-505: Human Approval via Signals
- **What:** Human-in-the-loop gate.
- **How:** Workflow calls `request_approval` activity (creates `ApprovalRequest` row + notification event), then `await workflow.wait_condition(lambda: self.decision is not None, timeout=48h)`. REST `POST /approvals/{id}/decision` signals the workflow (`approve`/`reject` + comment). Timeout → auto-reject + notify.
- **AC:** E2E test: workflow pauses (status PAUSED), API approval resumes it; rejection triggers compensation.

### CORTEX-506: Long-Running Workflow Hygiene
- **What:** Support week+ workflows.
- **How:** Use `continue_as_new` after N events; queries (`workflow.query`) expose live progress for the UI; heartbeats on long activities with cancellation checks.
- **AC:** Workflow with 10k iterations doesn't blow history limits; progress query returns current step.

---

# EPIC 6 — Agent Framework (LangGraph)

### CORTEX-601: LLM Gateway (LiteLLM + Ollama)
- **What:** Single LLM access point.
- **How:** LiteLLM proxy in Compose routing model aliases (`planner-model`, `worker-model`) to Ollama locally / hosted models in prod. `app/agents/llm.py` client: retries, timeout, cost tracking hooks, model selection per agent role from config.
- **AC:** Swapping `worker-model` backend requires zero code change; token usage logged per call.

### CORTEX-602: Agent State & Graph Skeleton
- **What:** Generic LangGraph runtime.
- **How:** `AgentState` (TypedDict): messages, task, plan, tool_results, reflection, iteration, budget. Graph nodes: `planner → tool_selector → executor → validator → reflector` with conditional edges (validator pass → END; fail → reflector → planner; budget exceeded → END with failure). Compile with checkpointer (CORTEX-605).
- **AC:** Graph runs a toy task ("summarize this text using the search tool") end-to-end with trace of each node.

### CORTEX-603: Planner Node
- **What:** Structured task decomposition.
- **How:** Prompt template + structured output (Pydantic `Plan`: list of steps with tool hints & success criteria). Validate LLM output against schema; one repair-retry on parse failure.
- **AC:** 20-case golden test set: planner returns valid `Plan` schema ≥ 95% of runs.

### CORTEX-604: Tool Selection & Execution Nodes
- **What:** Safe tool invocation.
- **How:** Tools registered via Tool Gateway (Phase 9) with JSON-schema args. Selector uses LLM function-calling; executor validates args against schema, enforces per-tool policy (allowed roles, approval-required flag), captures result/error into state. Destructive tools raise `ApprovalRequired` → bubbles to Temporal (CORTEX-505).
- **AC:** Unknown tool or bad args never reaches execution; approval-flagged tool pauses the run.

### CORTEX-605: Checkpointing & Failure Recovery
- **What:** Resumable agents.
- **How:** LangGraph Postgres checkpointer (thread_id = `agent_step_id`). On worker crash/restart, Temporal activity retry resumes from last checkpoint instead of restarting the graph.
- **AC:** Kill the worker mid-run; retry resumes at the interrupted node (verified via node-execution log).

### CORTEX-606: Reflection & Validation Nodes
- **What:** Self-correction loop.
- **How:** Validator: LLM-as-judge against the plan's success criteria + deterministic checks where possible. Reflector: summarizes failure into a correction hint appended to state. Hard cap: `max_iterations=3`.
- **AC:** Injected wrong tool result triggers exactly one reflection loop that fixes it; cap prevents infinite loops.

### CORTEX-607: Prompt Template Management
- **What:** Versioned prompts.
- **How:** `app/agents/prompts/` as Jinja2 files with YAML frontmatter (version, model, description). Loader renders with strict undefined. Prompt version recorded in `agent_steps.token_metrics` for traceability.
- **AC:** Changing a prompt file requires no code change; every AgentStep row records prompt versions used.

### CORTEX-608: Token Accounting & Budgets
- **What:** Cost control.
- **How:** Per-call usage from LiteLLM → accumulate into `AgentStepModel.token_metrics` (prompt/completion tokens, cost USD, model). Budget middleware: per-task and per-workflow token ceilings from config; exceeding → graceful stop with `BUDGET_EXCEEDED` status.
- **AC:** Workflow with $0.01 budget stops early and reports spend accurately (±1 call).

### CORTEX-609: Streaming
- **What:** Live token/node streaming.
- **How:** LangGraph `astream_events` → publish to NATS `agent.{step_id}.stream` → WebSocket (CORTEX-310) fans out to UI.
- **AC:** UI-connected client sees tokens appear incrementally during generation.

---

# EPIC 7 — Enterprise Departments
*(Each department = sub-epic. Pattern per department: define tools → system prompt → golden test cases → wire into planner routing.)*

### CORTEX-701: Planner Department — Request Decomposition
- **How:** Top-level agent that turns a natural-language request into `TaskModel` rows with `assigned_agent` + `depends_on` DAG. Uses department capability registry (each dept publishes its capabilities) to route.
- **AC:** "Deploy service X and notify the team" produces ≥ 2 tasks routed to Platform + Support with correct dependency.

### CORTEX-702: Support — Email, Ticketing, Knowledge Retrieval
- **How:** Tools: Gmail (read/send via Composio), Jira ticket CRUD, `knowledge_search` (Qdrant RAG over ingested docs — ingestion pipeline: chunk → embed via Ollama → upsert). Agent triages an email, searches knowledge, drafts reply (approval-gated send), files/updates ticket.
- **AC:** E2E: incoming test email → drafted reply citing a KB doc → approval → sent + Jira ticket linked.

### CORTEX-703: Engineering — GitHub, PR Generation, Code Review
- **How:** Tools: GitHub via Composio (read repo, create branch, commit, open PR, comment). PR generation: agent receives issue → plans change → generates diff → opens PR (always approval-gated). Code review: webhook on PR → agent posts structured review comments (never merges).
- **AC:** From a test issue, agent opens a compiling PR on a sandbox repo; review agent comments on a seeded bug.

### CORTEX-704: Platform — Kubernetes, Helm, Argo CD
- **How:** Tools: `kubectl_get/describe/logs` (read-only, no approval), `helm_upgrade`, `argocd_sync`, `k8s_scale` (approval-gated). All writes go through Argo CD app manipulation where possible (GitOps-first). Cluster access via scoped ServiceAccount.
- **AC:** "Scale service X to 3 replicas" → approval → Argo-synced change; read-only queries need no approval.

### CORTEX-705: SRE — Metrics, Logs, RCA, Rollback Recommendations
- **How:** Tools: PromQL query (Prometheus HTTP API), LogQL query (Loki), Jaeger trace search. RCA workflow: alert event → agent correlates metrics/logs/traces/recent deploys → produces RCA report + rollback recommendation (recommendation only; execution routes to Platform dept with approval).
- **AC:** Injected fault in demo app: agent's RCA report names the failing service and the offending deploy in ≥ 8/10 runs.

### CORTEX-706: Finance — Billing & Refund Workflows
- **How:** Mock/stub billing provider tool (Stripe-shaped API). Refund workflow: validate policy rules deterministically (amount limits, time window) in code, LLM only drafts customer communication. Refund execution always approval-gated with dual-control for amounts > threshold.
- **AC:** Refund above threshold requires two distinct approvers; policy violations rejected without LLM involvement.

### CORTEX-707: Security — Secret Rotation & Vulnerability Response
- **How:** Vault API tool: list secret metadata age, rotate via configured rotation endpoints; rotation is a Temporal saga (rotate → verify consumers → else rollback). Vulnerability response: consume scanner events (Trivy, Phase 13) → agent triages severity, files ticket, drafts remediation plan.
- **AC:** Scheduled rotation workflow rotates a demo secret with zero downtime for a consuming service.

### CORTEX-708: HR — Onboarding Workflows
- **How:** Long-running Temporal workflow (days): create accounts (Keycloak tool), grant access (approval-gated), send welcome email, schedule check-ins (durable timers). Demonstrates CORTEX-506 patterns.
- **AC:** Simulated onboarding runs across worker restarts; all steps audited.

---

# EPIC 8 — Memory

### CORTEX-801: Redis Short-Term Memory
- **How:** `ConversationMemory`: rolling window of recent messages per `task_id`, Redis lists with TTL (24h), token-aware truncation. Injected into agent state at graph start.
- **AC:** Agent recalls context from earlier in the same task; memory expires after TTL.

### CORTEX-802: PostgreSQL Structured Memory
- **How:** `MemoryFact` table (subject, predicate, object, confidence, source_step_id, created_at). Extraction node (optional, post-run) writes durable facts ("service X owner is team Y"). Queried by exact filters.
- **AC:** Fact written in workflow A is retrievable in workflow B.

### CORTEX-803: Qdrant Semantic Memory
- **How:** Collections: `episodic` (past task summaries) and `knowledge` (docs, shared with CORTEX-702). Embeddings via Ollama embedding model through LiteLLM. Store payload metadata (department, workflow_id, timestamps).
- **AC:** "Have we handled something like this before?" retrieves relevant past-episode summary with score > threshold.

### CORTEX-804: Unified Retrieval Strategy
- **How:** `MemoryService.retrieve(query, task_ctx)` composes: recent (Redis) + facts (PG filter) + semantic (Qdrant top-k) → dedupe → token-budget-aware ranking → single context block. Strategy configurable per agent role.
- **AC:** A/B eval on golden tasks: unified retrieval beats semantic-only on answer accuracy.

---

# EPIC 9 — Tool Integrations

### CORTEX-901: Tool Gateway
- **What:** Central choke point for ALL tool calls.
- **How:** `app/modules/tools/`: `ToolRegistry` (name, JSON schema, risk level `read|write|destructive`, required role, approval flag), `ToolGateway.execute()` doing: authz check → arg validation → approval gate → execute → audit log → metrics. Agents never call SDKs directly.
- **AC:** Grep confirms zero direct SDK calls from `app/agents/`; every tool call yields an audit row + Prometheus metric.

### CORTEX-902: Composio Integration
- **How:** Composio SDK wrapper: entity per department, OAuth connection flow persisted, map Composio actions into `ToolRegistry` with our risk metadata overlaid.
- **AC:** GitHub + Slack + Gmail + Jira actions callable through the Gateway using Composio-managed auth.

### CORTEX-903–906: GitHub / Slack / Gmail / Jira Tool Packs
- **How:** One ticket each. Curate minimal action sets (don't expose everything): GitHub (repo read, branch, PR, comment), Slack (post message, read channel — post to non-incident channels = write risk), Gmail (read, draft, send=approval), Jira (search, create, transition, comment). Integration tests against sandbox accounts with recorded cassettes (`vcrpy`) for CI.
- **AC (each):** Actions callable via Gateway; risk levels enforced; cassette tests green in CI.

### CORTEX-907: Kubernetes & Helm Tools
- **How:** Native (non-Composio) tools using official `kubernetes` Python client + `helm` subprocess wrapper: read ops unrestricted, write ops approval-gated and namespace-allowlisted from config. Dry-run mode returns rendered diff for approval context.
- **AC:** Approval request for `helm_upgrade` shows the manifest diff to the approver.

---

# EPIC 10 — Frontend (Next.js)

### CORTEX-1001: App Scaffold & Auth
- **How:** Next.js 15 (App Router, TypeScript), `frontend/` dir. Auth: `next-auth` with Keycloak provider, token refresh, roles in session. API client generated from OpenAPI (`openapi-typescript`). shadcn/ui + Tailwind.
- **AC:** Login via Keycloak; role-gated nav; typed API client compiles.

### CORTEX-1002: Dashboard
- **How:** Cards: active workflows, pending approvals, 24h success rate, token spend (from API aggregate endpoints — add them to Phase 3 backlog). Live-updates via WebSocket.
- **AC:** Numbers match DB within one refresh cycle; updates without reload.

### CORTEX-1003: Workflow Visualization
- **How:** Workflow detail page: task DAG rendered with React Flow (`depends_on` edges), node colors by status, click node → step drawer with agent thoughts, tool calls, token metrics. Live via WS.
- **AC:** Running workflow animates status changes in real time.

### CORTEX-1004: Agent Explorer
- **How:** List departments/agents with capabilities, per-agent stats (runs, success %, avg tokens), and a "playground" to submit a test task (admin-only).
- **AC:** Playground run appears in workflow list and streams output.

### CORTEX-1005: Approval Center
- **How:** Pending approvals inbox: rich context (what/why/diff/blast-radius from CORTEX-907), approve/reject with mandatory comment, dual-control UI for high-value items. Push notification via WS.
- **AC:** Approval round-trip from UI resumes the Temporal workflow; comments land in audit log.

### CORTEX-1006: Audit Viewer
- **How:** Filterable/paginated audit table (actor, action, resource, date range), event detail JSON viewer, export CSV. Viewer role can read, nobody can mutate.
- **AC:** Filter combinations return correct results against seeded data.

---

# EPIC 11 — Observability

### CORTEX-1101: OpenTelemetry Instrumentation
- **How:** OTel SDK: auto-instrument FastAPI, SQLAlchemy, Redis, HTTPX; manual spans for graph nodes and tool calls. Propagate context through NATS headers and Temporal (interceptors) so one trace covers API→workflow→agent→tool. OTLP export to Collector → Jaeger/Prometheus/Loki.
- **AC:** Single trace in Jaeger spans REST request through Temporal activity to LLM call.

### CORTEX-1102: Metrics & Prometheus
- **How:** Metrics: `workflow_duration_seconds`, `agent_step_duration_seconds`, `tool_call_duration_seconds{tool,status}`, `llm_tokens_total{model,type}`, `llm_cost_usd_total`, `approval_wait_seconds`. `/metrics` endpoint; Prometheus scrape config in Compose + Helm.
- **AC:** All KPI metrics visible in Prometheus with correct labels.

### CORTEX-1103: Grafana Dashboards
- **How:** Provisioned-as-code dashboards (JSON in `deploy/grafana/`): Platform Overview, Agent Performance, Cost, Approvals. Alert rules: error-rate spike, cost burn-rate, DLQ depth > 0.
- **AC:** `make up` provisions dashboards automatically; test alert fires to a webhook.

### CORTEX-1104: Loki Log Pipeline
- **How:** Structured JSON logging (`structlog`): every line carries `trace_id`, `workflow_id`, `task_id`. Promtail/Alloy ships to Loki. Grafana derived field links logs ↔ traces.
- **AC:** From a Jaeger trace, one click reaches the correlated Loki logs.

### CORTEX-1105: Phoenix LLM Observability
- **How:** Arize Phoenix in Compose; OpenInference instrumentation for LangGraph/LiteLLM traces (prompts, completions, latencies, evals). Wire golden-set evals (from CORTEX-603) to run against Phoenix datasets.
- **AC:** Every agent run visible in Phoenix with full prompt/response tree.

---

# EPIC 12 — Kubernetes

### CORTEX-1201: Application Helm Chart
- **How:** `deploy/helm/cortexops/`: Deployments (api, worker, consumers, frontend), values-driven config, probes wired to `/healthz` `/readyz`, resource requests/limits, PodDisruptionBudgets. Sub-chart or dependency refs for data services (dev only; prod uses managed/operator-based installs).
- **AC:** `helm install` on kind/minikube yields a fully working stack.

### CORTEX-1202: Namespaces, ConfigMaps, Secrets
- **How:** Namespaces per CORTEX-103. Config via ConfigMaps; secrets via External Secrets Operator pulling from Vault (no plaintext secrets in git or Helm values).
- **AC:** `kubectl get secrets -o yaml` shows only ESO-managed secrets; app boots with Vault-sourced creds.

### CORTEX-1203: HPA, NetworkPolicy, Ingress
- **How:** HPA on api (CPU + RPS via custom metrics) and workers (Temporal task-queue depth via KEDA scaler). Default-deny NetworkPolicies + explicit allows per the context map. Ingress (nginx or Gateway API) with TLS via cert-manager.
- **AC:** Load test triggers scale-out; cross-namespace probe blocked by NetworkPolicy; HTTPS terminates correctly.

### CORTEX-1204: GitOps with Argo CD
- **How:** App-of-apps pattern: `deploy/argocd/` with Applications per environment (dev/staging/prod), auto-sync + self-heal on dev, manual sync on prod, image updates via Argo CD Image Updater.
- **AC:** Merging a values change to `main` auto-deploys to dev within 5 min; prod requires manual sync.

---

# EPIC 13 — Security

### CORTEX-1301: Vault Production Setup
- **How:** Vault via Helm (HA raft), Kubernetes auth method, per-service policies (least privilege), dynamic Postgres credentials for the API, transit engine for any app-level crypto.
- **AC:** API's DB password rotates via dynamic creds; no static DB password anywhere.

### CORTEX-1302: Supply Chain — Scanning, SBOM, Signing
- **How:** CI pipeline: Trivy image + dependency scan (fail on HIGH+), Syft SBOM attached to releases, Cosign keyless signing of images; Kyverno/Sigstore policy in cluster verifies signatures at admission.
- **AC:** Unsigned image is rejected by the cluster; SBOM downloadable per release.

### CORTEX-1303: Policy Enforcement
- **How:** Kyverno policies: no privileged pods, required labels, resource limits mandatory, images only from our registry. Runtime: Pod Security Standards `restricted`.
- **AC:** Violating manifest rejected at admission with a clear message.

### CORTEX-1304: Agent-Specific Security Hardening
- **How:** Prompt-injection defenses at Tool Gateway (input sanitization, output-based tool-call verification), per-department tool allowlists, LLM output never interpolated into shell/SQL, egress restricted for agent pods.
- **AC:** Red-team prompt suite (≥ 20 injection attempts) cannot trigger an unauthorized tool call.

---

# EPIC 14 — Testing

### CORTEX-1401: Unit Test Foundation
- **How:** pytest + coverage gate (80% on `app/core`, `app/modules`); factory fixtures (`factory_boy`) for models; fake LLM client for deterministic agent-node tests.
- **AC:** CI enforces coverage; unit suite < 60s.

### CORTEX-1402: Integration Tests
- **How:** `testcontainers` for Postgres/Redis/NATS; Temporal test server (`temporalio.testing`) with time-skipping for approval timeouts; repository + consumer + workflow tests.
- **AC:** Full integration suite green in CI < 10 min.

### CORTEX-1403: Contract & E2E Tests
- **How:** Contract: schemathesis against OpenAPI; event contracts validated against the registry (CORTEX-401). E2E: Playwright — login, create workflow, approve, verify completion — against Compose stack in CI.
- **AC:** E2E happy path runs on every PR to `main`.

### CORTEX-1404: Load & Chaos
- **How:** Load: k6 scenarios (workflow creation RPS, WS fan-out) with SLO thresholds as pass/fail. Chaos: Litmus/chaos-mesh experiments — kill worker mid-workflow, partition NATS, restart Postgres — assert recovery invariants (no lost events, workflows resume).
- **AC:** Chaos suite passes: zero data loss, all workflows eventually complete or compensate.

### CORTEX-1405: Agent Evaluation Harness
- **How:** Golden-task datasets per department (from Phase 7 tickets); nightly eval run scoring success rate, cost, latency; regression alarm if success drops > 5%; results in Phoenix.
- **AC:** Nightly eval dashboard populated; a deliberately degraded prompt trips the alarm.

---

# EPIC 15 — Production Readiness

### CORTEX-1501: HA Deployment
- **How:** ≥ 3 replicas for api/workers across zones (topology spread), Postgres HA (CloudNativePG or managed), NATS 3-node cluster, Temporal multi-replica with proper persistence.
- **AC:** Killing any single node causes zero failed user requests (verified under load).

### CORTEX-1502: Backups & Disaster Recovery
- **How:** Postgres PITR (WAL to MinIO/S3), Qdrant snapshots, Vault snapshots, NATS stream backups. Documented + scripted restore. Quarterly DR drill runbook. Targets: RPO ≤ 5 min, RTO ≤ 1 h.
- **AC:** Full restore drill in a clean cluster meets RPO/RTO.

### CORTEX-1503: SLOs & Alerting
- **How:** SLOs: API availability 99.9%, workflow start latency p95 < 2s, agent task success ≥ 95%. Multi-window burn-rate alerts (Sloth/Pyrra) → PagerDuty/Slack.
- **AC:** SLO dashboards live; synthetic breach pages on-call.

### CORTEX-1504: Runbooks
- **How:** `docs/runbooks/`: one per alert (symptom, diagnosis queries, remediation, escalation) — DLQ growth, Temporal backlog, LLM provider outage, cost spike, Vault sealed.
- **AC:** Every alert links to its runbook; new on-call resolves a game-day incident using only runbooks.

### CORTEX-1505: Cost Dashboards
- **How:** Combine LLM cost metrics (CORTEX-608/1102) with infra cost (OpenCost). Grafana: cost per workflow, per department, per model; budget alerts.
- **AC:** Finance-friendly monthly cost report exportable; budget alert fires on simulated overspend.

---

# Suggested Sprint Mapping (first 6 sprints)

| Sprint | Focus | Tickets |
|---|---|---|
| 1 | Governance + repo tooling | CORTEX-001..005, 201, 202 |
| 2 | Local platform + config | CORTEX-203, 204, 301, 302 |
| 3 | Data layer done right | CORTEX-303, 304, 305, 308 |
| 4 | Auth + API | CORTEX-306, 307, 309, 310 |
| 5 | Events | CORTEX-401..406 |
| 6 | Temporal core | CORTEX-501..503 |