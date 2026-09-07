import structlog.contextvars

from packages.logging.structured_logs import StructuredLogger

logger_inst = StructuredLogger(service_name="test_logger_service", level= "INFO")
logger = logger_inst.get_logger()

structlog.contextvars.bind_contextvars(
    tenant_id="tenant-123",
    agent_run_id="run-456",
    correlation_id="corr-789"
)

logger.info(
    event = "Agent executed tool",
    tool_name="gmail.search",
    headers={"authorization": "Bearer secret-token-123", "x-api-key": "key-xyz"},
    payload={"password": "my_password", "query": "label:inbox"}
)

"""
docker run --rm -it \
  -v "$PWD":/app \
  -w /app \
  -e PYTHONPATH=/app \
  python:3.10 \
  bash -lc "pip install -r requirements.txt && python packages/logging/test_logger.py"

"""