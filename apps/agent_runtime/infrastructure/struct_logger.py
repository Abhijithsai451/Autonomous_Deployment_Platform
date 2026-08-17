from packages.logging.structured_logs import StructuredLogger

log_manager = StructuredLogger(
    service_name="cortexops-agent_runtime",
    level= "INFO",
    initial_context = {"env": "production"}
)
struct_logger = log_manager.get_logger()