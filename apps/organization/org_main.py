from fastapi import FastAPI

from packages.logging.structured_logs import StructuredLogger

log_manager = StructuredLogger(
    service_name="cortexops-organization",
    level= "INFO",
    initial_context = {"env": "production"}
)

logger = log_manager.get_logger()

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    logger.info("service_lifecycle_started", database_status="connected")