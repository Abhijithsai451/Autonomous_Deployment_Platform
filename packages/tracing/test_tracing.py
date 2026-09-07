import structlog
from packages.telemetry.provider import init_telemetry
from packages.tracing.spans import start_agent_span
from packages.logging.structured_logs import StructuredLogger

# Initialize telemetry and logger
init_telemetry("cortexops-agent-runtime", "local")
logger_inst = StructuredLogger(service_name="cortexops-agent-runtime")
logger = logger_inst.get_logger()

# Test span wrapper with logging
with start_agent_span("agent.execution", attributes={"agent.id": "agent-007"}):
    logger.info("Executing agent task step")

print("Phase 5 tracing helper verified successfully.")