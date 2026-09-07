import logging

from opentelemetry.sdk._logs import LoggingHandler

from packages.logging.structured_logs import StructuredLogger

otel_handler = LoggingHandler()
logging.getLogger().addHandler(otel_handler)
logging.getLogger().setLevel(logging.INFO)

log_manager = StructuredLogger(
    service_name="cortexops-agent_runtime",
    level= "INFO",
    initial_context = {"env": "production"}
)
struct_logger = log_manager.get_logger()