import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm.exc import StaleDataError

from apps.agent_runtime.api import health
from apps.agent_runtime.infrastructure.agent_runtime_nats_client import agent_nats_client as nats
from apps.agent_runtime.infrastructure.database import agent_runtime_db_client
from apps.agent_runtime.infrastructure.outbox_publisher import agent_outbox_publisher
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger
from apps.agent_runtime.infrastructure.telemetry import AgentObservability
from packages.redis.redis_client import redis_client
from packages.telemetry.provider import init_telemetry


@asynccontextmanager
async def agent_lifespan(app: FastAPI):
    if not agent_runtime_db_client.check_health():
        raise RuntimeError("Agent Runtime database health check failed on startup!")
    init_telemetry(service_name="cortexops-agent-runtime", environment="local")
    logger.info("Initializing the Agent Runtime Daemon ....")

    await redis_client.initialize()
    await nats.initialize()
    logger.info("NATS Core Messaging is successfully initialized for Agent Runtime Service")
    outbox_task = asyncio.create_task(agent_outbox_publisher.start())
    logger.info("Agent Runtime Outbox Publisher Worker started successfully.")

    yield

    agent_outbox_publisher.stop()
    await outbox_task
    await nats.shutdown()
    await redis_client.close()

    logger.info("NATS Messaging Core successfully disconnected from Agent Runtime.")

app = FastAPI(title="ADD Platform Agent Runtime Service", lifespan=agent_lifespan)

@app.post("/api/v1/agents/execute")
async def execute_agent(payload: dict):
    agent_id = payload.get("agent_id", "unknown")
    agent_type = payload.get("agent_type", "ReActAgent")

    start_time = time.perf_counter()
    status = "success"

    # 1. Open correlated span and bind context
    with AgentObservability.trace_agent_run(
            agent_id=agent_id,
            agent_type=agent_type,
            tenant_id=payload.get("tenant_id"),
            workflow_instance_id=payload.get("workflow_instance_id"),
            agent_run_id=payload.get("agent_run_id"),
    ):
        try:
            logger.info("Agent starting execution", extra_data={"agent_type": agent_type})

            # --- AGENT REASONING / TOOL CALL LOOP ---
            # (Simulated execution and token consumption)
            prompt_tokens, completion_tokens = 150, 45

            logger.info("Agent completed task execution")
            return {"status": "ok", "agent_id": agent_id}

        except Exception as exc:
            status = "failure"
            logger.error(f"Agent execution failed: {str(exc)}", exc_info=True)
            raise exc

        finally:
            # 2. Record metrics safely
            duration = time.perf_counter() - start_time
            AgentObservability.record_metrics(
                agent_type=agent_type,
                status=status,
                duration=duration,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
@app.exception_handler(StaleDataError)
async def stale_data_exception_handler(request: Request, exc: StaleDataError):
    logger.warning(f"Optimistic lock conflict detected in Agent Runtime: {exc}")
    return JSONResponse(
        status_code=409,
        content={
            "error": "RESOURCE_CONFLICT",
            "message": "The agent runtime resource was updated by another request. Please retry."
        }
    )


app.include_router(health.router)