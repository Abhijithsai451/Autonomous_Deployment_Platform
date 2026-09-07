import uuid
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from typing import Optional, Any, Dict, Generator

import structlog


@dataclass
class CorrelationContext:
    tenant_id: Optional[str] = None
    organization_id: Optional[str] = None
    workflow_instance_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_run_id: Optional[str] = None
    agent_id: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None

    def to_dict(self)-> Dict[str, Any]:
        """Fiilters out None values to keep log payloads clean """
        return {k: v  for k,v in asdict(self).items() if v is not None}

def generate_id()-> str:
    return str(uuid.uuid4())

@contextmanager
def bind_correlation_context(**kwargs: Any) -> Generator[CorrelationContext, None, None]:
    """
    Context manager to safely bind execution correlation variables to async thread-local
    structlog contextvars, ensuring cleanup upon exit to prevent cross-request leakage.
    """
    if "correlation_id" not in kwargs or not kwargs["correlation_id"]:
        kwargs["correlation_id"] = generate_id()

    ctx = CorrelationContext(**{k:v for k, v in kwargs.items() if hasattr(CorrelationContext, k)})
    bound_dict = ctx.to_dict()

    structlog.contextvars.bind_contextvars(**bound_dict)

    try:
        yield ctx
    finally:
        structlog.contextvars.unbind_contextvars(*bound_dict.keys())


