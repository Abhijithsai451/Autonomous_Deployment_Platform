import logging
import sys
from typing import Dict

import structlog
from typing_extensions import Any


class StructuredLogger:
    """
    Central Log Manager responsible for configuring and providing highly optimized, JSON log streams for distributed
    Microservices
    """
    def __init__(self, service_name: str, level: str = "Info", initial_context: Dict[str, Any]=None):
        self.service_name = service_name
        self.level = level.upper()
        self.initial_context = initial_context or {}
        self._log_level = getattr(logging, self.level, logging.INFO)
        self._bootstrap_system_logging()
        self._configure_structlog_pipeline()
        self._logger = self.get_logger()
    def _bootstrap_system_logging(self) -> None:
        """
        Forwards standard Library log statements cleanly into stdout streams
        """
        logging.basicConfig(
            format= "%(message)s",
            stream = sys.stdout,
            level = self._log_level
        )

    def _configure_structlog_pipeline(self) -> None:
        """Sets up the operational middleware chains for stringifying objects to JSON blocks."""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    def get_logger(self, **runtime_context: Any) -> structlog.stdlib.BoundLogger:
        """
        Generates or retrieves a context-bound structural logger instance.
        Allows immediate binding of runtime metadata keys at initialization.
        """
        # Combine default class parameters with custom execution contextual logs
        bound_meta = {
            "service": self.service_name,
            **self.initial_context,
            **runtime_context
        }
        return structlog.get_logger().bind(**bound_meta)

    def info(self, event: str, **kwargs: Any) -> None:
        self._logger.info(event, **kwargs)

    def debug(self, event: str, **kwargs: Any) -> None:
        self._logger.debug(event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._logger.error(event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._logger.warning(event, **kwargs)

struc_logger = StructuredLogger(
    service_name="cortexops-infra",
    level= "INFO",
    initial_context = {"env": "production"}
)