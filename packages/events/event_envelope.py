from typing import Optional, Any, Dict

from pydantic import BaseModel

from packages.events.base import BaseEvent
from packages.events.context import RequestContext


class EventEnvelope(BaseModel):
    event_id : str
    event_name: str
    source_service: str
    timestamp: str
    version: int
    correlation_id: Optional[str]= None
    causation_id: Optional[str] = None
    tenant_id: Optional[str] = None
    payload: Dict[str, Any]

    @classmethod
    def wrap(cls, event: BaseEvent, source_service: str) -> "EventEnvelope":
        """Wraps a typed BaseEvent instance inside a standardized wire envelope."""
        return cls(
            event_id=str(event.event_id),
            event_name=event.event_name,
            source_service=source_service,
            timestamp=event.timestamp.isoformat(),
            version=event.version,
            correlation_id=RequestContext.get_correlation_id() or str(event.event_id),
            causation_id=RequestContext.get_causation_id(),
            tenant_id=RequestContext.get_tenant_id(),
            payload=event.to_payload(),
        )